import asyncio
import uuid

from app.pipeline.chunking.models import Chunk
from app.pipeline.embeddings.ollama_emdedder import OllamaEmbedder


async def main():
    chunk = Chunk(
        chunk_id=str(uuid.uuid4()),
        document_id="doc1",
        chunk_index=0,
        text="Artificial Intelligence is transforming healthcare.",
        start_char=0,
        end_char=48,
    )

    embedder = OllamaEmbedder()

    result = await embedder.embed([Chunk])

    print(result)

    asyncio.run(main())
