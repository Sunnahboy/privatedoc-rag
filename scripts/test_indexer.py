import argparse
import asyncio
import time
from uuid import uuid4

from app.pipeline.embeddings.models import EmbeddingResult
from app.pipeline.indexing.qdrant_indexer import QdrantIndexer


def generate_embeddings(count: int = 1000) -> list[EmbeddingResult]:
    embeddings = []

    for i in range(count):
        embeddings.append(
            EmbeddingResult(
                chunk_id=uuid4(),
                document_id=uuid4(),
                chunk_index=i,
                vector=[0.1] * 768,
                model_name="nomic-embed-text",
                dimensions=768,
            )
        )

    return embeddings


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n",
        "--num-embeddings",
        type=int,
        default=1000,
    )

    args = parser.parse_args()

    embeddings = generate_embeddings(args.num_embeddings)

    indexer = QdrantIndexer()

    start = time.perf_counter()
    result = asyncio.run(indexer.index(embeddings))
    elapsed = time.perf_counter() - start

    print(f"Indexed {result.indexed_count} embeddings in {elapsed:.2f} seconds")
    print(f"Throughput: {result.indexed_count / elapsed:.2f} vectors/second")

    if result.indexed_count:
        print(f"Latency: {(elapsed / result.indexed_count) * 1000:.2f} ms/vector")
    else:
        print("Latency: N/A")

    await indexer.close()


if __name__ == "__main__":
    asyncio.run(main())
