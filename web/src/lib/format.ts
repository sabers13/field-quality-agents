/** Number, date and metric formatting shared by every page. */

export type MetricKind = "percent" | "score" | "days" | "money" | "per1000" | "ms" | "integer" | "tokens";

interface MetricMeta {
  label: string;
  kind: MetricKind;
}

const METRIC_META: Record<string, MetricMeta> = {
  group_macro_f1: { label: "Group macro F1", kind: "score" },
  group_coverage: { label: "Group coverage", kind: "percent" },
  safety_precision: { label: "Safety precision", kind: "percent" },
  safety_recall: { label: "Safety recall", kind: "percent" },
  quote_grounding_rate: { label: "Quote grounding", kind: "percent" },
  citation_validity_rate: { label: "Citation validity", kind: "percent" },
  targeted_test_share: { label: "Targeted test share", kind: "percent" },
  targeted_test_with_quote_share: { label: "Targeted test with quote", kind: "percent" },
  issue_precision: { label: "Issue precision", kind: "percent" },
  issue_median_lead_days: { label: "Issue lead time", kind: "days" },
  issue_base_rate: { label: "Issue base rate", kind: "percent" },
  recall_link_match_rate: { label: "Recall link match", kind: "percent" },
  human_touches_per_case: { label: "Human touches / case", kind: "score" },
  decided_without_edits_share: { label: "Prepared without human edits", kind: "percent" },
  steps_per_case: { label: "Steps / case", kind: "score" },
  cost_per_1000_cases_usd: { label: "Cost / 1,000 cases", kind: "per1000" },
  latency_p50_ms: { label: "Latency p50", kind: "ms" },
  latency_p95_ms: { label: "Latency p95", kind: "ms" },
  budget_hits: { label: "Budget hits", kind: "integer" },
  cases: { label: "Cases", kind: "integer" },
};

export function metricMeta(metric: string, fallbackLabel?: string): MetricMeta {
  const known = METRIC_META[metric];
  if (known) {
    return known;
  }
  return { label: fallbackLabel ?? humanizeToken(metric), kind: "score" };
}

export function humanizeToken(token: string): string {
  const words = token.split("_").filter(Boolean);
  if (words.length === 0) {
    return token;
  }
  const first = words[0] ?? token;
  return [first.charAt(0).toUpperCase() + first.slice(1), ...words.slice(1)].join(" ");
}

const integerFormatter = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const oneDecimalFormatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function formatInteger(value: number): string {
  return integerFormatter.format(Math.round(value));
}

export function formatScore(value: number, digits = 2): string {
  return value.toFixed(digits);
}

export function formatPercent(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatMoney(value: number, options: { perCase?: boolean } = {}): string {
  const digits = options.perCase && Math.abs(value) < 0.01 ? 4 : 2;
  return `$${value.toFixed(digits)}`;
}

export function formatDate(value: string): string {
  return value.slice(0, 10);
}

export function formatDateTime(value: string): string {
  const date = value.slice(0, 10);
  const time = value.slice(11, 16);
  return time ? `${date} ${time} UTC` : date;
}

export function formatRelative(value: string, now: number = Date.now()): string {
  const then = Date.parse(value);
  if (Number.isNaN(then)) {
    return value;
  }
  const seconds = Math.max(0, Math.round((now - then) / 1000));
  if (seconds < 60) {
    return "just now";
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${minutes} min ago`;
  }
  const hours = Math.round(minutes / 60);
  if (hours < 24) {
    return `${hours} h ago`;
  }
  const days = Math.round(hours / 24);
  if (days < 30) {
    return `${days} d ago`;
  }
  const months = Math.round(days / 30);
  return `${months} mo ago`;
}

export function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${formatInteger(ms)} ms`;
  }
  return `${(ms / 1000).toFixed(1)} s`;
}

export function formatTokens(tokens: number): string {
  if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(1)}k`;
  }
  return formatInteger(tokens);
}

export function formatMetricValue(value: number, kind: MetricKind): string {
  switch (kind) {
    case "percent":
      return formatPercent(value);
    case "score":
      return formatScore(value);
    case "days":
      return `${oneDecimalFormatter.format(value)} d`;
    case "money":
      return formatMoney(value, { perCase: value < 0.01 });
    case "per1000":
      return formatMoney(value);
    case "ms":
      return `${formatInteger(value)} ms`;
    case "integer":
      return formatInteger(value);
    case "tokens":
      return formatTokens(value);
  }
}

/** One before/after headline: its unit decides the format, not a single default. */
export function formatHeadlineValue(unit: string, value: number): string {
  if (unit === "USD") {
    return formatMoney(value);
  }
  if (unit === "per case") {
    return formatScore(value, 1);
  }
  return formatPercent(value);
}

/** The change arrow in the headline's own unit (points, dollars or per-case). */
export function formatHeadlineDelta(unit: string, delta: number): string {
  const sign = delta >= 0 ? "+" : "−";
  const size = Math.abs(delta);
  if (unit === "USD") {
    return `${sign}${formatMoney(size)}`;
  }
  if (unit === "per case") {
    return `${sign}${size.toFixed(1)}`;
  }
  return `${sign}${(size * 100).toFixed(1)} pts`;
}

/** Metrics where a smaller number is the better outcome. */
const LOWER_IS_BETTER = new Set(["cost_per_1000_cases_usd", "human_touches_per_case"]);

/** Whether a headline change reads as good, bad or neutral. */
export function headlineTone(id: string, delta: number): "good" | "bad" | "neutral" {
  if (delta === 0) {
    return "neutral";
  }
  const good = LOWER_IS_BETTER.has(id) ? delta < 0 : delta > 0;
  return good ? "good" : "bad";
}

export interface EstimateLike {
  value: number;
  ci_low: number | null;
  ci_high: number | null;
  n: number;
}

export function formatEstimate(estimate: EstimateLike, kind: MetricKind): string {
  const value = formatMetricValue(estimate.value, kind);
  if (estimate.ci_low === null || estimate.ci_high === null) {
    return value;
  }
  return `${value} (${formatMetricValue(estimate.ci_low, kind)}–${formatMetricValue(estimate.ci_high, kind)})`;
}

export function isEstimate(value: unknown): value is EstimateLike {
  return (
    typeof value === "object" &&
    value !== null &&
    "value" in value &&
    typeof (value as { value: unknown }).value === "number"
  );
}

/** Plain-language summary of a stream event, used by the feed and replay. */
export function describeStreamEvent(event: import("../types").StreamEvent): string {
  const data = event.data;
  switch (event.kind) {
    case "case_status": {
      const caseId = String(data.case_id ?? "case");
      const status = String(data.status ?? "").replaceAll("_", " ");
      return `${caseId} moved to ${status}`;
    }
    case "trace": {
      const caseId = String(data.case_id ?? "case");
      const step = data.step as { agent?: string; action?: string } | undefined;
      return `${caseId}: ${step?.agent ?? "agent"} ${step?.action ?? "acted"}`;
    }
    case "issue": {
      return `Issue ${String(data.issue_id ?? "")} is ${String(data.status ?? "open")}`;
    }
    case "run": {
      return `Run ${String(data.run_id ?? "")} ${String(data.status ?? "")}`;
    }
    case "heartbeat":
      return "Stream heartbeat";
    case "connection": {
      return String(data.status) === "open" ? "Live stream connected" : "Live stream disconnected";
    }
  }
}
