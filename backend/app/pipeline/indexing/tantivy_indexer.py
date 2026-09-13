import re
from pathlib import Path

from tantivy import Document, Index, SchemaBuilder
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.config import settings
from app.pipeline.chunking.models import Chunk
from app.pipeline.retrieval.models import RetrievedChunk
from app.utils.logging_utils import logging

from .interface import BaseSparseIndex


def _escape_query_literal(value: str) -> str:
    """Escape a value embedded in a quoted Tantivy query literal."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


class TantivyIndexer(BaseSparseIndex):
    def __init__(
        self,
        index_path: str | None = None,
    ):
        self.index_path = Path(index_path or settings.tantivy_index_path)

        self.index = None

        builder = SchemaBuilder()
        # Tenant IDs are indexed as exact raw tokens, never analyzed text.
        self.user_id = builder.add_text_field(
            "user_id",
            stored=True,
            tokenizer_name="raw",
        )

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
        self.page_number = builder.add_integer_field("page_number", stored=True)

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
        self._assert_tenant_schema()

    def _assert_tenant_schema(self) -> None:
        """Refuse an old sparse index that has no tenant field.

        Tantivy schemas are immutable. Silently opening an index produced by
        the single-tenant schema would make the mandatory tenant query invalid
        (or tempt a caller to issue an unscoped fallback). Operators must
        rebuild that index from tenant-stamped source documents instead.
        """
        try:
            self.index.parse_query_lenient('user_id:"schema-check"', ["user_id"])
        except ValueError as exc:
            raise RuntimeError(
                "The Tantivy index lacks the required user_id field. "
                "Rebuild it from tenant-stamped documents before serving search."
            ) from exc

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_random_exponential(multiplier=1, max=10),
        reraise=True,
    )
    async def add_documents(
        self,
        chunks: list[Chunk],
        user_id: str,
    ) -> None:
        """Index chunks with their tenant ownership stamp."""
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        writer = self.index.writer()
        for chunk in chunks:
            doc = Document()
            doc.add_text("user_id", user_id)
            doc.add_text("document_id", chunk.document_id)
            doc.add_text("chunk_id", chunk.chunk_id)
            doc.add_integer("chunk_index", chunk.chunk_index)
            doc.add_text("text", chunk.text)
            if chunk.page_number is not None:
                doc.add_integer("page_number", chunk.page_number)

            writer.add_document(doc)
        writer.commit()
        self.index.reload()
        self.searcher = self.index.searcher()

    async def search(
        self,
        query: str,
        top_k: int,
        user_id: str,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        # Reload so this searcher sees segments committed by any other instance.
        self.index.reload()
        self.searcher = self.index.searcher()

        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        # Remove parser operators so only the structural clauses below decide
        # filtering. If no searchable terms remain, return no match rather
        # than parsing a user-controlled expression.
        safe_query = re.sub(r'[\+\-\&&\|!(){}[\]^"~*?:\\/]', " ", query).strip()
        if not safe_query:
            return []

        # SECURITY: Every sparse query carries an exact tenant clause. This
        # clause is programmatically constructed and ANDed with any optional
        # document selection and with the sanitized text query.
        tenant_clause = f'user_id:"{_escape_query_literal(user_id)}"'
        if document_ids:
            # Creates: document_id:"doc_1" OR document_id:"doc_2".
            # IDs are escaped because this is the final query string boundary.
            doc_or_clause = " OR ".join(
                f'document_id:"{_escape_query_literal(doc_id)}"'
                for doc_id in document_ids
            )

            final_query = f"({tenant_clause}) AND ({doc_or_clause}) AND ({safe_query})"
        else:
            final_query = f"({tenant_clause}) AND ({safe_query})"

        query_parser, errors = self.index.parse_query_lenient(
            final_query,
            # Unqualified user text can search text only; tenant and document
            # fields are available solely through the generated clauses above.
            ["text"],
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
            page_number_values = doc["page_number"]
            results.append(
                RetrievedChunk(
                    chunk_id=doc["chunk_id"][0],
                    document_id=doc["document_id"][0],
                    chunk_index=doc["chunk_index"][0],
                    text=doc["text"][0],
                    score=score,
                    page_number=page_number_values[0] if page_number_values else None,
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
        user_id: str,
    ) -> None:
        """Delete a document after the caller has verified ownership in SQL.

        tantivy-py deletes by one term here, so the database ownership check
        remains the authorization boundary for deletion.
        """
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
