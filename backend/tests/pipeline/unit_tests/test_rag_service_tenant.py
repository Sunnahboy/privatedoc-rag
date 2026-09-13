from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.rag_service import RAGService


def _db_with_documents(documents):
    return SimpleNamespace(
        execute=AsyncMock(
            return_value=SimpleNamespace(
                scalars=lambda: SimpleNamespace(all=lambda: documents)
            )
        )
    )


@pytest.mark.asyncio
async def test_answer_query_rejects_unowned_document_before_retrieval():
    pipeline = SimpleNamespace(search=AsyncMock())
    service = RAGService(pipeline)
    db = _db_with_documents([])

    with pytest.raises(PermissionError):
        await service.answer_query(
            document_ids=["guessed-document-id"],
            user_id="tenant-a",
            query="show me the diagram",
            db=db,
        )

    statement = db.execute.await_args.args[0]
    assert "documents.user_id" in str(statement)
    pipeline.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_answer_query_passes_tenant_and_renders_authorized_storage_key():
    document = SimpleNamespace(id="doc-1", storage_key="stored-document.pdf")
    retrieval_result = SimpleNamespace(
        has_strong_visual_match=True,
        visual_pages=[{"document_id": "doc-1", "page_number": 2}],
        fused_page_ranks=[(2, 1.0)],
        text_chunks=["retrieved text"],
    )
    pipeline = SimpleNamespace(search=AsyncMock(return_value=retrieval_result))
    service = RAGService(pipeline)
    service._render_page = Mock(return_value="rendered-image")

    response = await service.answer_query(
        document_ids=["doc-1", "doc-1"],
        user_id="tenant-a",
        query="show me the diagram",
        db=_db_with_documents([document]),
    )

    pipeline.search.assert_awaited_once_with(
        query="show me the diagram",
        document_ids=["doc-1"],
        user_id="tenant-a",
    )
    service._render_page.assert_called_once_with("stored-document.pdf", 2)
    assert response["images"] == ["rendered-image"]
