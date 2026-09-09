import logging

import httpx

from app.config import settings
from app.models.chat import ChatMessage

logger = logging.getLogger(__name__)

REWRITE_PROMPT = """You are a specialized query transformation engine.
Your ONLY job is to rewrite the follow-up question into a comprehensive search query incorporating ALL active document titles provided below. 
Do not drop any document names.

<context>
{chat_history}
</context>

Active Documents:
{doc_context}

Follow-up: {query}
Standalone:"""


class QueryRewriter:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.base_url = settings.ollama_url.rstrip("/")
        # Reuse Gemma 3:4b already pinned in VRAM
        self.model = settings.generation_model
        self.client = client

    async def rewrite(
        self,
        query: str,
        chat_history: list[ChatMessage] | None = None,
        document_titles: list[str] | None = None,
    ) -> str:
        # If no history exists, skip inference entirely (0ms latency penalty)
        if not chat_history:
            return query

        # Extract only the last 3-4 turns to keep prompt evaluation fast
        # Format document titles into the context if available
        # Format document titles into the context if available
        doc_context = ""
        if document_titles:
            doc_list = "\n".join([f"- {title}" for title in document_titles])
            doc_context = f"Active documents being searched:\n{doc_list}"

        recent_history = chat_history[-4:]
        formatted_history = "\n".join(
            f"{msg.role.capitalize()}: {msg.content}" for msg in recent_history
        )

        # Pass doc_context explicitly into format
        prompt = REWRITE_PROMPT.format(
            chat_history=formatted_history, query=query, doc_context=doc_context
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,  # Non-streaming for instant full-token extraction
            "keep_alive": -1,  # Keep Gemma hot in VRAM
            "options": {
                "temperature": 0.0,  # Deterministic output; eliminates creative hallucination
                "num_predict": 60,  # Search queries rarely exceed 40 tokens
                # Stop sequences force the model to halt immediately if it tries
                # to generate conversational filler like a newline or "User:"
                "stop": ["\n", "User:", "<"],
            },
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate", json=payload
            )
            response.raise_for_status()
            data = response.json()
            rewritten = data.get("response", "").strip().strip('"')

            if rewritten:
                logger.info("Rewrote query: '%s' -> '%s'", query, rewritten)
                return rewritten
            return query

        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.warning("Query rewrite network error: %s. Falling back.", e)
            return query
