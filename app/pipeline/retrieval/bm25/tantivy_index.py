from pathlib import Path

from app.config import settings

from .base import BaseSparseIndex


class TantivyIndex(BaseSparseIndex):
    def __init__(
        self,
        index_path: str | None = None,
    ):
        self.index_path = Path(
            index_path or settings.tantivy_index_path
        )

        self.index = None
        self.writer = None
        self.searcher = None

    async def add_documents(self, chunks):
        ...

    async def search(
        self,
        query: str,
        top_k: int,
    ):
        ...

    async def delete_document(
        self,
        document_id: str,
    ):
        ...

    async def close(self):
        pass