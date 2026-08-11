import logging

logger = logging.getLogger(__name__)


class IngestionLogger:
    @staticmethod
    def benchmark(
        document_id: str,
        timings: dict[str, float],
        total: float,
        chunks: int,
    ) -> None:
        throughput = chunks / total if total else 0

        logger.info(
            "\n"
            "========== INGESTION ==========\n"
            "Document   : %s\n"
            "Extraction : %.3fs\n"
            "Cleaning   : %.3fs\n"
            "Chunking   : %.3fs\n"
            "Embedding  : %.3fs\n"
            "Indexing   : %.3fs\n"
            "Total      : %.3fs\n"
            "Throughput : %.2f chunks/sec\n"
            "==============================",
            document_id,
            timings.get("extraction", 0),
            timings.get("cleaning", 0),
            timings.get("chunking", 0),
            timings.get("embedding", 0),
            timings.get("indexing", 0),
            total,
            throughput,
        )

    @staticmethod
    def error(document_id: str) -> None:
        logger.exception(
            "Failed ingesting document '%s'",
            document_id,
        )

    @staticmethod
    def close_error(component: object) -> None:
        logger.exception(
            "Failed closing %s",
            component.__class__.__name__,
        )
