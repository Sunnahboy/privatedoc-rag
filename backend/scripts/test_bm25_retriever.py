import asyncio

from app.pipeline.retrieval.bm25_retriever import BM25Retriever


async def main():
    retriever = BM25Retriever()

    result = await retriever.retrieve(
        query="software architecture",
        top_k=3,
    )

    print("=" * 60)
    print("BM25 RETRIEVER")
    print("=" * 60)

    print(f"Found: {result.found}")
    print(f"Chunks: {len(result.chunks)}")

    for chunk in result.chunks:
        print()
        print(f"Score       : {chunk.score:.4f}")
        print(f"Document ID : {chunk.document_id}")
        print(f"Chunk Index : {chunk.chunk_index}")
        print(f"Text        : {chunk.text[:100]}")

    await retriever.close()


if __name__ == "__main__":
    asyncio.run(main())