import argparse
import asyncio
import random
import time
import uuid

from app.pipeline.chunking.models import Chunk
from app.pipeline.embeddings.ollama_embedder import OllamaEmbedder


def generate_random_text(min_words=50, max_words=150):
    """Generates random text to simulate realistic payload variation."""
    words = [
        "lorem",
        "ipsum",
        "dolor",
        "sit",
        "amet",
        "consectetur",
        "adipiscing",
        "elit",
        "data",
        "vector",
    ]
    length = random.randint(min_words, max_words)
    return " ".join(random.choices(words, k=length))


async def run_benchmark(num_chunks: int, concurrency: int):
    """Executes a single benchmark run and returns raw stats."""
    chunks = [
        Chunk(
            chunk_id=str(uuid.uuid4()),
            document_id=f"doc_{i}",
            chunk_index=i,
            text=generate_random_text(),
            start_char=0,
            end_char=100,
        )
        for i in range(num_chunks)
    ]

    embedder = OllamaEmbedder(max_concurrency=concurrency)

    try:
        # Small indicator I knows it's working
        print(f"Benchmarking: N={num_chunks}, Conc={concurrency}...", end="\r")

        start = time.perf_counter()
        await embedder.embed(chunks)
        elapsed = time.perf_counter() - start

        return {
            "chunks": num_chunks,
            "concurrency": concurrency,
            "time": elapsed,
            "throughput": num_chunks / elapsed,
            "latency": (elapsed / num_chunks) * 1000,
        }
    finally:
        await embedder.close()


def print_table(header_label: str, rows: list):
    """Generic table printer."""
    print("\n" + "=" * 65)
    print(f"{header_label:<10} {'Time(s)':<12} {'Chunks/s':<15} {'Latency(ms)':<15}")
    print("-" * 65)

    for row in rows:
        # Row format: (label_value, time, throughput, latency)
        print(f"{row[0]:<10} {row[1]:<12.3f} {row[2]:<15.1f} {row[3]:<15.2f}")

    print("=" * 65 + "\n")


async def run_size_sweep(args):
    print(f"\nStarting Size Sweep (Concurrency={args.concurrency})...")

    # Handle default if no specific sizes provided
    sizes = args.sizes if args.sizes else [64, 128, 256, 512, 1000]
    rows = []

    for size in sizes:
        res = await run_benchmark(size, args.concurrency)
        rows.append((res["chunks"], res["time"], res["throughput"], res["latency"]))

    print_table("Chunks", rows)


async def run_concurrency_sweep(args):
    print(f"\nStarting Concurrency Sweep (Chunks={args.num_chunks})...")

    levels = [1, 2, 4, 8, 16, 32]
    rows = []

    for conc in levels:
        res = await run_benchmark(args.num_chunks, conc)
        rows.append(
            (res["concurrency"], res["time"], res["throughput"], res["latency"])
        )

    print_table("Conc.", rows)


async def main():
    parser = argparse.ArgumentParser(description="Ollama Embedding Benchmark")

    # Global Defaults
    parser.add_argument(
        "-n",
        "--num-chunks",
        type=int,
        default=500,
        help="Fixed N for concurrency sweep",
    )
    parser.add_argument(
        "-c", "--concurrency", type=int, default=8, help="Fixed C for size sweep"
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)

    # Mode 1: Size Sweep
    p_size = subparsers.add_parser("size", help="Sweep chunk sizes")
    p_size.add_argument(
        "sizes",
        nargs="*",
        type=int,
        help="List of sizes (default: 64 128 256 512 1000)",
    )

    # Mode 2: Concurrency Sweep
    subparsers.add_parser("concurrency", help="Sweep concurrency levels")

    args = parser.parse_args()

    if args.mode == "size":
        await run_size_sweep(args)
    elif args.mode == "concurrency":
        await run_concurrency_sweep(args)


if __name__ == "__main__":
    asyncio.run(main())
