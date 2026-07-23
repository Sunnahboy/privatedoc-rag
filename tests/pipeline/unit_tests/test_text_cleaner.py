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
        text="Hello\n\n\n\nWorld",
        page_count=1,
        metadata={},
    )

    result = await cleaner.clean(extraction)

    assert result.text == "Hello\n\nWorld"


@pytest.mark.asyncio
async def test_clean_text_unchanged(cleaner):

    extraction = ExtractionResult(
        text="Hello\n\nWorld",
        page_count=1,
        metadata={},
    )

    result = await cleaner.clean(extraction)

    assert result.text == "Hello\n\nWorld"


@pytest.mark.asyncio
async def test_empty_text(cleaner):

    extraction = ExtractionResult(
        text="",
        page_count=1,
        metadata={},
    )

    result = await cleaner.clean(extraction)

    assert result.text == ""


@pytest.mark.asyncio
async def test_only_newlines(cleaner):
    """Ensures a string of pure newlines collapses safely."""
    extraction = ExtractionResult(text="\n\n\n\n", page_count=1, metadata={})
    result = await cleaner.clean(extraction)
    assert result.text == "\n\n"
