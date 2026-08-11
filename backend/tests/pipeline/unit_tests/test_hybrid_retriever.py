from unittest.mock import AsyncMock, Mock

import pytest
from app.config import settings
from app.pipeline.retrieval.exceptions import RetrievalError, SearchError
from app.pipeline.retrieval.hybrid_retriever import HybridRetriever
from app.pipeline.retrieval.models import RetrievalResult, RetrievedChunk


def chunk(chunk_id: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id="doc1",
        chunk_index=0,
        text=f"Chunk {chunk_id}",
        score=1.0,
    )


@pytest.fixture
def dense():
    return AsyncMock()


@pytest.fixture
def sparse():
    return AsyncMock()


@pytest.fixture
def fusion():
    return Mock()


@pytest.fixture
def hybrid(dense, sparse, fusion):
    return HybridRetriever(
        dense=dense,
        sparse=sparse,
        fusion=fusion,
    )


@pytest.mark.asyncio
async def test_successful_hybrid_retrieval(
    hybrid,
    dense,
    sparse,
    fusion,
):
    dense.retrieve.return_value = RetrievalResult(
        chunks=[chunk("A"), chunk("B")],
        found=True,
    )

    sparse.retrieve.return_value = RetrievalResult(
        chunks=[chunk("B"), chunk("C")],
        found=True,
    )

    fusion.fuse.return_value = [
        chunk("B"),
        chunk("A"),
        chunk("C"),
    ]

    result = await hybrid.retrieve(
        query="software architecture",
        top_k=3,
    )

    assert result.found
    assert len(result.chunks) == 3

    dense.retrieve.assert_awaited_once()
    sparse.retrieve.assert_awaited_once()
    fusion.fuse.assert_called_once()


@pytest.mark.asyncio
async def test_empty_query_raises(hybrid):
    with pytest.raises(RetrievalError):
        await hybrid.retrieve("")


@pytest.mark.asyncio
@pytest.mark.parametrize("top_k", [0, -1])
async def test_invalid_top_k_raises(
    hybrid,
    top_k,
):
    with pytest.raises(RetrievalError):
        await hybrid.retrieve(
            "query",
            top_k=top_k,
        )


@pytest.mark.asyncio
async def test_dense_failure_propagates(
    hybrid,
    dense,
    sparse,
):
    dense.retrieve.side_effect = SearchError("Dense retrieval failed.")

    sparse.retrieve.return_value = RetrievalResult(
        chunks=[],
        found=False,
    )

    with pytest.raises(SearchError):
        await hybrid.retrieve("query")


@pytest.mark.asyncio
async def test_sparse_failure_propagates(
    hybrid,
    dense,
    sparse,
):
    dense.retrieve.return_value = RetrievalResult(
        chunks=[],
        found=False,
    )

    sparse.retrieve.side_effect = SearchError("Sparse retrieval failed.")

    with pytest.raises(SearchError):
        await hybrid.retrieve("query")


@pytest.mark.asyncio
async def test_both_empty(
    hybrid,
    dense,
    sparse,
    fusion,
):
    dense.retrieve.return_value = RetrievalResult(
        chunks=[],
        found=False,
    )

    sparse.retrieve.return_value = RetrievalResult(
        chunks=[],
        found=False,
    )

    fusion.fuse.return_value = []

    result = await hybrid.retrieve("query")

    assert not result.found
    assert result.chunks == []


@pytest.mark.asyncio
async def test_top_k_limiting(
    hybrid,
    dense,
    sparse,
    fusion,
):
    dense.retrieve.return_value = RetrievalResult(
        chunks=[],
        found=False,
    )

    sparse.retrieve.return_value = RetrievalResult(
        chunks=[],
        found=False,
    )

    fusion.fuse.return_value = [chunk(str(i)) for i in range(20)]

    result = await hybrid.retrieve(
        "query",
        top_k=5,
    )

    assert len(result.chunks) == 5


@pytest.mark.asyncio
async def test_document_id_propagated(
    hybrid,
    dense,
    sparse,
    fusion,
):
    dense.retrieve.return_value = RetrievalResult(
        chunks=[],
        found=False,
    )

    sparse.retrieve.return_value = RetrievalResult(
        chunks=[],
        found=False,
    )

    fusion.fuse.return_value = []

    await hybrid.retrieve(
        query="fault tolerance",
        document_id="doc123",
    )
    expected_top_k = settings.top_k_search * settings.hybrid_candidate_multiplier
    dense.retrieve.assert_awaited_once_with(
        query="fault tolerance",
        top_k=expected_top_k,
        document_id="doc123",
    )

    sparse.retrieve.assert_awaited_once_with(
        query="fault tolerance",
        top_k=expected_top_k,
        document_id="doc123",
    )


@pytest.mark.asyncio
async def test_close_closes_dependencies(
    hybrid,
    dense,
    sparse,
):
    await hybrid.close()

    dense.close.assert_awaited_once()
    sparse.close.assert_awaited_once()
