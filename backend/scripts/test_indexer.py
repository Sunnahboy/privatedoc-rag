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
    result = await indexer.index(embeddings)
    elapsed = time.perf_counter() - start

    print("\n" + "=" * 55)
    print("           QDRANT INDEXING BENCHMARK")
    print("=" * 55)
    print(f"{'Metric':<25}{'Value'}")
    print("-" * 55)
    print(f"{'Embeddings':<25}{result.indexed_count}")
    print(f"{'Collection':<25}{result.collection_name}")
    print(f"{'Time':<25}{elapsed:.3f} s")
    print(f"{'Throughput':<25}{result.indexed_count / elapsed:.2f} vectors/s")

    if result.indexed_count:
        print(
            f"{'Latency':<25}"
            f"{(elapsed / result.indexed_count) * 1000:.2f} ms/vector"
        )
    else:
        print(f"{'Latency':<25}N/A")

    print("=" * 55)

    await indexer.close()


if __name__ == "__main__":
    asyncio.run(main())
