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

    def __init__(
        self,
        *,
        batch_size: int | None = None,
        max_concurrency: int | None = None,
    ) -> None:
        self.base_url = settings.ollama_url.strip("/")
        self.model = settings.embedding_model
        self.timeout = settings.embedding_timeout

        self.batch_size = (
            batch_size if batch_size is not None else settings.embedding_batch_size
        )

        self.max_concurrency = (
            max_concurrency
            if max_concurrency is not None
            else settings.embedding_max_concurrency
        )

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

    def _split_batches(
        self,
        chunks: list[Chunk],
    ) -> list[list[Chunk]]:
        """Split chunks into fixed-size batches."""
        batch_size = self.batch_size

        return [chunks[i : i + batch_size] for i in range(0, len(chunks), batch_size)]

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddingResult]:
        """
        Generate embeddings for all chunks,
            -split batches
            -run tasks
            -combine results
        """

        if not chunks:
            return []

        # call all http requests concurrently using asyncio.gather
        batches = self._split_batches(chunks)
        # Process batches concurrently, but limit how many tasks are active at once
        # to prevent overloading Ollama's internal connection pool on massive documents.
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def bounded_process(batch: list[Chunk]) -> list[EmbeddingResult]:
            async with semaphore:
                return await self._process_batch(batch)

        # create onee task per batch
        tasks = [self._process_batch(batch) for batch in batches]
        batch_vectors = await asyncio.gather(*tasks)

        return [result for batch in batch_vectors for result in batch]

    async def embed_query(self, query: str) -> list[float]:
        """Generate user query embeddings"""
        vectors = await self._embed_batch([query])
        return vectors[0]

    async def _embed_batch(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        Generate an embedding for a single piece of text
            -HTTP request only
        """

        url = f"{self.base_url}/api/embed"

        payload = {
            "model": self.model,
            "input": texts,
        }
        client = self._get_client()

        async with self._semaphore:
            try:
                print(
                    f"Sending batch: {len(texts)} texts, "
                    f"{sum(len(text) for text in texts)} characters"
                )
                # connection pooling: to avoid constant TCP handshake
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

            except httpx.RequestError as exc:
                raise EmbeddingResponseError("Failed to connect to ollama.") from exc
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text.strip() if exc.response is not None else ""
                raise EmbeddingResponseError(
                    f"Ollama API returned {exc.response.status_code}: {detail}"
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

        return embeddings

    async def _process_batch(
        self,
        batch: list[Chunk],
    ) -> list[EmbeddingResult]:
        """
        Process a single batch of chunks.
            -extract text
            -call Ollama
            -build EmbeddingResult
        """
        texts = [chunk.text for chunk in batch]
        vectors = await self._embed_batch(texts)

        results: list[EmbeddingResult] = []

        for chunk, vector in zip(batch, vectors, strict=True):
            results.append(
                EmbeddingResult(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    vector=vector,
                    model_name=self.model,
                    dimensions=len(vector),
                )
            )
        print(f"Processing batch {batch[0].chunk_index} - {batch[-1].chunk_index}")
        return results
