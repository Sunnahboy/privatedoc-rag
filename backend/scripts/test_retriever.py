import asyncio
from uuid import uuid4

from app.pipeline.embeddings.models import EmbeddingResult
from app.pipeline.indexing.qdrant_indexer import QdrantIndexer
from app.pipeline.retrieval.qdrant_retriever import QdrantRetriever


async def main():
    embeddings = []

    for i in range(5):
        embeddings.append(
            EmbeddingResult(
                chunk_id=str(uuid4()),
                document_id="doc1",
                chunk_index=i,
                text=f"Document 1 - Chunk {i}",
                vector=[0.1] * 768,
                model_name="nomic-embed-text",
                dimensions=768,
            )
        )
    for i in range(5):
        embeddings.append(
            EmbeddingResult(
                chunk_id=str(uuid4()),
                document_id="doc2",
                chunk_index=i,
                text=f"Document 2 - Chunk {i}",
                vector=[0.2] * 768,
                model_name="nomic-embed-text",
                dimensions=768,

            )
        )

    async with QdrantIndexer() as indexer:
        # Clean previous benchmark/test data
        await indexer.client.delete_collection(
            collection_name=indexer.collection_name,
        )
        await indexer.index(embeddings)

    async with QdrantRetriever() as retriever:
        response = await retriever.retrieve(
            query="Document",
            top_k=3,
            document_id="doc2"
        )

        print(response)


if __name__ == "__main__":
    asyncio.run(main())
