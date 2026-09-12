# app/pipeline/indexing/composite_indexer.py

import asyncio

from .models import IndexingRequest, IndexingResult
from .qdrant_indexer import QdrantIndexer
from .tantivy_indexer import TantivyIndexer


class CompositeIndexer:
    """Coordinates indexing into multiple backends, enforcing tenant boundaries."""

    def __init__(
        self,
        vector_indexer: QdrantIndexer | None = None,
        sparse_indexer: TantivyIndexer | None = None,
    ):
        self.vector_indexer = vector_indexer or QdrantIndexer()
        self.sparse_indexer = sparse_indexer or TantivyIndexer()

    async def index(
        self,
        request: IndexingRequest,
    ) -> IndexingResult:
        # IDENTITY INJECTION: Extract user_id from the request and pass to Tantivy.
        # QdrantIndexer will extract it internally from the same request object.
        vector_result, _ = await asyncio.gather(
            self.vector_indexer.index(request),
            self.sparse_indexer.add_documents(
               chunks = request.chunks,
               user_id =request.user_id
                ),
        )

        # Return the vector indexing result for compatibility
        return vector_result

    async def delete_document(
        self,
        document_id: str,
        user_id:str,
    ) -> None:
        await asyncio.gather(
            self.vector_indexer.delete_document(
                document_id= document_id,
                user_id=user_id,
                ),
            self.sparse_indexer.delete_document(
                document_id=document_id,
                user_id=user_id,
                ),
        )

    async def close(self) -> None:
        await asyncio.gather(
            self.vector_indexer.close(),
            self.sparse_indexer.close(),
            return_exceptions=True,
        )
