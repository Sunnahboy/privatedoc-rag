import json
import logging
import copy
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.orchestration.rag_pipeline import RAGPipeline
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Valkey client for the worker
valkey_client = redis.from_url(settings.valkey_url, decode_responses=True)

class ChatWorker:
    def __init__(self, rag_pipeline: RAGPipeline):
        self.rag_pipeline = rag_pipeline

    async def process_chat_job(self, message_id: str, session_id: str, question:str, document_id:str, db: AsyncSession):
        stream_key = f"chat:stream:{message_id}"
        generated_chunks: list[str] = []
        final_citations = "[]"
        notify_dict = {}

        await db.execute(
            text("UPDATE chat_messages SET status = 'processing' WHERE id = :id"),
            {"id": message_id}
        )
        await db.commit()

        try:
            stream = self.rag_pipeline.ask_stream(
                question=question,
                document_id=document_id,
                chat_history=[], 
            )

            # LIVE GENERATION: Write to Valkey RAM buffer
            async for chunk_dict in stream:
                if chunk_dict.get("type") == "token":
                    generated_chunks.append(chunk_dict["content"])

                notify_dict = chunk_dict
                if chunk_dict.get("type") == "done" and "citations" in chunk_dict:
                    notify_dict = copy.deepcopy(chunk_dict)
                    for cit in notify_dict["citations"]:
                        if "text" in cit and cit["text"]:
                            # Truncation is no longer strictly required for Valkey, but good for bandwidth
                            cit["text"] = cit["text"][:500] + "... [truncated]"
                    final_citations = json.dumps(chunk_dict["citations"])

                # XADD automatically generates the offset ID and pushes to waiting clients
                payload = json.dumps(notify_dict)
                await valkey_client.xadd(stream_key, {"payload": payload})

            # DURABLE STORAGE: Commit the final assembled string to Postgres disk
            final_answer = "".join(generated_chunks)
            await db.execute(
                text("""
                    UPDATE chat_messages 
                    SET content = :content, 
                        citations = :citations,
                        status = 'completed' 
                    WHERE id = :id
                """),
                {
                    "content": final_answer,
                    "citations": final_citations,
                    "id": message_id
                }
            )
            await db.commit()
            
            # MEMORY MANAGEMENT: Tell Valkey to delete the stream after 10 minutes.
            # Postgres is the permanent home now.
            await valkey_client.expire(stream_key, 600)

        except Exception as exc:
            logger.error("Chat generation failed for %s: %s", message_id, str(exc))
            await db.rollback()
            
            await db.execute(
                text("UPDATE chat_messages SET status = 'failed' WHERE id = :id"),
                {"id": message_id}
            )
            await db.commit()
            
            error_payload = json.dumps({"type": "error", "error": "Generation failed."})
            await valkey_client.xadd(stream_key, {"payload": error_payload})
            await valkey_client.expire(stream_key, 60) # Expire errors faster
            
            raise exc