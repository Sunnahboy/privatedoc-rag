import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import ClassVar

from app.config import settings
from app.pipeline.cleaning.models import CleaningResult

from .base import BaseChunker
from .models import Chunk


@dataclass(frozen=True, slots=True)
class _Span:
    """Absolute character span into the original document."""

    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start


class RecursiveChunker(BaseChunker):
    """
    Production-oriented recursive chunker.

    Design goals:
    - Never reconstruct offsets with `find()`.
    - Carry absolute offsets through the entire split process.
    - Preserve separators exactly by splitting on spans, not rebuilt strings.
    - Apply overlap in one place only: chunk emission.
    - Avoid repeated joins / regex splits / substring searching for reconstruction.
    - Keep recursion depth bounded by separator priority, not document size.

    Default separator priority matches the current implementation:
        1. paragraph  -> "\\n\\n"
        2. line       -> "\\n"
        3. sentence   -> ". "
        4. word       -> " "
        5. fallback   -> hard character split
    """

    DEFAULT_SEPARATORS: ClassVar[list[str]] = [
        "\n\n",
        "\n",
        ". ",
        " ",
        "",
    ]

    def __init__(
        self,
        chunk_size: int | None = None,
        overlap: int | None = None,
        separators: list[str] | None = None,
    ) -> None:
        self.chunk_size = (
            chunk_size if chunk_size is not None else settings.rag_chunk_size
        )
        self.overlap = overlap if overlap is not None else settings.rag_chunk_overlap
        self.separators = (
            separators if separators is not None else self.DEFAULT_SEPARATORS
        )

        self._validate_config()

    async def chunk(self, cleaning_result: CleaningResult) -> list[Chunk]:
        """
        Split the cleaned document into chunks with absolute source offsets.

        Offsets are measured against the original `cleaning_result.text`,
        not against a trimmed copy.

        Leading and trailing whitespace-only margins are excluded to preserve
        the behavior of the previous `.strip()`-based implementation while
        keeping offsets truthful to the original source document.
        """
        text = cleaning_result.text or ""
        content_start, content_end = self._content_bounds(text)

        if content_start == content_end:
            return []

        chunks: list[Chunk] = []
        self._split_span(
            text=text,
            start=content_start,
            end=content_end,
            separator_index=0,
            chunks=chunks,
            prefix_start=None,
        )
        return chunks

    # ------------------------------------------------------------------
    # Core recursive splitting
    # ------------------------------------------------------------------

    def _split_span(
        self,
        *,
        text: str,
        start: int,
        end: int,
        separator_index: int,
        chunks: list[Chunk],
        prefix_start: int | None,
    ) -> _Span | None:
        """
        Recursively split the absolute span [start, end) and emit Chunk objects.

        Parameters
        ----------
        text:
            Original full document text.
        start, end:
            Absolute bounds of the span owned by this recursive call.
        separator_index:
            Current separator priority level.
        chunks:
            Output list, appended in-order.
        prefix_start:
            Optional absolute start offset for overlap with the previously
            emitted chunk.

            Important:
            The first chunk emitted by this call may legally begin before
            `start` if overlap with the previous chunk requires it. This is
            how overlap is preserved across recursive boundaries without any
            reconstruction pass.

        Returns
        -------
        _Span | None
            The last chunk span emitted by this call, used by callers to seed
            overlap into subsequent sibling ranges.
        """
        if end <= start:
            return None

        span_length = end - start

        # Base case: this owned span already fits in a chunk.
        if span_length <= self.chunk_size:
            chunk_start = self._bounded_start(
                end=end,
                owning_start=start,
                prefix_start=prefix_start,
            )
            return self._emit_chunk(
                text=text, start=chunk_start, end=end, chunks=chunks
            )

        # Base case: no finer separators remain -> hard split.
        if (
            separator_index >= len(self.separators)
            or self.separators[separator_index] == ""
        ):
            return self._hard_split(
                text=text,
                start=start,
                end=end,
                chunks=chunks,
                prefix_start=prefix_start,
            )

        separator = self.separators[separator_index]
        next_index = separator_index + 1

        current_start: int | None = None
        current_end: int = 0
        previous_emitted: _Span | None = None

        for part in self._iter_parts(
            text=text, start=start, end=end, separator=separator
        ):
            # If one separator-delimited part is still too large, recurse into it
            # using the next finer separator.
            if part.length > self.chunk_size:
                if current_start is not None:
                    previous_emitted = self._emit_chunk(
                        text=text,
                        start=current_start,
                        end=current_end,
                        chunks=chunks,
                    )
                    current_start = None

                previous_emitted = self._split_span(
                    text=text,
                    start=part.start,
                    end=part.end,
                    separator_index=next_index,
                    chunks=chunks,
                    prefix_start=self._active_prefix(
                        previous_emitted=previous_emitted,
                        incoming_prefix=prefix_start,
                    ),
                )
                continue

            # Start a new chunk candidate.
            if current_start is None:
                current_start = self._bounded_start(
                    end=part.end,
                    owning_start=part.start,
                    prefix_start=self._active_prefix(
                        previous_emitted=previous_emitted,
                        incoming_prefix=prefix_start,
                    ),
                )
                current_end = part.end
                continue

            # Extend the current chunk candidate if it still fits.
            if part.end - current_start <= self.chunk_size:
                current_end = part.end
                continue

            # Otherwise flush the current chunk and start a new one with overlap.
            previous_emitted = self._emit_chunk(
                text=text,
                start=current_start,
                end=current_end,
                chunks=chunks,
            )
            current_start = self._bounded_start(
                end=part.end,
                owning_start=part.start,
                prefix_start=self._overlap_seed_start(previous_emitted),
            )
            current_end = part.end

        if current_start is not None:
            previous_emitted = self._emit_chunk(
                text=text,
                start=current_start,
                end=current_end,
                chunks=chunks,
            )

        return previous_emitted

    # ------------------------------------------------------------------
    # Hard split fallback
    # ------------------------------------------------------------------

    def _hard_split(
        self,
        *,
        text: str,
        start: int,
        end: int,
        chunks: list[Chunk],
        prefix_start: int | None,
    ) -> _Span | None:
        """
        Emit fixed-size overlapping windows for [start, end).

        This is only used after all semantic separators have been exhausted.
        """
        window_start = prefix_start if prefix_start is not None else start

        # Defensive clamp: a caller-provided prefix should add overlap context,
        # not create a window that fails to cover any newly owned text.
        if window_start + self.chunk_size <= start:
            window_start = start

        last_emitted: _Span | None = None

        while window_start < end:
            window_end = min(window_start + self.chunk_size, end)
            last_emitted = self._emit_chunk(
                text=text,
                start=window_start,
                end=window_end,
                chunks=chunks,
            )

            if window_end == end:
                break

            window_start = window_end - self.overlap

        return last_emitted

    # ------------------------------------------------------------------
    # Chunk emission
    # ------------------------------------------------------------------

    def _emit_chunk(
        self,
        *,
        text: str,
        start: int,
        end: int,
        chunks: list[Chunk],
    ) -> _Span:
        """
        Append a Chunk with exact absolute offsets.

        This is the only place where substrings are materialized.
        """
        if end <= start:
            raise ValueError(
                f"Cannot emit empty or negative chunk span: [{start}, {end})"
            )

        chunks.append(
            Chunk(
                chunk_id=str(uuid.uuid4()),
                document_id="",  # assigned later by caller/pipeline
                chunk_index=len(chunks),
                text=text[start:end],
                start_char=start,
                end_char=end,
            )
        )
        return _Span(start, end)

    # ------------------------------------------------------------------
    # Separator scanning
    # ------------------------------------------------------------------

    def _iter_parts(
        self,
        *,
        text: str,
        start: int,
        end: int,
        separator: str,
    ) -> Iterator[_Span]:
        """
        Yield contiguous separator-delimited spans inside [start, end).

        The separator is attached to the end of the left-hand part so that
        separators are preserved exactly.

        Example:
            text = "Hello. World"
            separator = ". "
            yields:
                [0, 7)   -> "Hello. "
                [7, 12)  -> "World"
        """
        sep_len = len(separator)
        cursor = start

        while cursor < end:
            index = text.find(separator, cursor, end)
            if index == -1:
                yield _Span(cursor, end)
                return

            next_cursor = index + sep_len
            yield _Span(cursor, next_cursor)
            cursor = next_cursor

    # ------------------------------------------------------------------
    # Overlap / boundary helpers
    # ------------------------------------------------------------------

    def _active_prefix(
        self,
        *,
        previous_emitted: _Span | None,
        incoming_prefix: int | None,
    ) -> int | None:
        """
        Determine which overlap prefix should seed the next chunk.

        - If this recursive call has already emitted something, use overlap from
          that last emitted chunk.
        - Otherwise use the prefix inherited from the caller.
        """
        if previous_emitted is not None:
            return self._overlap_seed_start(previous_emitted)
        return incoming_prefix

    def _overlap_seed_start(self, span: _Span | None) -> int | None:
        """Return the absolute start offset for overlap seeding."""
        if span is None or self.overlap == 0:
            return None
        return max(span.end - self.overlap, span.start)

    def _bounded_start(
        self,
        *,
        end: int,
        owning_start: int,
        prefix_start: int | None,
    ) -> int:
        """
        Choose the start for a chunk that must end at `end` and must include
        newly owned text beginning at `owning_start`.

        If a prefix overlap is requested, keep as much of it as possible without
        violating chunk_size.
        """
        if prefix_start is None:
            return owning_start

        start = max(prefix_start, end - self.chunk_size)

        # In normal operation this should already be <= owning_start. If not,
        # prioritize correctness and ensure the chunk still includes the owned
        # range from its natural boundary.
        if start > owning_start:
            return owning_start

        return start

    # ------------------------------------------------------------------
    # Input normalization / validation
    # ------------------------------------------------------------------

    @staticmethod
    def _content_bounds(text: str) -> tuple[int, int]:
        """
        Return the bounds of non-whitespace content.

        This preserves the old `.strip()` behavior without losing original
        absolute offsets.
        """
        start = 0
        end = len(text)

        while start < end and text[start].isspace():
            start += 1

        while end > start and text[end - 1].isspace():
            end -= 1

        return start, end

    def _validate_config(self) -> None:
        if self.chunk_size is None:
            raise ValueError(
                "chunk_size must be provided explicitly or via settings.rag_chunk_size"
            )
        if self.overlap is None:
            raise ValueError(
                "overlap must be provided explicitly or via settings.rag_chunk_overlap"
            )
        if self.chunk_size <= 0:
            raise ValueError(f"chunk_size must be > 0, got {self.chunk_size}")
        if self.overlap < 0:
            raise ValueError(f"overlap cannot be negative, got {self.overlap}")
        if self.overlap >= self.chunk_size:
            raise ValueError(
                f"overlap ({self.overlap}) must be smaller than chunk_size ({self.chunk_size})"
            )
