from pathlib import Path

from app.config import settings
from app.pipeline.chunking.models import Chunk
from app.pipeline.retrieval.models import RetrievedChunk
from tantivy import Document, Index, SchemaBuilder

from .base import BaseSparseIndex


class TantivyIndex(BaseSparseIndex):
    def __init__(
        self,
        index_path: str | None = None,
    ):
        self.index_path = Path(index_path or settings.tantivy_index_path)

        self.index = None
        self.writer = None
        builder = SchemaBuilder()

        self.document_id = builder.add_text_field("document_id", stored=True)
        self.chunk_id = builder.add_text_field("chunk_id", stored=True)
        self.chunk_index = builder.add_integer_field("chunk_index", stored=True)
        self.text = builder.add_text_field("text", stored=True)

        self.schema = builder.build()

        self.index_path.mkdir(parents=True, exist_ok=True)

        if self.index_path.exists() and any(self.index_path.iterdir()):
            self.index = Index.open(str(self.index_path))
        else:
            self.index = Index(
                self.schema,
                path=str(self.index_path),
            )
        self.writer = self.index.writer()
        self.searcher = self.index.searcher()

    async def add_documents(
        self,
        chunks: list[Chunk],
    ) -> None:
        """converts  domain model (Chunk) into Tantivy documents.
        - writes them to the index,
        - After commit(), the documents become searchable,
        - A new Searcher  queries  latest index."""
        for chunk in chunks:
            doc = Document(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
            )
            self.writer.add_document(doc)
        self.writer.commit()
        self.index.reload()
        self.searcher = self.index.searcher()

    async def search(
        self,
        query: str,
        top_k: int,
    ) -> list[RetrievedChunk]:
        if self.searcher is None:
            self.searcher = self.index.searcher()
        query_parser = self.index.parse_query(
            query,
            ["text"],
        )
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

    async def delete_document(
        self,
        document_id: str,
    ):
        raise NotImplementedError

    async def close(self):
        self.writer = None
        self.searcher = None
        self.index = None
