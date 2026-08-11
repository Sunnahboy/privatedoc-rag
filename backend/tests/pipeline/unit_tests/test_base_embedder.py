import pytest
from app.pipeline.embeddings.base import BaseEmbedder


def test_base_embedder_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseEmbedder()
