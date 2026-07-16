import pytest

from app.pipeline.cleaning.text_cleaner import TextCleaner
from app.pipeline.extraction.models import ExtractionResult


@pytest.mark.asyncio
async def test_removes_extra_blank_lines():
    cleaner = TextCleaner()

    extraction = ExtractionResult(
        text="Hello\n\n\n\nWorld",
        page_count=1,
        metadata={},
    )

    result = await cleaner.clean(extraction)

    assert result.text == "Hello\n\nWorld"


@pytest.mark.asyncio
async def test_clean_text_unchanged():
    cleaner = TextCleaner()

    extraction = ExtractionResult(
        text="Hello\n\nWorld",
        page_count=1,
        metadata={},
    )

    result = await cleaner.clean(extraction)

    assert result.text == "Hello\n\nWorld"


@pytest.mark.asyncio
async def test_empty_text():
    cleaner = TextCleaner()

    extraction = ExtractionResult(
        text="",
        page_count=1,
        metadata={},
    )

    result = await cleaner.clean(extraction)

    assert result.text == ""