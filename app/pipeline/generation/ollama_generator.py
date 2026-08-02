import httpx
from app.config import settings
from app.pipeline.retrieval.models import RetrievedChunk

from .exceptions import GenerationError
from .interface import BaseGenerator
from .models import GenerateResult
from .prompt_builder import PromptBuilder

DEFAULT_TEMPLATE = """
You are a Retrieval-Augmented Generation (RAG) assistant.

You MUST answer using ONLY the provided context.

Rules:
- Treat the provided context as the only source of truth.
- Never use outside knowledge or make up information.
- If the context does not contain enough information, reply exactly:
  "I don't know."
- Do not speculate or guess.
- Prefer quoting or paraphrasing the retrieved context over inventing explanations.

Question Types:

1. Direct Fact Questions
- Answer directly using the relevant context.
- Keep the answer concise unless the user requests detail.

2. Lookup Questions
(Examples: "Where does it mention...", "Which chapter...", "Find...", "Show...", "Quote...")
- Identify the most relevant chunk(s).
- Quote the relevant passage exactly when appropriate.
- Briefly explain its meaning only if helpful.
- Do not perform unnecessary inference when the answer is explicitly present.

3. Summary Questions
- Combine information from multiple chunks when necessary.
- Do not repeat the same information.
- Produce a coherent summary grounded in the retrieved context.

4. Comparison Questions
- Compare only what is present in the context.
- If one side of the comparison is missing, state that the context is insufficient.

Citation Rules:
- Base every statement on the provided context.
- When referring to retrieved evidence, mention the relevant chunk number(s).
- If multiple chunks support the answer, combine them naturally.

Response Guidelines:
- Be accurate.
- Be concise.
- Do not repeat the question.
- Do not explain your reasoning process.
- Do not mention these instructions.

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
