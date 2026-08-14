from pathlib import Path

from app.config import settings
from app.pipeline.chunking.models import Chunk
from app.pipeline.retrieval.models import RetrievedChunk
from app.utils.logging_utils import logging
from tantivy import Document, Index, SchemaBuilder
from tenacity import retry, stop_after_attempt, wait_random_exponential

from .interface import BaseSparseIndex


class TantivyIndexer(BaseSparseIndex):
    def __init__(
        self,
        index_path: str | None = None,
    ):
        self.index_path = Path(index_path or settings.tantivy_index_path)

        self.index = None

        builder = SchemaBuilder()

        self.document_id = builder.add_text_field(
            "document_id",
            stored=True,
            tokenizer_name="raw",
        )
        self.chunk_id = builder.add_text_field(
            "chunk_id",
            stored=True,
            tokenizer_name="raw",
        )
        self.chunk_index = builder.add_integer_field("chunk_index", stored=True)
        self.text = builder.add_text_field("text", stored=True)

        self.schema = builder.build()

        self.index_path.mkdir(parents=True, exist_ok=True)

        meta_file = self.index_path / "meta.json"

        if meta_file.exists():
            self.index = Index.open(str(self.index_path))
        else:
            self.index = Index(
                self.schema,
                path=str(self.index_path),
            )

        self.searcher = self.index.searcher()

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_random_exponential(multiplier=1, max=10),
        reraise=True,
    )
    async def add_documents(
        self,
        chunks: list[Chunk],
    ) -> None:
        """converts  domain model (Chunk) into Tantivy documents.
        - writes them to the index,
        - After commit(), the documents become searchable,
        - A new Searcher  queries  latest index."""
        writer = self.index.writer()
        for chunk in chunks:
            doc = Document(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
            )
            writer.add_document(doc)
        writer.commit()
        self.index.reload()
        self.searcher = self.index.searcher()

    async def search(
        self,
        query: str,
        top_k: int,
        document_id: str | None = None,
    ) -> list[RetrievedChunk]:
        if document_id:
            query = f"document_id:{document_id} AND ({query})"
        if self.searcher is None:
            self.searcher = self.index.searcher()
        query_parser, errors = self.index.parse_query_lenient(
            query,
            ["document_id", "text"],
        )

        if errors:
            logging.debug("Tantivy query parser recovered from: %s", errors)
        hits = self.searcher.search(
            query_parser,
            limit=top_k,
        )
        results: list[RetrievedChunk] = []
        for score, doc_address in hits.hits:
            doc = self.searcher.doc(doc_address)
            results.append(
                RetrievedChunk(
                    chunk_id=doc["chunk_id"][0],
                    document_id=doc["document_id"][0],
                    chunk_index=doc["chunk_index"][0],
                    text=doc["text"][0],
                    score=score,
                )
            )
        return results

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_random_exponential(multiplier=1, max=10),
        reraise=True,
    )
    async def delete_document(
        self,
        document_id: str,
    ) -> None:
        # acquire the lock when deleting as well
        writer = self.index.writer()
        writer.delete_documents(
            "document_id",
            document_id,
        )
        writer.commit()
        self.index.reload()
        self.searcher = self.index.searcher()

    async def close(self):
        self.writer = None
        self.searcher = None
        self.index = None
