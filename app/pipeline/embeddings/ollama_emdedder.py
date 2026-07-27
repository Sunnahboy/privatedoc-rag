import asyncio

import httpx
from app.config import settings
from app.pipeline.chunking.models import Chunk

from .base import BaseEmbedder
from .exception import EmbeddingResponseError
from .models import EmbeddingResult


class OllamaEmbedder(BaseEmbedder):
    """
    Generates embeddings using a local Ollama model efficiently and concurrently.
    """

    def __init__(self) -> None:
        self.base_url = settings.ollama_url.strip("/")
        self.model = settings.embedding_model
        self.timeout = settings.embedding_timeout
        # Maximum concurrent requests to Ollama
        self.max_concurrency = settings.embedding_max_concurrency
        # Persistent client to maintain connection pooling across requests
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

    def _get_client(self) -> httpx.AsyncClient:
        """ "Lazy-loads a single reusable HTTP client instance."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Closes the underlying client connection pool when done."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddingResult]:
        """
        Processes all chunks concurrently and maps them to EmbeddingResult objects,
        """

        if not chunks:
            return []

        # call all http requests concurrently using asyncio.gather
        tasks = [self._embed_text(chunk.text) for chunk in chunks]
        vectors = await asyncio.gather(*tasks)

        results: list[EmbeddingResult] = []
        for chunk, vector in zip(chunks, vectors):
            results.append(
                EmbeddingResult(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    vector=vector,
                    model_name=self.model,
                    dimensions=len(vector),  # Vector returned is the source of truth
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
        client = self._get_client()

        async with self._semaphore:
            try:
                # connection pooling: to avoid constant TCP handshake
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

            except httpx.CloseError as exc:
                raise EmbeddingResponseError("Failed to connect to ollama.") from exc
            except httpx.HTTPStatusError as exc:
                raise EmbeddingResponseError(
                    f"Ollama API returned an error status code: {exc.response.status_code}"
                ) from exc
            except (httpx.HTTPError, ValueError) as exc:
                raise EmbeddingResponseError(
                    "Network communication or JSON parsing failed."
                ) from exc

            # Securely validate schema inside safe bounds
            if "embeddings" not in data:
                raise EmbeddingResponseError(
                    "Missing 'embeddings' field in Ollama response."
                )
            embeddings = data["embeddings"]

        if not embeddings or not isinstance(embeddings, list):
            raise EmbeddingResponseError(
                "Invalid embedding response returned by ollama."
            )
        return embeddings[0]
