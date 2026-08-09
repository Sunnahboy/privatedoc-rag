import logging
import sys

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """
    Configure application-wide logging.

    Why logging matters:
    - Print statements are weak debugging.
    - Logs help us understand what happened during upload, retrieval, and generation.
    - Help with log chunk counts, retrieval scores, and LLM latency.
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def log_rag_profile(
    timings: dict[str, float],
    dense_hits: int,
    sparse_hits: int,
    fused_hits: int,
    context_chunks: int,
    prompt_chars: int,
    context_chars: int,
) -> None:
    avg_chunk_chars = context_chars / context_chunks if context_chunks else 0
    total_time = timings.get("Retrieval", 0) + timings.get("Generation", 0)

    llm_percent = (
        (timings.get("Generation", 0) / total_time) * 100 if total_time > 0 else 0
    )
    logger.info(
        """
==================== RAG PROFILING ====================

Retrieval
├── Dense Hits      : %7d
├── Sparse Hits     : %7d
├── Fused Hits      : %7d
├── Query Embedding : %7.2f ms
├── Qdrant Search   : %7.2f ms
├── Sparse Search   : %7.2f ms
├── RRF Fusion      : %7.2f ms
└── Cross-Enc Rerank: %7.2f ms

Generation
├── Context Chunks  : %7d
├── Context Chars   : %7d
├── Prompt Chars    : %7d
├── Time            : %7.2f ms
├── Load            : %7.2f ms
├── Prompt Eval     : %7.2f ms
├── Token Eval      : %7.2f ms
├── LLM %%          : %6.2f%%
├── Prompt Tokens   : %7.0f
├── Output Tokens   : %7.0f
├── Avg Chunk Chars : %7.0f
├── Prompt TPS      : %7.2f
└── Generate TPS    : %7.2f

-------------------------------------------------------
Retrieval Total     : %7.2f ms
Request Total       : %7.2f ms
=======================================================
""",
        dense_hits,
        sparse_hits,
        fused_hits,
        timings.get("Query Embedding", 0) * 1000,
        timings.get("Qdrant Search", 0) * 1000,
        timings.get("Sparse Search", 0) * 1000,
        timings.get("RRF Fusion", 0) * 1000,
        timings.get("Cross-Encoder Reranking", 0) * 1000,  # <-- Added here
        context_chunks,
        context_chars,
        prompt_chars,
        timings.get("Generation", 0) * 1000,
        timings.get("ollama.load", 0) * 1000,
        timings.get("ollama.prompt_eval", 0) * 1000,
        timings.get("ollama.eval", 0) * 1000,
        llm_percent,
        timings.get("ollama.prompt_tokens", 0),
        timings.get("ollama.completion_tokens", 0),
        avg_chunk_chars,
        timings.get("ollama.prompt_tps", 0),
        timings.get("ollama.generation_tps", 0),
        timings.get("Retrieval", 0) * 1000,
        (timings.get("Retrieval", 0) + timings.get("Generation", 0)) * 1000,
    )
