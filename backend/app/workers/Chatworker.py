import copy  # noqa
import json
import logging

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.chat import ChatMessage
from app.orchestration.rag_pipeline import RAGPipeline
from app.pipeline.retrieval.query_rewriter import QueryRewriter
from app.pipeline.retrieval.query_router import HybridQueryRouter, RouteDecision

logger = logging.getLogger(__name__)

# Initialize Valkey client for the worker
valkey_client = redis.from_url(settings.valkey_url, decode_responses=True)


class ChatWorker:
    def __init__(
        self,
        rag_pipeline: RAGPipeline,
        query_rewriter: QueryRewriter,
        query_router: HybridQueryRouter,
    ):
        self.rag_pipeline = rag_pipeline
        self.query_rewriter = query_rewriter
        self.query_router = query_router

    async def _get_chat_history(
        self, session_id: str, current_message_id: str, db: AsyncSession, limit: int = 6
    ) -> list[ChatMessage]:
        query = text("""
            SELECT role, content 
            FROM chat_messages 
            WHERE session_id = :session_id 
              AND id != :current_message_id
              AND status = 'completed'
            ORDER BY created_at DESC 
            LIMIT :limit
        """)
        result = await db.execute(
            query,
            {
                "session_id": session_id,
                "current_message_id": current_message_id,
                "limit": limit,
            },
        )
        rows = result.fetchall()
        # Reversed so the LLM reads messages chronologically (oldest to newest)
        return [ChatMessage(role=r.role, content=r.content) for r in reversed(rows)]

    async def process_chat_job(
        self,
        message_id: str,
        session_id: str,
        question: str,
        document_ids: list[str],
        db: AsyncSession,
    ):
        stream_key = f"chat:stream:{message_id}"
        generated_chunks: list[str] = []
        final_citations = "[]"
        notify_dict = {}

        await db.execute(
            text("UPDATE chat_messages SET status = 'processing' WHERE id = :id"),
            {"id": message_id},
        )
        await db.commit()

        try:
            chat_history = await self._get_chat_history(
                session_id=session_id, current_message_id=message_id, db=db, limit=6
            )

            # --- THE DOUBLE SHIELD PIPELINE ---

            # 1. TIER 1: Instant Regex Bypass on RAW query (0ms)
            route_decision = self.query_router.route_regex_only(question)

            # 2. TIER 3: Semantic Fallback on RAW query (10ms)
            if route_decision != RouteDecision.CASUAL:
                # If regex missed a typo (e.g., "hi are u"), catch it with vectors BEFORE rewriting
                route_decision = await self.query_router.route_semantic(question)

            # 3. EXECUTION FORKING
            if route_decision == RouteDecision.CASUAL:
                search_query = question
                skip_search = True
                logger.info(
                    "Router identified casual intent. Bypassing Rewriter and Qdrant."
                )
            else:
                # 4. CONTEXT RESOLUTION (800ms)
                # We only pay the LLM latency cost if we are GUARANTEED to hit Qdrant
                logger.info("Query requires search. Rewriting context...")
                search_query = await self.query_rewriter.rewrite(
                    query=question, chat_history=chat_history
                )
                skip_search = False

            stream = self.rag_pipeline.ask_stream(
                question=search_query,
                document_ids=document_ids,
                chat_history=chat_history,
                skip_search=skip_search,
            )

            # LIVE GENERATION: Write to Valkey RAM buffer
            async for chunk_dict in stream:
                if chunk_dict.get("type") == "token":
                    generated_chunks.append(chunk_dict["content"])

                notify_dict = chunk_dict
                if chunk_dict.get("type") == "done" and "citations" in chunk_dict:
                    notify_dict = copy.deepcopy(chunk_dict)
                    for cit in notify_dict["citations"]:
                        if cit.get("text"):
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
                    "id": message_id,
                },
            )
            await db.commit()

            # MEMORY MANAGEMENT: Tell Valkey to delete the stream after 10 minutes.
            # Postgres is the permanent home now.
            await valkey_client.expire(stream_key, 600)

        except Exception:
            logger.exception("Chat generation failed for %s", message_id)
            await db.rollback()

            await db.execute(
                text("UPDATE chat_messages SET status = 'failed' WHERE id = :id"),
                {"id": message_id},
            )
            await db.commit()

            error_payload = json.dumps({"type": "error", "error": "Generation failed."})
            await valkey_client.xadd(stream_key, {"payload": error_payload})
            await valkey_client.expire(stream_key, 60)  # Expire errors faster

            raise
