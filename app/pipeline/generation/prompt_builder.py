from app.pipeline.retrieval.models import RetrievedChunk


class PromptBuilder:
    def __init__(self, template: str):
        self.template = template

    def build(
        self,
        question: str,
        context: list[RetrievedChunk],
    ) -> str:
        context_text = "\n\n".join(
            f"[Chunk {chunk.chunk_index}] \n{chunk.text}" for chunk in context
        )
        return self.template.format(
            context=context_text,
            question=question,
        )
