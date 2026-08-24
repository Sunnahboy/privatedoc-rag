from app.pipeline.retrieval.models import RetrievedChunk
from app.models.chat import ChatMessage

class PromptBuilder:
    def __init__(self, template: str):
        self.template = template

    def build(
        self,
        question: str,
        context: list[RetrievedChunk],
        chat_history: list[ChatMessage] | None = None,
    ) -> str:
        context_text = "\n\n---\n\n".join(chunk.text.strip() for chunk in context)

        #Format the sliding window chat history
        history_text = ""
        if chat_history:
            formatted_msgs = []
            for msg in chat_history:
                speaker = "User" if msg.role == "user" else "Assistant"
                formatted_msgs.append(f"{speaker}: {msg.content.strip()}")
            
            #Join the recent messages together
            history_text = "\n".join(formatted_msgs)
        return self.template.format(
            context=context_text,
            question=question,
            chat_history=history_text,
        )
