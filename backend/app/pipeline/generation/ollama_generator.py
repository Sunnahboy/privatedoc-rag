import httpx
from app.config import settings
from app.pipeline.retrieval.models import RetrievedChunk
from app.utils.profiler import record_ollama_metrics
import base64
from io import BytesIO
from PIL import Image
from .exceptions import GenerationError
from .interface import BaseGenerator
from .models import GenerateResult
from .prompt_builder import PromptBuilder
import asyncio
from app.models.chat import ChatMessage
import logging
import json
from typing import AsyncGenerator
logger = logging.getLogger(__name__)
TEXT_TEMPLATE = """You are an expert technical assistant. Answer the question directly using the provided context.

<context>
{context}
</context>

Instructions:
1. Base your answer primarily on the context. Connect related ideas across chunks.
2. If the context does not contain the answer, explicitly state: "The provided documents do not contain this information." before adding general knowledge.
3. Structure your response using Markdown (bullet points, bold text, code blocks).
4. Do not use conversational filler or greetings.

Prior Conversation:
{chat_history}

<context>
{context}
</context>

Question:
{question}

Answer:"""

MULTIMODAL_TEMPLATE = """You are an expert technical assistant. Answer the question using the text context and attached document images.

<context>
{context}
</context>

Instructions:
1. For charts, tables, diagrams, and code snippets, read values and syntax directly from the visual images as the primary source of truth.
2. Synthesize facts across text chunks and images seamlessly.
3. Structure your answer using Markdown with proper headings, lists, and code blocks.
4. Do not use conversational preamble.

Prior Conversation:
{chat_history}

<context>
{context}
</context>

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
        self.model = settings.generation_model
        self.timeout = settings.generation_timeout

        self.client = httpx.AsyncClient(
            timeout=self.timeout,
        )

    async def close(self) -> None:
        await self.client.aclose()
    @staticmethod
    def _to_base64(img: Image.Image, format: str = "JPEG", quality: int = 85) -> str:
    # Ensure RGB mode for JPEG encoding
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
            
    )->AsyncGenerator[dict, None]:
        """Core generation method: streams response from llm token by token."""
        active_template = MULTIMODAL_TEMPLATE if images else TEXT_TEMPLATE
        prompt_builder = PromptBuilder(active_template)
        prompt = prompt_builder.build(
            question=question,
            context=context,
            chat_history=chat_history,
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_ctx": 8192,
                "num_predict": 1024,
            },
        }

        if images:
            logger.info("Multimodal Stream: Attaching %d image(s)", len(images))
            tasks = [asyncio.to_thread(self._to_base64, img) for img in images]
            payload["images"] = await asyncio.gather(*tasks)

        try:
            async with self.client.stream(
                "POST", 
                f"{self.base_url}/api/generate", 
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        if not data.get("done"):
                            yield {
                                "type": "token",
                                "content": data.get("response", "")
                            }
                        else:
                            record_ollama_metrics(data)
                            
                            citations_dict = [
                                {
                                    "text": chunk.text, 
                                    "score": chunk.score, 
                                    "chunk_index": chunk.chunk_index
                                } for chunk in context
                            ]
                            
                            yield {
                                "type": "done",
                                "citations": citations_dict,
                                "prompt_tokens": data.get("prompt_eval_count", 0),
                                "completion_tokens": data.get("eval_count", 0),
                                "prompt_chars": len(prompt)
                            }
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse streaming line from Ollama: {line}")
                        continue

        except httpx.HTTPStatusError as exc:
            raise GenerationError(exc.response.json().get("error", "Unknown error")) from exc
        except httpx.HTTPError as exc:
            raise GenerationError("Failed to communicate with Ollama during stream.") from exc

    
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
        async for chunk in self.generate_stream(question, context, images, chat_history):
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
