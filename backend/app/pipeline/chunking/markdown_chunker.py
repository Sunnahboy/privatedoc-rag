"""Markdown-aware chunking with source offsets carried through splitting.

The previous implementation made an extra copy of every page while rebuilding
the document, materialized two LangChain document lists, and reconstructed
every chunk's offset by searching the whole document. The search is
particularly expensive for long documents with repeated content.

This implementation keeps sections as spans into one source string. Chunks are
emitted directly from those spans, so only the source and final chunk strings
are retained.
"""

import asyncio
import bisect
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass

from app.pipeline.chunking.base import BaseChunker
from app.pipeline.chunking.models import Chunk
from app.pipeline.cleaning.models import CleaningResult
from app.utils.id_id_utils import generate_chunk_id


@dataclass(frozen=True, slots=True)
class _Span:
    """A half-open character range in the virtual source document."""

    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass(frozen=True, slots=True)
class _Header:
    level: int
    name: str
    value: str


@dataclass(frozen=True, slots=True)
class _Section:
    """A markdown section and the header metadata active for it."""

    span: _Span
    metadata: dict[str, str]


class MarkdownSemanticChunker(BaseChunker):
    """Split Markdown at headers, then recursively split oversized sections.

    Offsets are carried as spans instead of reconstructed with ``str.find``.
    Only one virtual document string is created for paginated input; chunk
    boundaries may still cross pages as before, avoiding extra embeddings for
    short pages.
    """

    _SEPARATORS = ("\n\n", "\n", " ", "")

    def __init__(self, chunk_size: int = 2000, chunk_overlap: int = 200):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if chunk_overlap > chunk_size:
            raise ValueError("chunk_overlap cannot exceed chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.headers_to_split_on = [
            ("#", "Header_1"),
            ("##", "Header_2"),
            ("###", "Header_3"),
            ("####", "Header_4"),
        ]
        # Match MarkdownHeaderTextSplitter's longest-marker-first behaviour.
        self._headers = tuple(
            sorted(
                self.headers_to_split_on,
                key=lambda header: len(header[0]),
                reverse=True,
            )
        )

    async def chunk(
        self,
        cleaning_result: CleaningResult,
        document_id: str = "unknown_doc",
    ) -> list[Chunk]:
        pages = getattr(cleaning_result, "pages", None)
        page_boundaries: list[int] = []

        if pages:
            offset = 0
            for page in pages:
                # Keep the old virtual-document offset convention without
                # allocating a temporary string for each page.
                offset += len(page) + 2
                page_boundaries.append(offset)
            content = "\n\n".join(pages)
        elif getattr(cleaning_result, "text", None):
            content = cleaning_result.text
        elif getattr(cleaning_result, "cleaned_text", None):
            content = cleaning_result.cleaned_text
        else:
            content = str(cleaning_result)

        # ``strip()`` would duplicate a large string just to test whether it is
        # blank. isspace() performs that check without allocating a copy.
        if not content or content.isspace():
            return []

        doc_id = getattr(cleaning_result, "document_id", document_id)
        return await asyncio.to_thread(
            self._sync_chunk,
            content,
            doc_id,
            page_boundaries,
        )

    def _sync_chunk(
        self,
        text: str,
        document_id: str,
        page_boundaries: list[int],
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        header_stack: list[_Header] = []

        for section in self._iter_sections(text, header_stack):
            for span in self._iter_chunk_spans(text, section.span):
                page_number = (
                    bisect.bisect_right(page_boundaries, span.start) + 1
                    if page_boundaries
                    else None
                )
                chunks.append(
                    Chunk(
                        chunk_id=generate_chunk_id(document_id, len(chunks)),
                        document_id=document_id,
                        chunk_index=len(chunks),
                        text=text[span.start : span.end],
                        start_char=span.start,
                        end_char=span.end,
                        page_number=page_number,
                        metadata=section.metadata.copy(),
                    )
                )

        return chunks

    def _iter_sections(
        self, text: str, header_stack: list[_Header]
    ) -> Iterator[_Section]:
        """Yield source-backed sections while carrying active header state."""
        section_start = 0
        cursor = 0
        in_code_block = False
        opening_fence = ""

        while cursor <= len(text):
            newline = text.find("\n", cursor)
            line_end = len(text) if newline == -1 else newline
            line = text[cursor:line_end]
            stripped_line = line.strip()
            if stripped_line and not stripped_line.isprintable():
                stripped_line = "".join(
                    character for character in stripped_line if character.isprintable()
                )

            if not in_code_block:
                if (
                    stripped_line.startswith("```")
                    and stripped_line.count("```") == 1
                ):
                    in_code_block = True
                    opening_fence = "```"
                elif stripped_line.startswith("~~~"):
                    in_code_block = True
                    opening_fence = "~~~"
            elif stripped_line.startswith(opening_fence):
                in_code_block = False
                opening_fence = ""

            if not in_code_block:
                header = self._header_from_line(stripped_line)
                if header is not None:
                    if section_start < cursor:
                        yield _Section(
                            span=_Span(section_start, cursor),
                            metadata=self._metadata(header_stack),
                        )

                    level, name, value = header
                    while header_stack and header_stack[-1].level >= level:
                        header_stack.pop()
                    header_stack.append(_Header(level, name, value))
                    section_start = cursor

            if newline == -1:
                break
            cursor = newline + 1

        if section_start < len(text):
            yield _Section(
                span=_Span(section_start, len(text)),
                metadata=self._metadata(header_stack),
            )

    def _header_from_line(self, line: str) -> tuple[int, str, str] | None:
        for marker, name in self._headers:
            if line.startswith(marker) and (
                len(line) == len(marker) or line[len(marker)] == " "
            ):
                return marker.count("#"), name, line[len(marker) :].strip()
        return None

    @staticmethod
    def _metadata(header_stack: list[_Header]) -> dict[str, str]:
        return {header.name: header.value for header in header_stack}

    def _iter_chunk_spans(self, text: str, span: _Span) -> Iterator[_Span]:
        """RecursiveCharacterTextSplitter's algorithm, but operating on spans."""
        yield from self._split_span(text, span, self._SEPARATORS)

    def _split_span(
        self, text: str, span: _Span, separators: tuple[str, ...]
    ) -> Iterator[_Span]:
        separator_index = len(separators) - 1
        for index, separator in enumerate(separators):
            if not separator or text.find(separator, span.start, span.end) != -1:
                separator_index = index
                break

        separator = separators[separator_index]
        remaining_separators = separators[separator_index + 1 :]
        good_splits: deque[_Span] = deque()

        for split in self._iter_splits(text, span, separator):
            if split.length < self.chunk_size:
                good_splits.append(split)
                continue

            yield from self._merge_splits(text, good_splits)
            good_splits.clear()
            if remaining_separators:
                yield from self._split_span(text, split, remaining_separators)
            else:
                trimmed = self._trim_span(text, split)
                if trimmed is not None:
                    yield trimmed

        yield from self._merge_splits(text, good_splits)

    @staticmethod
    def _iter_splits(text: str, span: _Span, separator: str) -> Iterator[_Span]:
        """Yield contiguous spans, retaining each separator at the next split."""
        if not separator:
            for index in range(span.start, span.end):
                yield _Span(index, index + 1)
            return

        cursor = span.start
        first_separator = text.find(separator, cursor, span.end)
        if first_separator == -1:
            yield span
            return

        if first_separator > cursor:
            yield _Span(cursor, first_separator)
        cursor = first_separator

        while cursor < span.end:
            next_separator = text.find(separator, cursor + len(separator), span.end)
            end = span.end if next_separator == -1 else next_separator
            yield _Span(cursor, end)
            cursor = end

    def _merge_splits(self, text: str, splits: deque[_Span]) -> Iterator[_Span]:
        """Merge contiguous spans with bounded overlap and no string joins."""
        current: deque[_Span] = deque()
        total = 0

        for split in splits:
            if total + split.length > self.chunk_size and current:
                trimmed = self._trim_span(
                    text,
                    _Span(current[0].start, current[-1].end),
                )
                if trimmed is not None:
                    yield trimmed

                while total > self.chunk_overlap or (
                    total + split.length > self.chunk_size and total > 0
                ):
                    total -= current.popleft().length

            current.append(split)
            total += split.length

        if current:
            trimmed = self._trim_span(text, _Span(current[0].start, current[-1].end))
            if trimmed is not None:
                yield trimmed

    @staticmethod
    def _trim_span(text: str, span: _Span) -> _Span | None:
        """Apply LangChain's default whitespace stripping without copying text."""
        start, end = span.start, span.end
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        return _Span(start, end) if start < end else None
