import asyncio

from app.pipeline.generation.ollama_generator import OllamaGenerator
from app.pipeline.retrieval.models import RetrievedChunk


async def main():
    context = [
        RetrievedChunk(
            chunk_id="1",
            document_id="doc1",
            chunk_index=0,
            text="Retrieval-Augmented Generation (RAG) combines retrieval with large language models.",
            score=0.98,
        ),
        RetrievedChunk(
            chunk_id="2",
            document_id="doc1",
            chunk_index=1,
            text="Qdrant is a vector database used to store and search embeddings.",
            score=0.95,
        ),
    ]

    generator = OllamaGenerator()

    try:
        result = await generator.generate(
            question="What is RAG?",
            context=context,
        )

        print("=" * 50)
        print("ANSWER")
        print("=" * 50)
        print(result.answer)

        print("\nCITATIONS")
        for chunk in result.citations:
            print(f"Chunk {chunk.chunk_index}: {chunk.text}")

    finally:
        await generator.close()


if __name__ == "__main__":
    asyncio.run(main())
