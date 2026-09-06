import asyncio
import base64
import json
import logging
from collections.abc import AsyncGenerator
from io import BytesIO

import httpx
from PIL import Image

from app.config import settings
from app.models.chat import ChatMessage
from app.pipeline.retrieval.models import RetrievedChunk
from app.utils.profiler import record_ollama_metrics

from .exceptions import GenerationError
from .interface import BaseGenerator
from .models import GenerateResult
from .prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)
TEXT_TEMPLATE = """You are an expert technical assistant. Answer directly using the provided context.

<context>
{context}
</context>

Instructions:
1. Grounding: Rely SOLELY on the provided context. No external knowledge, assumptions, or inferences.
2. Fallback: If the context lacks the answer, output EXACTLY: "The provided documents do not contain enough information to answer this question." If you can answer, NEVER output this phrase.
3. Specificity: Describe figures, tables, or sections ONLY if explicitly detailed in the context.
4. Formatting: Use structured Markdown (bullet points, bolding, code blocks).
5. Opening: Start immediately with a natural summary sentence answering the core question. Omit robotic filler like "Based on the context...".

Prior Conversation:
{chat_history}

Question:
{question}

Answer:"""


MULTIMODAL_TEMPLATE = """You are an expert technical assistant. Answer using the text context and attached images.

<context>
{context}
</context>

Instructions:
1. Grounding: Rely SOLELY on the provided text and images. No external knowledge or assumptions.
2. Visual Truth: Treat attached images as the primary source of truth for values, syntax, and charts. Do not substitute visually similar images.
3. Fallback: If the text and images lack the answer, output EXACTLY: "The provided documents do not contain enough information to answer this question." If you can answer, NEVER output this phrase.
4. Formatting: Use structured Markdown (headings, lists, code blocks).
5. Opening: Start immediately with a natural summary sentence answering the core question. Omit robotic filler like "Based on the context...".

Prior Conversation:
{chat_history}

Question:
{question}

Answer:"""


class OllamaGenerator(BaseGenerator):
    def __init__(
        self,
        template: str = TEXT_TEMPLATE,
    ):
        self.prompt_builder = PromptBuilder(template)
        self.base_url = settings.ollama_url.rstrip("/")

        # Pull both models so we can dynamically route based on payload
        self.text_model = settings.generation_model
        self.visual_model = settings.visual_model

        self.timeout = settings.generation_timeout
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def close(self) -> None:
        """Must be explicitly called by the worker when the job or process terminates."""
        if not self.client.is_closed:
            await self.client.aclose()

    @staticmethod
    def _to_base64(img: Image.Image, format: str = "JPEG", quality: int = 85) -> str:
        if format == "JPEG" and img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        buf = BytesIO()
        img.save(buf, format=format, quality=quality, optimize=False)
        return base64.b64encode(buf.getbuffer()).decode("utf-8")

    async def generate_stream(
        self,
        question: str,
        context: list[RetrievedChunk],
        images: list[Image.Image] | None = None,
        chat_history: list[ChatMessage] | None = None,
    ) -> AsyncGenerator[dict, None]:

        active_template = MULTIMODAL_TEMPLATE if images else TEXT_TEMPLATE

        # THE FIX: Dynamically route to the VLM if images are present
        active_model = self.visual_model if images else self.text_model

        prompt_builder = PromptBuilder(active_template)
        prompt = prompt_builder.build(
            question=question,
            context=context,
            chat_history=chat_history,
        )

        payload = {
            "model": active_model,
            "prompt": prompt,
            "stream": True,
            "keep_alive": -1,  # THE FIX: Pin the model in VRAM indefinitely to prevent cold-starts
            "options": {
                "num_ctx": 8192,
                "num_predict": 1024,
            },
        }

        if images:
            logger.info(
                "Multimodal Stream: Routing to %s and attaching %d image(s)",
                active_model,
                len(images),
            )
            tasks = [asyncio.to_thread(self._to_base64, img) for img in images]
            payload["images"] = await asyncio.gather(*tasks)

        try:
            async with self.client.stream(
                "POST", f"{self.base_url}/api/generate", json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        if not data.get("done"):
                            yield {"type": "token", "content": data.get("response", "")}
                        else:
                            record_ollama_metrics(data)
                            citations_dict = [
                                {
                                    "text": chunk.text,
                                    "score": chunk.score,
                                    "chunk_index": chunk.chunk_index,
                                }
                                for chunk in context
                            ]
                            yield {
                                "type": "done",
                                "citations": citations_dict,
                                "prompt_tokens": data.get("prompt_eval_count", 0),
                                "completion_tokens": data.get("eval_count", 0),
                                "prompt_chars": len(prompt),
                            }
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse streaming line from Ollama: {line}"
                        )
                        continue

        except httpx.HTTPStatusError as exc:
            raise GenerationError(
                exc.response.json().get("error", "Unknown error")
            ) from exc
        except httpx.HTTPError as exc:
            raise GenerationError(
                "Failed to communicate with Ollama during stream."
            ) from exc

    async def generate(
        self,
        question: str,
        context: list[RetrievedChunk],
        images: list[Image.Image] | None = None,
        chat_history: list[ChatMessage] | None = None,
    ) -> GenerateResult:
        """
        Non-streaming wrapper. Accumulates the stream and returns a single GenerateResult.
        """
        text_buffer: list[str] = []
        done_metadata: dict = {}

        # Consume the stream internally
        async for chunk in self.generate_stream(
            question, context, images, chat_history
        ):
            chunk_type = chunk.get("type")

            if chunk_type == "token":
                text_buffer.append(chunk.get("content", ""))
            elif chunk_type == "done":
                done_metadata = chunk

        return GenerateResult(
            answer="".join(text_buffer),
            citations=context,
            prompt_tokens=done_metadata.get("prompt_tokens", 0),
            completion_tokens=done_metadata.get("completion_tokens", 0),
            prompt_chars=done_metadata.get("prompt_chars", 0),
        )
