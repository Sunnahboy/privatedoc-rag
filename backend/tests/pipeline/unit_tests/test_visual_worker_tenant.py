from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.pipeline.detector.models import DocumentVisualJobMessage, PageClassification
from app.workers import visual_worker


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, traceback):
        return None


class _Vector:
    def tolist(self):
        return [[0.1, 0.2]]


def _message(user_id: str = "tenant-a"):
    payload = DocumentVisualJobMessage(
        document_id="doc-1",
        page_number=1,
        classification=PageClassification.VISUAL_RICH,
        reasons=["diagram"],
        signals={},
        user_id=user_id,
    )
    return SimpleNamespace(
        body=payload.model_dump_json().encode(),
        ack=AsyncMock(),
        reject=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_visual_worker_queries_document_with_tenant_lock(monkeypatch):
    session = SimpleNamespace(
        execute=AsyncMock(
            return_value=SimpleNamespace(
                scalars=lambda: SimpleNamespace(first=lambda: None)
            )
        )
    )
    monkeypatch.setattr(
        visual_worker, "AsyncSessionLocal", lambda: _SessionContext(session)
    )

    message = _message()
    await visual_worker.VisualWorker().process_job(message)

    statement = session.execute.await_args.args[0]
    assert "documents.user_id" in str(statement)
    message.reject.assert_awaited_once_with(requeue=False)


@pytest.mark.asyncio
async def test_visual_worker_stamps_tenant_on_qdrant_point(tmp_path, monkeypatch):
    stored_filename = "doc-1.pdf"
    (tmp_path / stored_filename).touch()
    document = SimpleNamespace(stored_filename=stored_filename)
    session = SimpleNamespace(
        execute=AsyncMock(
            return_value=SimpleNamespace(
                scalars=lambda: SimpleNamespace(first=lambda: document)
            )
        )
    )
    monkeypatch.setattr(
        visual_worker, "AsyncSessionLocal", lambda: _SessionContext(session)
    )
    monkeypatch.setattr(visual_worker, "ensure_upload_dir", lambda: tmp_path)
    monkeypatch.setattr(visual_worker, "render_pdf_page_to_image", Mock())

    worker = visual_worker.VisualWorker()
    worker.visual_engine = SimpleNamespace(embed_image=AsyncMock(return_value=_Vector()))
    worker.qdrant_client = SimpleNamespace(upsert=AsyncMock())

    message = _message()
    await worker.process_job(message)

    point = worker.qdrant_client.upsert.await_args.kwargs["points"][0]
    assert point.payload["user_id"] == "tenant-a"
    assert point.payload["document_id"] == "doc-1"
    message.ack.assert_awaited_once()
