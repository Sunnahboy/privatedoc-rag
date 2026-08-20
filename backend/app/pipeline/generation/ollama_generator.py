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

import logging

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
    
    async def generate(
        self,
        question: str,
        context: list[RetrievedChunk],
        images: list[Image.Image] | None = None,
    ) -> GenerateResult:

        active_template = MULTIMODAL_TEMPLATE if images else TEXT_TEMPLATE
        prompt_builder= PromptBuilder(active_template)
        prompt = prompt_builder.build(
            question=question,
            context=context,
            
        )

        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "keep_alive": "15m",
            "options": {
                "num_ctx": 8192,
                "num_predict": 1024,
            },
        }

        if images:
            logger.info(
            "Multimodal Request: Attaching %d rendered page image(s) to model '%s'",
            len(images),
            self.model,
    )
            tasks = [asyncio.to_thread(self._to_base64, img) for img in images]
            base64_images = await asyncio.gather(*tasks)
            payload["images"] = base64_images
        else:
            logger.info("Text-Only Request: Querying model '%s'", self.model)
        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            record_ollama_metrics(data)

        except httpx.HTTPStatusError as exc:
            raise GenerationError(exc.response.json()["error"]) from exc

        except httpx.HTTPError as exc:
            raise GenerationError("Failed to communicate with Ollama.") from exc

        return GenerateResult(
            answer=data["response"],
            citations=context,
            prompt_tokens=data["prompt_eval_count"],
            completion_tokens=data["eval_count"],
            prompt_chars=len(prompt),
        )
