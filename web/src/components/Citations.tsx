import { useState } from "react";

import type { Citation } from "../types";
import { Icon } from "./Icon";
import { Modal } from "./Overlay";

const SOURCE_LABELS: Record<Citation["source_type"], string> = {
  case: "Case",
  recall: "Recall",
  investigation: "Investigation",
};

export function CitationItem({
  citation,
  onOpenSource,
}: {
  citation: Citation;
  onOpenSource?: (citation: Citation) => void;
}) {
  const sourceLabel = SOURCE_LABELS[citation.source_type];
  const body = (
    <>
      <span className="citation-head">
        <span className="citation-source">{sourceLabel}</span>
        <code>{citation.source_id}</code>
        {citation.verified ? (
          <span className="citation-state is-verified">
            <Icon name="check" size={11} /> verified
          </span>
        ) : (
          <span className="citation-state is-unverified">
            <Icon name="close" size={11} /> not verified
          </span>
        )}
      </span>
      {citation.quote ? <span className="citation-quote">“{citation.quote}”</span> : null}
    </>
  );

  if (citation.source_type === "case") {
    return (
      <li className="citation">
        <a className="citation-link" href={`#/cases/${encodeURIComponent(citation.source_id)}`}>
          {body}
        </a>
      </li>
    );
  }
  return (
    <li className="citation">
      <button type="button" className="citation-link" onClick={() => onOpenSource?.(citation)}>
        {body}
        <span className="citation-open">
          Open {sourceLabel.toLowerCase()} <Icon name="chevron" size={12} />
        </span>
      </button>
    </li>
  );
}

export function CitationList({ citations }: { citations: readonly Citation[] }) {
  const [selected, setSelected] = useState<Citation | null>(null);

  if (citations.length === 0) {
    return <p className="muted">No citations.</p>;
  }

  return (
    <>
      <ul className="citation-list">
        {citations.map((citation, index) => (
          <CitationItem
            citation={citation}
            key={`${citation.source_type}-${citation.source_id}-${index}`}
            onOpenSource={setSelected}
          />
        ))}
      </ul>
      {selected ? (
        <Modal
          title={`${SOURCE_LABELS[selected.source_type]} ${selected.source_id}`}
          onClose={() => setSelected(null)}
        >
          <p>
            This {SOURCE_LABELS[selected.source_type].toLowerCase()} is cited by the agent. The
            full source is not bundled in this view; the id and the verbatim quote are kept so the
            citation can be checked.
          </p>
          {selected.quote ? (
            <blockquote className="citation-quote-block">“{selected.quote}”</blockquote>
          ) : (
            <p className="muted">No quote is attached to this citation.</p>
          )}
          <p className="citation-state is-verified">
            {selected.verified ? <Icon name="check" size={12} /> : <Icon name="close" size={12} />}{" "}
            {selected.verified ? "Verified" : "Not verified"} citation
          </p>
        </Modal>
      ) : null}
    </>
  );
}
