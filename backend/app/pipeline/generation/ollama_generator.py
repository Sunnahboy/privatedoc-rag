import httpx
from app.config import settings
from app.pipeline.retrieval.models import RetrievedChunk
from app.utils.profiler import record_ollama_metrics

from .exceptions import GenerationError
from .interface import BaseGenerator
from .models import GenerateResult
from .prompt_builder import PromptBuilder

DEFAULT_TEMPLATE = """
Context information is below.

Context:
{context}
Use only information supported by the context.
Do not add general explanations, interpretations, or conclusions that are not explicitly supported by the context.
Avoid unnecessary repetition and use the source's terminology for technical conclusions.
Include only information necessary to answer the question.
Given the context information and not prior knowledge, answer the query.

Question:
{question}

Answer:
"""


class OllamaGenerator(BaseGenerator):
    def __init__(
        self,
        template: str = DEFAULT_TEMPLATE,
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

    async def generate(
        self,
        question: str,
        context: list[RetrievedChunk],
    ) -> GenerateResult:
        prompt = self.prompt_builder.build(
            question=question,
            context=context,
        )
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "keep_alive": "30m",
            "options": {
                "num_predict": 256,
            },
        }
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
