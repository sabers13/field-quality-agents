import type { ReactNode } from "react";

import { STATUS_META, type CaseStatus, type StatusTone } from "../lib/status";

export function StatusBadge({ status }: { status: CaseStatus }) {
  const meta = STATUS_META[status];
  return <ToneBadge tone={meta.tone} label={meta.label} />;
}

export function ToneBadge({
  tone,
  label,
  quiet = false,
}: {
  tone: StatusTone;
  label: string;
  quiet?: boolean;
}) {
  return (
    <span className={`badge${quiet ? " badge-quiet" : ""}`} data-tone={tone}>
      <span className="badge-dot" aria-hidden="true" />
      {label}
    </span>
  );
}

export function ToneDot({ tone }: { tone: StatusTone }) {
  return <span className="status-dot" data-tone={tone} aria-hidden="true" />;
}

export function Meta({ children }: { children: ReactNode }) {
  return <span className="meta">{children}</span>;
}
