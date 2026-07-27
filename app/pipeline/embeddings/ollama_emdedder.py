import httpx
from app.config import settings
from app.pipeline.chunking.models import Chunk

from .base import BaseEmbedder
from .exception import EmbeddingResponseError
from .models import EmbeddingResult


class OllamaEmbedder(BaseEmbedder):
    """
    Generates embeddings using a local Ollama model.
    """

    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.strip("/")
        self.model = settings.embedding_model
        self.timeout = settings.embedding_timeout

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddingResult]:
        results: list[EmbeddingResult] = []
        for chunk in chunks:
            vector = await self._embed_text(chunk.text)

            results.append(
                EmbeddingResult(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    vector=vector,
                    model_name=self.model,
                    dimensions=len(vector),#source of truth is the vector returned by the model.
                )
            )

            return results

    async def _embed_text(
        self,
        text: str,
    ) -> list[float]:
        """Generate an embedding for a single piece of text"""
        url = f"{self.base_url}/api/embed"

        payload = {
            "model": self.model,
            "input": text,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        except httpx.CloseError as exc:
            raise EmbeddingResponseError("Failed to connect to ollama.") from exc
        except httpx.HTTPError:
            raise EmbeddingResult("Missing 'embeddings' field in response.")
        embeddings = data["embeddings"]

        if not embeddings or not isinstance(embeddings, list):
            raise EmbeddingResponseError("Invalid embedding response.")
        return embeddings[0]
