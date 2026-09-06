import logging

import httpx

from app.config import settings
from app.models.chat import ChatMessage

logger = logging.getLogger(__name__)

REWRITE_PROMPT = """You are a specialized query transformation engine. 
Your ONLY job is to read a brief conversation, look at the user's vague follow-up question, and rewrite it into a standalone search query. 
Do not answer the question. Do not summarize the text. Only output the rewritten search query.

Example 1:
Conversation:
User: How does Kubernetes handle networking?
Assistant: It uses the CNI (Container Network Interface)...
Follow-up: Give me an example of that.
Standalone: Give me an example of Kubernetes CNI (Container Network Interface) networking.

Example 2:
Conversation:
{chat_history}
Follow-up: {query}
Standalone:"""


class QueryRewriter:
    def __init__(self, timeout: float = 60.0) -> None:
        self.base_url = settings.ollama_url.rstrip("/")
        # Reuse Gemma 3:4b already pinned in VRAM
        self.model = settings.generation_model
        self.client = httpx.AsyncClient(timeout=timeout)

    async def rewrite(
        self, query: str, chat_history: list[ChatMessage] | None = None
    ) -> str:
        # If no history exists, skip inference entirely (0ms latency penalty)
        if not chat_history:
            return query

        # Extract only the last 3-4 turns to keep prompt evaluation fast
        recent_history = chat_history[-4:]
        formatted_history = "\n".join(
            f"{msg.role.capitalize()}: {msg.content}" for msg in recent_history
        )

        prompt = REWRITE_PROMPT.format(chat_history=formatted_history, query=query)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,  # Non-streaming for instant full-token extraction
            "keep_alive": -1,  # Keep Gemma hot in VRAM
            "options": {
                "temperature": 0.0,  # Deterministic output; eliminates creative hallucination
                "num_predict": 40,  # Search queries rarely exceed 40 tokens
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

        except Exception:
            # Resiliency: If Ollama times out or errors, fall back to the raw query without crashing
            logger.exception(
                "Query rewrite fatally crashed! Falling back to original query."
            )
            return query

    async def close(self) -> None:
        if not self.client.is_closed:
            await self.client.aclose()
