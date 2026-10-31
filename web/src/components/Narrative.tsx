import type { CaseDetail } from "../types";
import { highlightQuotes } from "../lib/highlight";
import { Icon } from "./Icon";

export function Narrative({ detail }: { detail: CaseDetail }) {
  const clues = detail.extraction?.clues ?? [];
  const citations = [
    ...(detail.proposal?.evidence ?? []),
    ...(detail.decision?.edited_proposal?.evidence ?? []),
  ];
  const segments = highlightQuotes(detail.case.narrative, clues, citations);
  const hasQuotes = segments.some((segment) => segment.quote);

  return (
    <section className="narrative-block" aria-labelledby="narrative-heading">
      <h3 id="narrative-heading" className="subheading">
        Report narrative
      </h3>
      <p className="narrative">
        {segments.map((segment, index) =>
          segment.quote ? (
            segment.verified ? (
              <mark
                className="quote quote-verified"
                key={`${index}-${segment.text}`}
                title="Verified verbatim quote"
              >
                {segment.text}
                <span className="quote-label">
                  <Icon name="check" size={11} /> verified
                </span>
              </mark>
            ) : (
              <mark
                className="quote quote-unverified"
                key={`${index}-${segment.text}`}
                title="Not a verbatim quote in the source"
              >
                {segment.text}
                <span className="quote-label">not verified</span>
              </mark>
            )
          ) : (
            <span key={`${index}-${segment.text}`}>{segment.text}</span>
          ),
        )}
      </p>
      <p className="narrative-note">
        {hasQuotes
          ? "Highlighted spans are the agent's verbatim clues. Unverified quotes are struck through and never counted as evidence."
          : "No verbatim clue has been extracted from this narrative yet."}
      </p>
    </section>
  );
}
