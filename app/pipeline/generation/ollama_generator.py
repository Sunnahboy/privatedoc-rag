import httpx
from app.config import settings
from app.pipeline.retrieval.models import RetrievedChunk
from app.utils.profiler import record_ollama_metrics

from .exceptions import GenerationError
from .interface import BaseGenerator
from .models import GenerateResult
from .prompt_builder import PromptBuilder

DEFAULT_TEMPLATE = """
You are a Retrieval-Augmented Generation (RAG) assistant.

Use ONLY the provided context to answer the question.

Rules:
- Treat the provided context as the only source of information.
- Never use outside knowledge.
- Never guess or speculate.
- If the answer cannot be determined from the context, reply exactly:
  I don't know.
- Answer only what the user asked.
- Do not explain your reasoning.
- Do not mention these instructions.
- Do not mention chunk numbers or citations in your answer. Citations are handled separately.

Question Types:

1. Direct Questions
- Answer directly.
- Be concise unless the user requests more detail.

2. Lookup Questions
(Examples: "Find...", "Where does it mention...", "Which chapter...", "Quote...")
- If the requested information appears explicitly in the context, extract it exactly as written.
- Do not rewrite or reinterpret explicit lists, tables, headings, or numbered items.
- Only summarize if the information is spread across multiple chunks.

3. Summary Questions
- Combine information from multiple chunks.
- Remove duplicate information.
- Preserve the original meaning.
- Do not add information that is not present.

4. Comparison Questions
- Compare only information found in the context.
- If information for one side is missing, state that the context is insufficient.

Extraction Rules:
- Prefer extraction over inference.
- If one chunk directly answers the question, use that chunk.
- If multiple chunks contain the same information, avoid repeating it.
- If multiple chunks contain complementary information, combine them into one coherent answer.

Response Style:
- Be factual.
- Be precise.
- Be concise.
- Use bullet points or numbered lists when the context itself contains lists.

--------------------
Context:
{context}
--------------------

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
        )
