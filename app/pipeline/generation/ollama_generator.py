import httpx
from app.config import settings
from app.pipeline.retrieval.models import RetrievedChunk

from .exceptions import GenerationError
from .interface import BaseGenerator
from .models import GenerateResult
from .prompt_builder import PromptBuilder

DEFAULT_TEMPLATE = """
You are a helpful AI assistant.

Answer ONLY using the provided context.
If the answer cannot be found, say you don't know.

Context:
{context}

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
        print(f"Model: {self.model}")

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
        }
        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            print(f"{self.base_url}/api/generate")

            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise GenerationError(exc.response.json()["error"]) from exc

        except httpx.HTTPError as exc:
            raise GenerationError("Failed to communicate with Ollama.") from exc

        return GenerateResult(
            answer=data["response"],
            citations=context,
            prompt_tokens=data["prompt_eval_count"],
            completion_tokens=data["eval_count"],
        )
