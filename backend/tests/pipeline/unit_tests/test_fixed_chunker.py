import pytest
from app.pipeline.chunking.fixed_chunker import FixedChunker
from app.pipeline.cleaning.models import CleaningResult


@pytest.mark.asyncio
async def test_single_chunk():
    chunker = FixedChunker(chunk_size=100,overlap=3)

    cleaning_result = CleaningResult(
        text="Hello World", removed_blank_lines=0, metadata={"document_id":"doc1"}
    )

    chunks = await chunker.chunk(cleaning_result)

    assert len(chunks) == 1
