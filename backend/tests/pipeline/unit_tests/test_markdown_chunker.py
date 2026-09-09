import pytest
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.pipeline.chunking.markdown_chunker import MarkdownSemanticChunker
from app.pipeline.cleaning.models import CleaningResult


def clean(*pages: str) -> CleaningResult:
    return CleaningResult(pages=list(pages))


@pytest.mark.asyncio
async def test_repeated_content_keeps_exact_source_offsets():
    text = "# Repeated\n" + ("same words appear again " * 200)
    chunker = MarkdownSemanticChunker(chunk_size=96, chunk_overlap=24)

    chunks = await chunker.chunk(clean(text), document_id="document")

    assert len(chunks) > 10
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    for chunk in chunks:
        assert chunk.text == text[chunk.start_char : chunk.end_char]
        assert chunk.metadata == {"Header_1": "Repeated"}


@pytest.mark.asyncio
async def test_length_splitting_matches_recursive_character_splitter():
    text = "  first paragraph\n\nsecond paragraph has several words\nthird paragraph  "
    chunker = MarkdownSemanticChunker(chunk_size=24, chunk_overlap=6)

    chunks = await chunker.chunk(clean(text), document_id="document")
    expected = RecursiveCharacterTextSplitter(
        chunk_size=24,
        chunk_overlap=6,
    ).split_text(text)

    assert [chunk.text for chunk in chunks] == expected


@pytest.mark.asyncio
async def test_headers_are_attached_to_their_source_sections():
    text = "# Top\nopening\n## Child\ninside\n# Next\nend"
    chunker = MarkdownSemanticChunker(chunk_size=100, chunk_overlap=10)

    chunks = await chunker.chunk(clean(text), document_id="document")

    assert [chunk.text for chunk in chunks] == [
        "# Top\nopening",
        "## Child\ninside",
        "# Next\nend",
    ]
    assert [chunk.metadata for chunk in chunks] == [
        {"Header_1": "Top"},
        {"Header_1": "Top", "Header_2": "Child"},
        {"Header_1": "Next"},
    ]


@pytest.mark.asyncio
async def test_pages_keep_virtual_offsets_and_header_metadata():
    first_page = "# Title\n" + ("alpha " * 30)
    second_page = "beta " * 30
    virtual_document = "\n\n".join((first_page, second_page))
    chunker = MarkdownSemanticChunker(chunk_size=80, chunk_overlap=20)

    chunks = await chunker.chunk(clean(first_page, second_page), document_id="document")

    assert {chunk.page_number for chunk in chunks} == {1, 2}
    assert all(
        chunk.text == virtual_document[chunk.start_char : chunk.end_char]
        for chunk in chunks
    )
    assert all(
        chunk.metadata == {"Header_1": "Title"}
        for chunk in chunks
        if chunk.page_number == 2
    )


@pytest.mark.asyncio
async def test_short_pages_can_share_a_chunk():
    first_page = "alpha " * 5
    second_page = "beta " * 5
    virtual_document = "\n\n".join((first_page, second_page))
    chunker = MarkdownSemanticChunker(chunk_size=100, chunk_overlap=20)

    chunks = await chunker.chunk(clean(first_page, second_page), document_id="document")

    assert len(chunks) == 1
    assert chunks[0].text == virtual_document.strip()
    assert chunks[0].page_number == 1


@pytest.mark.asyncio
async def test_markdown_fences_do_not_create_header_sections():
    text = "```markdown\n# not a heading\n```\n# Heading\ncontent"
    chunker = MarkdownSemanticChunker(chunk_size=100, chunk_overlap=10)

    chunks = await chunker.chunk(clean(text), document_id="document")

    assert [chunk.metadata for chunk in chunks] == [{}, {"Header_1": "Heading"}]
