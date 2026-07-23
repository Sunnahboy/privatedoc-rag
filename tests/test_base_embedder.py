
from app.pipeline.embeddings.models import EmbeddingResult


def test_embedding_result_creation():
    result = EmbeddingResult(
        chunk_id="chunk1",
        document_id="doc1",
        chunk_index=0,
        vector=[0.1, 0.2, 0.3],
        model_name="nomic-embed-text",
        dimensions=3,
    )

    assert result.chunk_id == "chunk1"
    assert result.document_id == "doc1"
    assert len(result.vector) == 3