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
    context_chunks: int,
) -> None:
    logger.info(
        """
==================== RAG PROFILING ====================

Retrieval
├── Query Embedding : %7.2f ms
├── Qdrant Search   : %7.2f ms
├── Sparse Search   : %7.2f ms
└── RRF Fusion      : %7.2f ms

Generation
├── Context Chunks  : %7d
├── Time            : %7.2f ms
├── Load            : %7.2f ms
├── Prompt Eval     : %7.2f ms
├── Token Eval      : %7.2f ms
├── Prompt Tokens   : %7.0f
├── Output Tokens   : %7.0f
├── Prompt TPS      : %7.2f
└── Generate TPS    : %7.2f

-------------------------------------------------------
Retrieval Total     : %7.2f ms
Request Total       : %7.2f ms
=======================================================
""",
        timings.get("Query Embedding", 0) * 1000,
        timings.get("Qdrant Search", 0) * 1000,
        timings.get("Sparse Search", 0) * 1000,
        timings.get("RRF Fusion", 0) * 1000,
        context_chunks,
        timings.get("Generation", 0) * 1000,
        timings.get("ollama.load", 0) * 1000,
        timings.get("ollama.prompt_eval", 0) * 1000,
        timings.get("ollama.eval", 0) * 1000,
        timings.get("ollama.prompt_tokens", 0),
        timings.get("ollama.completion_tokens", 0),
        timings.get("ollama.prompt_tps", 0),
        timings.get("ollama.generation_tps", 0),
        timings.get("Retrieval", 0) * 1000,
        (timings.get("Retrieval", 0) + timings.get("Generation", 0)) * 1000,
    )
