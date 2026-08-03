import re


class Tokenizer:
    """Simple tokenizer for Bm25.
     Responsibilities:
    - Lowercase text.
    - Split into tokens.
    - Remove punctuation.

    """

    TOKEN_PATTERN = re.compile(r"\b[a-zA-Z0-9]+\b")

    def tokenize(self, text: str) -> list[str]:
        return self.TOKEN_PATTERN.findall(text.lower())
