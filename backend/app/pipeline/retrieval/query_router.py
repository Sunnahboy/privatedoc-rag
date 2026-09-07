import asyncio
import logging
import re
from enum import Enum

import numpy as np

from app.pipeline.embeddings.base import BaseEmbedder

logger = logging.getLogger(__name__)


class RouteDecision(str, Enum):
    CASUAL = "casual"
    SEARCH = "search"


# Strict exact-match patterns for pure, isolated casual intents.
# Anchored with ^ and $ to ensure we don't accidentally match "Hi, how do I install X?"
CASUAL_REGEX = re.compile(
    r"^(hi|hello|hey|thanks|thank you|good morning|good evening|bye|ok|okay|got it|awesome|great)\b[\s!.?]*$",
    re.IGNORECASE,
)

# A broader net for the semantic fallback
CASUAL_ANCHORS = [
    "hello",
    "how are you doing today",
    "thank you so much",
    "good morning",
    "who are you",
    "what can you do for me",
    "goodbye",
    "ok",
]


class HybridQueryRouter:
    """
    A production-grade router combining deterministic heuristics
    with a fallback semantic vector threshold.
    """

    def __init__(self, embedder: BaseEmbedder, threshold: float = 0.85):
        self.threshold = threshold
        self.embedder = embedder
        self.casual_matrix = None

    async def initialize(self) -> None:
        """
        Pre-computes anchors.
        embed anchors using embed_query() to keep them in the exact same
        asymmetric vector space as incoming user queries.
        """
        logger.info("Initializing Hybrid Router anchors in query space...")

        casual_vectors = []
        for text in CASUAL_ANCHORS:
            # Embed each anchor as a QUERY to fix the asymmetric manifold trap
            vector_list = await self.embedder.embed_query(text)
            casual_vectors.append(vector_list)

        self.casual_matrix = np.vstack(casual_vectors)

    def _compute_similarity(self, query_vector: np.ndarray) -> float:
        """Synchronous dot product math."""
        query_norm = query_vector / np.linalg.norm(query_vector)
        matrix_norm = self.casual_matrix / np.linalg.norm(
            self.casual_matrix, axis=1, keepdims=True
        )
        similarities = np.dot(matrix_norm, query_norm)
        return float(np.max(similarities))

    def route_regex_only(self, query: str) -> RouteDecision | None:
        """TIER 1: Deterministic regex bypass. 0ms latency."""
        if CASUAL_REGEX.match(query.strip()):
            logger.info(f"Router [Regex]: CASUAL bypass for '{query}'")
            return RouteDecision.CASUAL
        return None

    async def route_semantic(self, query: str) -> RouteDecision:
        """TIER 2 & 3: Heuristic and Semantic vector check. 10ms latency."""
        clean_query = query.strip()
        
        # TIER 2: Length Heuristic
        word_count = len(clean_query.split())
        if word_count > 7:
            logger.info(f"Router [Heuristic]: SEARCH execution for long query ({word_count} words)")
            return RouteDecision.SEARCH

        # TIER 3: Semantic Fallback
        try:
            query_vector_list = await self.embedder.embed_query(clean_query)
            query_vector = np.array(query_vector_list)
            
            max_casual_score = await asyncio.to_thread(self._compute_similarity, query_vector)
            logger.debug(f"Router [Semantic]: Score {max_casual_score:.3f} for '{clean_query}'")

            if max_casual_score >= self.threshold:
                logger.info(f"Router [Semantic]: CASUAL bypass for '{clean_query}'")
                return RouteDecision.CASUAL
                
            return RouteDecision.SEARCH
        except Exception as e:#noqa
            logger.error(f"Semantic fallback failed: {e}. Defaulting to SEARCH.")
            return RouteDecision.SEARCH