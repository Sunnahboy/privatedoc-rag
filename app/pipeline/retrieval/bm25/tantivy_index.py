from pathlib import Path

from app.config import settings
from tantivy import Index, SchemaBuilder

from .base import BaseSparseIndex
from app.pipeline.chunking.models import Chunk


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
            self.index = Index.open(self.index_path)
        else:
            self.index = Index(self.schema, path=self.index_path)

    async def add_documents(self, chunks)->None:
        for chunk in chunks:
            self.writer.add_document(
                self.schema.parse_document(
                    {
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.chunk_id,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,

                    }
                )
            )
        self.writer.commit()
        self.searcher = self.index.searcher()

    async def search(
        self,
        query: str,
        top_k: int,
    ): ...

    async def delete_document(
        self,
        document_id: str,
    ): ...

    async def close(self):
        pass
