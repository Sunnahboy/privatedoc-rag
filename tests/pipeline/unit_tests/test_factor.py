import httpx
import pytest
from app.pipeline.embeddings.exception import EmbeddingResponseError
from app.pipeline.embeddings.factory import create_embedder
from app.pipeline.embeddings.ollama_emdedder import OllamaEmbedder


def test_factory_returns_ollama_embedder():
    embedder = create_embedder()

    assert isinstance(embedder, OllamaEmbedder)


def test_split_batches_uses_embedder_batch_size():
    embedder = OllamaEmbedder(batch_size=2)
    chunks = [object() for _ in range(5)]

    batches = embedder._split_batches(chunks)

    assert [len(batch) for batch in batches] == [2, 2, 1]


@pytest.mark.asyncio
async def test_embed_batch_includes_response_body_in_error(monkeypatch):
    embedder = OllamaEmbedder()
    error_text = '{"error":"input too large"}'

    class FakeClient:
        async def post(self, url, json):
            response = httpx.Response(
                400,
                request=httpx.Request("POST", url),
                text=error_text,
            )
            raise httpx.HTTPStatusError(
                "Ollama returned an error",
                request=response.request,
                response=response,
            )

    monkeypatch.setattr(embedder, "_get_client", lambda: FakeClient())

    with pytest.raises(EmbeddingResponseError, match="input too large"):
        await embedder._embed_batch(["hello"])
