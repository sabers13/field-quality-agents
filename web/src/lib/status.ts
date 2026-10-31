export const CASE_STATUSES = [
  "new",
  "intake",
  "analysis",
  "needs_engineer",
  "decided",
  "issue_linked",
] as const;

export type CaseStatus = (typeof CASE_STATUSES)[number];

export type StatusTone = "new" | "in_agent" | "needs_engineer" | "decided" | "issue";

export interface StatusMeta {
  label: string;
  tone: StatusTone;
  /** CSS custom-property prefix, e.g. `--status-needs-engineer`. */
  cssVar: string;
}

export const STATUS_META: Record<CaseStatus, StatusMeta> = {
  new: { label: "New", tone: "new", cssVar: "--status-new" },
  intake: { label: "In agent", tone: "in_agent", cssVar: "--status-in-agent" },
  analysis: { label: "In agent", tone: "in_agent", cssVar: "--status-in-agent" },
  needs_engineer: {
    label: "Needs engineer",
    tone: "needs_engineer",
    cssVar: "--status-needs-engineer",
  },
  decided: { label: "Decided", tone: "decided", cssVar: "--status-decided" },
  issue_linked: { label: "Issue linked", tone: "issue", cssVar: "--status-issue" },
};

export function statusTone(status: CaseStatus): StatusTone {
  return STATUS_META[status].tone;
}

export function statusLabel(status: CaseStatus): string {
  return STATUS_META[status].label;
}

/** Statuses shown as board columns; intake and analysis share the "in agent" column. */
export const BOARD_COLUMNS: { tone: StatusTone; label: string; statuses: CaseStatus[] }[] = [
  { tone: "new", label: "New", statuses: ["new"] },
  { tone: "in_agent", label: "In agent", statuses: ["intake", "analysis"] },
  { tone: "needs_engineer", label: "Needs engineer", statuses: ["needs_engineer"] },
  { tone: "decided", label: "Decided", statuses: ["decided"] },
  { tone: "issue", label: "Issue-linked", statuses: ["issue_linked"] },
];
