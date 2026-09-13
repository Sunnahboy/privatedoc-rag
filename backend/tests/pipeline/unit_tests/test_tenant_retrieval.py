from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.pipeline.chunking.models import Chunk
from app.pipeline.indexing.tantivy_indexer import TantivyIndexer
from app.pipeline.retrieval.bm25_retriever import BM25Retriever
from app.pipeline.retrieval.qdrant_retriever import QdrantRetriever


@pytest.mark.asyncio
async def test_qdrant_retrieval_always_adds_user_filter():
    """A missing document scope must not remove the tenant scope."""
    embedder = AsyncMock()
    embedder.embed_query.return_value = [0.1, 0.2]
    retriever = QdrantRetriever(embedder=embedder)
    retriever.client.query_points = AsyncMock(
        return_value=SimpleNamespace(points=[])
    )

    await retriever.retrieve(query="architecture", user_id="tenant-a", top_k=3)

    query_filter = retriever.client.query_points.await_args.kwargs["query_filter"]
    assert len(query_filter.must) == 1
    assert query_filter.must[0].key == "user_id"
    assert query_filter.must[0].match.value == "tenant-a"
    await retriever.close()


@pytest.mark.asyncio
async def test_qdrant_retrieval_combines_user_and_document_filters():
    """Document selection narrows, but never substitutes for, tenant isolation."""
    embedder = AsyncMock()
    embedder.embed_query.return_value = [0.1, 0.2]
    retriever = QdrantRetriever(embedder=embedder)
    retriever.client.query_points = AsyncMock(
        return_value=SimpleNamespace(points=[])
    )

    await retriever.retrieve(
        query="architecture",
        user_id="tenant-a",
        document_ids=["doc-1", "doc-2"],
    )

    query_filter = retriever.client.query_points.await_args.kwargs["query_filter"]
    assert [condition.key for condition in query_filter.must] == [
        "user_id",
        "document_id",
    ]
    assert query_filter.must[1].match.any == ["doc-1", "doc-2"]
    await retriever.close()


@pytest.mark.asyncio
async def test_bm25_passes_user_id_to_tantivy():
    index = AsyncMock()
    index.search.return_value = []
    retriever = BM25Retriever(index=index)

    await retriever.retrieve(
        query="architecture",
        user_id="tenant-a",
        document_ids=["doc-1"],
    )

    index.search.assert_awaited_once_with(
        query="architecture",
        top_k=5,
        user_id="tenant-a",
        document_ids=["doc-1"],
    )


@pytest.mark.asyncio
async def test_tantivy_search_returns_only_the_request_tenant(tmp_path):
    index = TantivyIndexer(index_path=str(tmp_path / "tantivy"))
    shared_text = "fault tolerant architecture"

    await index.add_documents(
        [
            Chunk(
                chunk_id="chunk-a",
                document_id="doc-a",
                chunk_index=0,
                text=shared_text,
                start_char=0,
                end_char=len(shared_text),
            )
        ],
        user_id="tenant-a",
    )
    await index.add_documents(
        [
            Chunk(
                chunk_id="chunk-b",
                document_id="doc-b",
                chunk_index=0,
                text=shared_text,
                start_char=0,
                end_char=len(shared_text),
            )
        ],
        user_id="tenant-b",
    )

    results = await index.search(
        query="fault tolerant",
        top_k=10,
        user_id="tenant-a",
    )

    assert [chunk.chunk_id for chunk in results] == ["chunk-a"]
    await index.close()
