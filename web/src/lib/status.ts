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

export interface BoardColumn {
  id: CaseStatus;
  /** Column heading. Intake and analysis are separate columns that share the
   * "In agent" status tone, per PLAN §6 and DESIGN.md's six-column board. */
  header: string;
  tone: StatusTone;
  statuses: CaseStatus[];
}

/** The six PLAN §6 board columns, in workflow order. */
export const BOARD_COLUMNS: BoardColumn[] = [
  { id: "new", header: "New", tone: "new", statuses: ["new"] },
  { id: "intake", header: "Intake", tone: "in_agent", statuses: ["intake"] },
  { id: "analysis", header: "Analysis", tone: "in_agent", statuses: ["analysis"] },
  {
    id: "needs_engineer",
    header: "Needs engineer",
    tone: "needs_engineer",
    statuses: ["needs_engineer"],
  },
  { id: "decided", header: "Decided", tone: "decided", statuses: ["decided"] },
  { id: "issue_linked", header: "Issue-linked", tone: "issue", statuses: ["issue_linked"] },
];

export function statusTone(status: CaseStatus): StatusTone {
  return STATUS_META[status].tone;
}

export function statusLabel(status: CaseStatus): string {
  return STATUS_META[status].label;
}

export function isCaseStatus(value: unknown): value is CaseStatus {
  return typeof value === "string" && (CASE_STATUSES as readonly string[]).includes(value);
}

export function isStatusTone(value: unknown): value is StatusTone {
  return (
    value === "new" ||
    value === "in_agent" ||
    value === "needs_engineer" ||
    value === "decided" ||
    value === "issue"
  );
}
