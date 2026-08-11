import itertools

import pytest
from app.pipeline.chunking.recursive_chunker import RecursiveChunker
from app.pipeline.cleaning.models import CleaningResult


def clean(text: str) -> CleaningResult:
    return CleaningResult(text=text)


# ==========================================================
# Configuration Validation
# ==========================================================


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [
        (0, 0),
        (-1, 0),
        (100, -1),
        (100, 100),
        (100, 101),
    ],
)
def test_invalid_configuration(chunk_size, overlap):
    with pytest.raises(ValueError):
        RecursiveChunker(
            chunk_size=chunk_size,
            overlap=overlap,
        )


# ==========================================================
# Empty / Blank Documents
# ==========================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "text",
    [
        "",
        " ",
        "\t",
        "\n",
        "\n\n\n",
        "     \n\t   ",
    ],
)
async def test_blank_documents_return_no_chunks(text):
    chunker = RecursiveChunker()

    chunks = await chunker.chunk(clean(text))

    assert chunks == []


# ==========================================================
# Small Documents
# ==========================================================


@pytest.mark.asyncio
async def test_small_document_returns_single_chunk():
    text = "Hello world."

    chunker = RecursiveChunker(
        chunk_size=512,
        overlap=64,
    )

    chunks = await chunker.chunk(clean(text))

    assert len(chunks) == 1

    chunk = chunks[0]

    assert chunk.text == text
    assert chunk.start_char == 0
    assert chunk.end_char == len(text)


# ==========================================================
# Large Documents
# ==========================================================


@pytest.mark.asyncio
async def test_large_document_produces_multiple_chunks():
    text = ("hello world " * 1000).strip()

    chunker = RecursiveChunker(
        chunk_size=200,
        overlap=40,
    )

    chunks = await chunker.chunk(clean(text))

    assert len(chunks) > 1

    assert all(len(chunk.text) <= 200 for chunk in chunks)


@pytest.mark.asyncio
async def test_long_single_token_falls_back_to_character_split():
    text = "A" * 50000

    chunker = RecursiveChunker(
        chunk_size=256,
        overlap=32,
    )

    chunks = await chunker.chunk(clean(text))

    assert len(chunks) > 1

    assert all(len(chunk.text) <= 256 for chunk in chunks)


# ==========================================================
# Production Regression
# ==========================================================


@pytest.mark.asyncio
async def test_non_empty_document_never_returns_zero_chunks():
    """
    Regression test for the production bug where ingestion
    completed successfully but produced zero chunks.
    """

    text = ("Interview question. " * 10000).strip()

    chunker = RecursiveChunker(
        chunk_size=512,
        overlap=64,
    )

    chunks = await chunker.chunk(clean(text))

    assert len(chunks) > 0


# ==========================================================
# Chunk Integrity
# ==========================================================


@pytest.mark.asyncio
async def test_every_chunk_has_non_empty_text():
    text = "Hello\n\nWorld\n\nAgain"

    chunker = RecursiveChunker(
        chunk_size=20,
        overlap=5,
    )

    chunks = await chunker.chunk(clean(text))

    assert all(chunk.text for chunk in chunks)


@pytest.mark.asyncio
async def test_every_chunk_respects_chunk_size():
    text = ("abc " * 5000).strip()

    chunker = RecursiveChunker(
        chunk_size=150,
        overlap=30,
    )

    chunks = await chunker.chunk(clean(text))

    assert all(len(chunk.text) <= 150 for chunk in chunks)


# ==========================================================
# Offsets
# ==========================================================


@pytest.mark.asyncio
async def test_offsets_match_original_document():
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three.\n\nParagraph four."

    chunker = RecursiveChunker(
        chunk_size=45,
        overlap=10,
    )

    chunks = await chunker.chunk(clean(text))

    for chunk in chunks:
        assert chunk.text == text[chunk.start_char : chunk.end_char]


@pytest.mark.asyncio
async def test_chunk_spans_are_valid():
    text = ("hello world " * 300).strip()

    chunker = RecursiveChunker()

    chunks = await chunker.chunk(clean(text))

    for chunk in chunks:
        assert chunk.start_char >= 0
        assert chunk.end_char > chunk.start_char
        assert chunk.end_char <= len(text)


# ==========================================================
# Ordering
# ==========================================================


@pytest.mark.asyncio
async def test_chunk_indices_are_sequential():
    text = ("abc " * 1000).strip()

    chunker = RecursiveChunker()

    chunks = await chunker.chunk(clean(text))

    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


@pytest.mark.asyncio
async def test_chunks_are_sorted_by_offset():
    text = ("abc " * 1000).strip()

    chunker = RecursiveChunker()

    chunks = await chunker.chunk(clean(text))

    starts = [c.start_char for c in chunks]

    assert starts == sorted(starts)


# ==========================================================
# Overlap
# ==========================================================


@pytest.mark.asyncio
async def test_overlap_is_preserved():
    text = " ".join(f"word{i}" for i in range(1000))

    chunker = RecursiveChunker(
        chunk_size=150,
        overlap=40,
    )

    chunks = await chunker.chunk(clean(text))

    assert len(chunks) > 1

    for previous, current in itertools.pairwise(chunks):
        overlap = previous.end_char - current.start_char

        assert overlap >= 0
        assert overlap <= chunker.overlap


# ==========================================================
# UUIDs
# ==========================================================


@pytest.mark.asyncio
async def test_chunk_ids_are_unique():
    text = ("abc " * 2000).strip()

    chunker = RecursiveChunker()

    chunks = await chunker.chunk(clean(text))

    ids = [chunk.chunk_id for chunk in chunks]

    assert len(ids) == len(set(ids))


# ==========================================================
# Separator Preference
# ==========================================================


@pytest.mark.asyncio
async def test_prefers_paragraph_boundaries():
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three.\n\nParagraph four."

    chunker = RecursiveChunker(
        chunk_size=45,
        overlap=0,
    )

    chunks = await chunker.chunk(clean(text))

    assert len(chunks) >= 2

    assert any("\n\n" in chunk.text for chunk in chunks)


# ==========================================================
# Unicode / PDF Edge Cases
# ==========================================================


@pytest.mark.asyncio
async def test_handles_unicode_and_pdf_artifacts():
    text = "\ufeff\u200bHello World\u200b\u00a0"

    chunker = RecursiveChunker()

    chunks = await chunker.chunk(clean(text))

    assert len(chunks) > 0


# ==========================================================
# Reconstruction
# ==========================================================


@pytest.mark.asyncio
async def test_original_document_is_fully_covered():
    """
    Every character in the trimmed document should belong
    to at least one chunk.
    """

    text = ("abcdefghijklmnopqrstuvwxyz " * 200).strip()

    chunker = RecursiveChunker(
        chunk_size=128,
        overlap=32,
    )

    chunks = await chunker.chunk(clean(text))

    coverage = [False] * len(text)

    for chunk in chunks:
        for i in range(chunk.start_char, chunk.end_char):
            coverage[i] = True

    assert all(coverage)
