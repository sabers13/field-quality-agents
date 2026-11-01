/**
 * Transport types for the dashboard.
 *
 * JSON field names match `src/field_quality_agents/contracts.py` and
 * `docs/INTERFACES.md`. Timestamps are ISO 8601 strings in the transport layer;
 * dates are `YYYY-MM-DD`. Ids are opaque strings and are never parsed.
 */

import type { CaseStatus } from "./lib/status";

export type { CaseStatus };

export type ClueKind =
  | "component_group"
  | "symptom"
  | "condition"
  | "fault_code"
  | "safety"
  | "other";

export type ProposalKind =
  | "standard_test"
  | "targeted_load_test"
  | "safety_priority"
  | "evidence_pack"
  | "request_info";

export type DecisionAction = "approve" | "override" | "ask" | "request_info";
export type DecisionActor = "simulated_engineer" | "live_engineer";
export type SourceType = "case" | "recall" | "investigation";
export type IssueStatus = "open" | "monitoring" | "closed";
export type EightDStatus = "draft" | "approved" | "rejected";

export interface Clue {
  kind: ClueKind;
  quote: string;
}

export interface Extraction {
  case_id: string;
  group: string;
  summary: string;
  symptoms: string[];
  conditions: string[];
  fault_codes: string[];
  clues: Clue[];
  safety_relevant: boolean;
}

export interface Citation {
  source_type: SourceType;
  source_id: string;
  quote: string | null;
  verified: boolean;
}

export interface TargetedTest {
  name: string;
  conditions: string[];
  reason: string;
}

export interface Proposal {
  case_id: string;
  kind: ProposalKind;
  summary: string;
  rationale: string;
  targeted_test: TargetedTest | null;
  evidence: Citation[];
  requested_info: string[];
  created_at: string;
}

export interface TraceStep {
  step: number;
  agent: string;
  action: string;
  reason: string;
  tool: string | null;
  tool_input: Record<string, unknown> | null;
  tool_output: Record<string, unknown> | null;
  started_at: string;
  duration_ms: number;
  tokens: number;
  cost_usd: number;
}

export interface HumanDecision {
  case_id: string;
  action: DecisionAction;
  actor: DecisionActor;
  rationale: string;
  decided_at: string;
  proposal_kind: ProposalKind | null;
  edited_proposal: Proposal | null;
}

export interface Case {
  id: string;
  received_at: string;
  make: string;
  model: string;
  year: number;
  component: string;
  narrative: string;
  group: string | null;
  status: CaseStatus;
  safety_relevant: boolean;
  source: "nhtsa";
  source_id: string | null;
  mileage: number | null;
}

export interface WeekCount {
  week_start: string;
  count: number;
}

export interface IssueSummary {
  id: string;
  title: string;
  status: IssueStatus;
  opened_at: string;
  make: string;
  model: string;
  year: number;
  group: string;
  observed: number;
  threshold: number;
  spike_ratio: number;
  linked_case_count: number;
}

export interface EightD {
  id: string;
  issue_id: string;
  d1_team: string[];
  d2_problem: string;
  d3_containment: string;
  d4_root_cause_hypotheses: string[];
  citations: Citation[];
  status: EightDStatus;
  created_at: string;
  updated_at: string | null;
}

export interface DecisionMemo {
  id: string;
  issue_id: string;
  title: string;
  body: string;
  citations: Citation[];
  created_at: string;
}

export interface IssueDetail extends IssueSummary {
  weekly_counts: WeekCount[];
  linked_case_ids: string[];
  linked_recall_ids: string[];
  linked_investigation_ids: string[];
  eight_d: EightD | null;
  memo: DecisionMemo | null;
}

export interface MetricEstimate {
  value: number;
  ci_low: number | null;
  ci_high: number | null;
  n: number;
}

export interface Metrics {
  cases: number;
  group_macro_f1: MetricEstimate | null;
  group_coverage: MetricEstimate | null;
  safety_precision: MetricEstimate | null;
  safety_recall: MetricEstimate | null;
  quote_grounding_rate: MetricEstimate | null;
  citation_validity_rate: MetricEstimate | null;
  targeted_test_share: MetricEstimate | null;
  targeted_test_with_quote_share: MetricEstimate | null;
  issue_precision: MetricEstimate | null;
  issue_median_lead_days: number | null;
  issue_base_rate: number | null;
  recall_link_match_rate: MetricEstimate | null;
  human_touches_per_case: number | null;
  decided_without_edits_share: number | null;
  steps_per_case: number | null;
  cost_per_1000_cases_usd: number | null;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  budget_hits: number;
}

export interface WeeklyReport {
  week_start: string;
  week_end: string;
  generated_at: string;
  cases_received: number;
  cases_decided: number;
  cases_needing_engineer: number;
  open_issues: number;
  proposals_targeted_test: number;
  metrics: Metrics;
  narrative: string;
}

export interface Kpi {
  id: string;
  label: string;
  value: number | string;
  unit?: string;
  context: string;
  delta?: number;
  tone?: "neutral" | "good" | "watch" | "issue";
  series?: number[];
}

export type StreamEventKind =
  | "heartbeat"
  | "case_status"
  | "trace"
  | "issue"
  | "run"
  | "connection";

/** One event from the SSE stream or a bundled feed. */
export interface StreamEvent {
  id?: string;
  kind: StreamEventKind;
  at: string;
  data: Record<string, unknown>;
}

export interface ComparisonSummary {
  headline: {
    id: string;
    label: string;
    before: number;
    after: number;
    unit: string;
  }[];
  examples: { case_id: string; before: string; after: string; note: string }[];
}

export interface ComparisonRow {
  metric: string;
  label: string;
  before: MetricEstimate | number | null;
  after: MetricEstimate | number | null;
  note?: string;
}

export interface ComparisonData {
  before: Metrics;
  after: Metrics;
  summary: ComparisonSummary;
  rows: ComparisonRow[];
}

/** One pipeline's metrics on one case set (Q14's panel). */
export interface FinalLiveSide {
  cases: number;
  before: Metrics;
  after: Metrics;
}

/** Q14's final live run beside the Q9 replay run. */
export interface FinalLiveData {
  run_id: string;
  set_name: string;
  window_start: string;
  window_end: string;
  spend_usd: number;
  steps: number;
  budget_hits: number;
  final: FinalLiveSide;
  q9: FinalLiveSide;
  q9_run_id: string;
}

export interface CommandCentreData {
  window: string;
  kpis: Kpi[];
  live_feed: StreamEvent[];
  comparison: ComparisonSummary;
  final_live?: FinalLiveData | null;
}

export interface CaseListItem {
  id: string;
  received_at: string;
  make: string;
  model: string;
  year: number;
  component: string;
  group: string | null;
  status: CaseStatus;
  safety_relevant: boolean;
  evidence_count: number;
  human_touches: number;
}

export interface CaseListPage {
  items: CaseListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface SimilarCase {
  id: string;
  score: number;
  make: string;
  model: string;
  year: number;
  group: string;
  excerpt: string;
}

export interface RecallRef {
  id: string;
  summary: string;
  open_date: string;
  match: boolean;
}

export interface InvestigationRef {
  id: string;
  summary: string;
  open_date: string;
  match: boolean;
}

export interface CaseDetail {
  case: Case;
  extraction: Extraction | null;
  proposal: Proposal | null;
  trace: TraceStep[];
  decision: HumanDecision | null;
  similar_cases: SimilarCase[];
  recalls: RecallRef[];
  investigations: InvestigationRef[];
}

export interface ReplayRun {
  run_id: string;
  set_name: string;
  started_at: string;
  status: "running" | "complete" | "failed";
  case_count: number;
}

export type ReplayEventKind = "case" | "trace" | "decision" | "issue" | "report";

export interface ReplayEvent {
  seq: number;
  at: string;
  kind: ReplayEventKind;
  case_id?: string;
  issue_id?: string;
  payload: Record<string, unknown>;
}

export interface CaseQuery {
  status?: CaseStatus;
  group?: string;
  safety?: boolean;
  q?: string;
  limit?: number;
  offset?: number;
}

export interface DecisionRequest {
  action: DecisionAction;
  rationale: string;
  edited_proposal: Proposal | null;
}

export interface DecisionResponse {
  case: Case;
  trace: TraceStep[];
  pending: HumanDecision | null;
  issue_ids: string[];
}
