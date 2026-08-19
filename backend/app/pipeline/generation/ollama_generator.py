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
TEXT_TEMPLATE = """Use the context below to answer.

<context>
{context}
</context>

Instructions:
1. Primary: Extract answers from the context. If the context contains explicit data, use it and cite page or figure.
2. Fallback: If the context lacks explicit data, state "Context lacks explicit data; using general knowledge with low/medium/high confidence" and then provide the general knowledge.
3. Visuals: Treat images and charts as primary numeric sources but ignore rendering metadata (e.g., "vector drawing coverage"). Verify chart values against nearby captions or text.
4. Format: Use Markdown with headings, bold labels, bullet lists, and code blocks for structured outputs.
5. Tone: Start immediately. Omit greetings.
Question:
{question}

Answer:
"""
MULTIMODAL_TEMPLATE = """Below is the context to use.

<context>
{context}
</context>

Instructions:
1. Visual-first but verified: Use images for numeric/chart data; cross-check captions and nearby text. Ignore chart-render metadata.
2. Extraction schema: Fill the following fields when present: multi_model_pct, models_range, deployment_percentages, country_breakdown, reasons_for_local_execution.
3. Fallback: If a field is missing, state "Field X not found in documents" then optionally provide general knowledge with a confidence tag.
4. Format: Use Markdown headings and a final JSON code block with the extracted schema.
5. Tone: Start immediately. Omit filler.

Question:
{question}

Answer:
"""



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
        effective_context = context[:2] if images else context
        prompt = prompt_builder.build(
            question=question,
            context=effective_context,
            
        )

        target_model = settings.visual_model if images else self.model
        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "keep_alive": "5m",
            "num_predict": 1024,
            "options": {
                "num_ctx": 4096,
                "num_predict": 1024,
            },
        }

        if images:
            logger.info(
            "Multimodal Request: Attaching %d rendered page image(s) to model '%s'",
            len(images),
            target_model,
    )
            tasks = [asyncio.to_thread(self._to_base64, img) for img in images]
            base64_images = await asyncio.gather(*tasks)
            payload["images"] = base64_images
        else:
            logger.info("Text-Only Request: Querying model '%s'", target_model)
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
