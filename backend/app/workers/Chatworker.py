import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.pipeline.generation.ollama_generator import OllamaGenerator
class Chatworker:
    def __init__(self, generator: OllamaGenerator):
        self.generator = generator
    async def process_chat_job(self, message_id: str, prompt: str, db: AsyncSession):
        channel = f"stream_{message_id.replace('-','_')}"#pg channel names shouldn't have hyphens

        generated_chunks: list[str] = []
        #update the status to processing
        await db.execute(
            text("UPDATE chat_messages SET status = 'processing' WHERE id = :id" ),
            {"id":message_id}
        )

        await db.commit()

        try:
            #consume the generator stream
            async for token in self.generator.generate_stream(prompt=prompt):
                generated_chunks.append(token)#fast, mutable insertion
            

                #broadcast( Broadcast via Pg Pub/sub)
                payload = json.dumps({"type":"token","content": token})
                await db.execute(
                    text("SELECT pg_notify(:channel, : payload)"),
                    {"channel": channel,"payload":payload}
                )

                await db.commit()#flush the notification

            await db.execute(
                text("SELECT pg_notify(:channel, :payload)"),
                {"channel": channel, "payload":json.dumps({"type": "done"})}
            )

            #final atomic state persistent
            final_text = "".join(generated_chunks)
            await db.execute(
                text("UPDATE  chat_messages SET content = : content, status = 'completed' WHERE id = :id"),
                {"content": final_text, "id": message_id}
            )
            await db.commit()

        except Exception as exc:
            await db.execute(
                text("UPDATE chat_message SET status = 'failed' WHERE id = :id" ),
                {"id": message_id}
            )
            await db.commit()
            raise exc


