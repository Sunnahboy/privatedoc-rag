import pytest
from app.pipeline.cleaning.text_cleaner import TextCleaner
from app.pipeline.extraction.models import ExtractionResult


@pytest.fixture
def cleaner():
    """Provides a reusable instance of TextCleaner."""
    return TextCleaner()


@pytest.mark.asyncio
async def test_removes_extra_blank_lines(cleaner):

    extraction = ExtractionResult(
        pages=["Hello\n\n\n\nWorld"],
        total_pages=1,
        metadata={},
    )

    result = await cleaner.clean(extraction)

    assert result.pages[0] == "Hello\n\nWorld"


@pytest.mark.asyncio
async def test_clean_text_unchanged(cleaner):

    extraction = ExtractionResult(
        pages=["Hello\n\nWorld"],
        total_pages=1,
        metadata={},
    )

    result = await cleaner.clean(extraction)

    assert result.pages[0] == "Hello\n\nWorld"


@pytest.mark.asyncio
async def test_empty_text(cleaner):

    extraction = ExtractionResult(
        pages=[""],
        total_pages=1,
        metadata={},
    )

    result = await cleaner.clean(extraction)

    assert result.pages[0] == ""


@pytest.mark.asyncio
async def test_only_newlines(cleaner):
    """Ensures a string of pure newlines collapses safely."""
    extraction = ExtractionResult(pages=["\n\n\n\n"], total_pages=1, metadata={})
    result = await cleaner.clean(extraction)
    assert result.pages[0] == "\n\n"
