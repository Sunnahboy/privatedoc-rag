from app.pipeline.retrieval.models import RetrievedChunk


class PromptBuilder:
    def __init__(self, template: str):
        self.template = template

    def build(
        self,
        question: str,
        context: list[RetrievedChunk],
    ) -> str:
        context_text = "\n\n---\n\n".join(chunk.text.strip() for chunk in context)
        return self.template.format(
            context=context_text,
            question=question,
        )
