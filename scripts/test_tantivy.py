import asyncio
import uuid

from app.pipeline.chunking.models import Chunk
from app.pipeline.indexing.tantivy_index import TantivyIndex


async def main():
    index = TantivyIndex()

    chunks = [
        Chunk(
            chunk_id=str(uuid.uuid4()),
            document_id="doc1",
            chunk_index=0,
            text="Software architecture defines the high level structure of a system.",
            start_char=0,
            end_char=0,
        ),
        Chunk(
            chunk_id=str(uuid.uuid4()),
            document_id="doc1",
            chunk_index=1,
            text="CQRS separates commands from queries.",
            start_char=0,
            end_char=0,
        ),
        Chunk(
            chunk_id=str(uuid.uuid4()),
            document_id="doc2",
            chunk_index=0,
            text="N-version programming improves fault tolerance.",
            start_char=0,
            end_char=0,
        ),
    ]

    await index.add_documents(chunks)

    results = await index.search(
        "software architecture",
        top_k=3,
    )

    print("=" * 60)
    print("TANTIVY SEARCH RESULTS")
    print("=" * 60)

    if not results:
        print("No results found.")
    else:
        for i, chunk in enumerate(results, start=1):
            print(f"\nResult #{i}")
            print(f"Score       : {chunk.score:.4f}")
            print(f"Document ID : {chunk.document_id}")
            print(f"Chunk Index : {chunk.chunk_index}")
            print(f"Text        : {chunk.text[:120]}...")

    await index.close()


if __name__ == "__main__":
    asyncio.run(main())
