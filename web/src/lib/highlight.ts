import type { Citation, Clue } from "../types";

export interface NarrativeSegment {
  text: string;
  /** Present when this segment is a verbatim clue quote in the narrative. */
  quote?: string;
  verified?: boolean;
}

const MIN_QUOTE_LENGTH = 4;

function normalise(text: string): string {
  return text.replace(/\s+/g, " ").trim().toLowerCase();
}

interface Range {
  start: number;
  end: number;
  quote: string;
  verified: boolean;
}

/**
 * Split a narrative into plain and highlighted segments for the verbatim
 * quotes found in it. Quotes are matched case-insensitively after whitespace
 * normalisation; overlapping quotes are merged and the longest span wins.
 * A quote counts as verified only when a verified citation carries the same
 * verbatim quote.
 */
export function highlightQuotes(
  narrative: string,
  clues: readonly Clue[],
  citations: readonly Citation[] = [],
): NarrativeSegment[] {
  const haystack = narrative.toLowerCase();
  const verifiedQuotes = new Set(
    citations
      .filter((citation) => citation.verified && citation.quote)
      .map((citation) => normalise(citation.quote ?? "")),
  );

  const ranges: Range[] = [];
  for (const clue of clues) {
    const quote = clue.quote.trim();
    if (quote.length < MIN_QUOTE_LENGTH) {
      continue;
    }
    const needle = quote.toLowerCase();
    let from = 0;
    for (;;) {
      const start = haystack.indexOf(needle, from);
      if (start === -1) {
        break;
      }
      ranges.push({
        start,
        end: start + quote.length,
        quote: narrative.slice(start, start + quote.length),
        verified: verifiedQuotes.has(normalise(quote)),
      });
      from = start + 1;
    }
  }

  if (ranges.length === 0) {
    return [{ text: narrative }];
  }

  ranges.sort((a, b) => a.start - b.start || b.end - a.end);
  const merged: Range[] = [];
  for (const range of ranges) {
    const last = merged.at(-1);
    if (!last) {
      merged.push(range);
      continue;
    }
    if (range.start < last.end) {
      // Keep the longest overlapping span; verification wins on a tie.
      if (range.end - range.start > last.end - last.start) {
        merged[merged.length - 1] = { ...range, start: last.start };
      } else if (range.verified) {
        last.verified = true;
      }
      continue;
    }
    merged.push(range);
  }

  const segments: NarrativeSegment[] = [];
  let cursor = 0;
  for (const range of merged) {
    if (range.start > cursor) {
      segments.push({ text: narrative.slice(cursor, range.start) });
    }
    segments.push({ text: range.quote, quote: range.quote, verified: range.verified });
    cursor = range.end;
  }
  if (cursor < narrative.length) {
    segments.push({ text: narrative.slice(cursor) });
  }
  return segments.filter((segment) => segment.text.length > 0);
}
