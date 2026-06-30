import logging
import sys


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