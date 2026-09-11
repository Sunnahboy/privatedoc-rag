"use client";

import type { PageProps } from "react-pdf";

export interface PageHighlight {
  page: number;
  text: string;
}

type CustomTextRenderer = NonNullable<PageProps["customTextRenderer"]>;

const MIN_MATCH_LENGTH = 4;

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Normalizes text for matching only (display text is never touched): lowercases,
 * and collapses everything that isn't a letter/number down to single spaces so
 * punctuation/quote-style/hyphenation differences between Docling's markdown
 * export and the PDF's raw text layer don't break an otherwise-real match.
 * `\p{L}`/`\p{N}` keep this correct for non-Latin scripts (e.g. Arabic terms).
 */
function normalizeForMatch(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function stripMarkdown(citationText: string): string {
  return citationText
    .replace(/^#{1,6}\s*/gm, "")
    .replace(/[*_`]/g, "")
    .trim();
}

/**
 * Builds a `customTextRenderer` for react-pdf's `<Page>` that wraps text runs
 * on the cited page in `<mark>` when they appear anywhere in the citation
 * text. Matching is done against the citation as a single normalized corpus
 * (not sentence-by-sentence), so runs that straddle a sentence boundary, or
 * fall late in a long citation, still get highlighted. Runs are matched
 * per-item (a PDF text run), not per-word, so precision is bounded by how the
 * PDF splits its text content.
 */
export function createHighlightTextRenderer(
  highlight: PageHighlight | null,
): CustomTextRenderer | undefined {
  if (!highlight || !highlight.text.trim()) {
    return undefined;
  }

  const corpus = normalizeForMatch(stripMarkdown(highlight.text));
  if (!corpus) {
    return undefined;
  }

  return ({ pageNumber, str }) => {
    const safeStr = escapeHtml(str);
    const trimmed = str.trim();

    // Match on the cited page and anything after it (never before) - chunks
    // often span into the next page, and page attribution is a best-effort
    // guess. Only pages actually mounted by the virtualizer ever call this,
    // so this can't reach far into unrelated later content.
    if (pageNumber < highlight.page || trimmed.length < MIN_MATCH_LENGTH) {
      return safeStr;
    }

    const normalized = normalizeForMatch(trimmed);
    const isMatch = normalized.length >= MIN_MATCH_LENGTH && corpus.includes(normalized);
    return isMatch ? `<mark class="pdf-citation-highlight">${safeStr}</mark>` : safeStr;
  };
}
