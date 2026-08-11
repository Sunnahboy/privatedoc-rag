import asyncio
import time

from app.pipeline.generation.ollama_generator import OllamaGenerator
from app.pipeline.retrieval.models import RetrievedChunk

QUESTION = "What is RAG?"


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
        # ---------------- Prompt ----------------
        prompt_start = time.perf_counter()

        prompt = generator.prompt_builder.build(
            question=QUESTION,
            context=context,
        )

        prompt_time = time.perf_counter() - prompt_start

        # ---------------- Generation ----------------
        generation_start = time.perf_counter()

        result = await generator.generate(
            question=QUESTION,
            context=context,
        )

        generation_time = time.perf_counter() - generation_start

        total_time = prompt_time + generation_time

        # ---------------- Output ----------------
        print("=" * 60)
        print("ANSWER")
        print("=" * 60)
        print(result.answer)

        print("\nCITATIONS")
        for chunk in result.citations:
            print(f"• Chunk {chunk.chunk_index}: {chunk.text}")

        print("\n" + "=" * 60)
        print("GENERATION BENCHMARK")
        print("=" * 60)
        print(f"Model              : {generator.model}")
        print(f"Context Chunks     : {len(context)}")
        print(f"Prompt Length      : {len(prompt)} chars")
        print(f"Answer Length      : {len(result.answer)} chars")
        print("-" * 60)
        print(f"Prompt Build       : {prompt_time:.4f} s")
        print(f"Inference          : {generation_time:.4f} s")
        print(f"Total Time         : {total_time:.4f} s")
        print("-" * 60)
        print(f"Prompt Tokens   : {result.prompt_tokens}")
        print(f"Output Tokens   : {result.completion_tokens}")
        print(
            f"Inference Speed : {result.completion_tokens / generation_time:.2f} tokens/sec"
        )
        print("=" * 60)

    finally:
        await generator.close()


if __name__ == "__main__":
    asyncio.run(main())
