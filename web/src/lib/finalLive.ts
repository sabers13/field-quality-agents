/** Rows for Q14's "Final live test" panel. */

import { isEstimate, metricMeta, type MetricKind } from "./format";
import type { FinalLiveData, Metrics } from "../types";

export interface FinalLiveRow {
  metric: string;
  label: string;
  kind: MetricKind;
  q9: number | null;
  final: number | null;
}

/** The PLAN §7 rows that are comparable between Q9 and the unseen set. */
const ROW_METRICS = [
  "group_macro_f1",
  "safety_precision",
  "safety_recall",
  "targeted_test_share",
  "targeted_test_with_quote_share",
  "quote_grounding_rate",
  "citation_validity_rate",
  "issue_precision",
  "issue_base_rate",
  "human_touches_per_case",
  "steps_per_case",
  "cost_per_1000_cases_usd",
  "budget_hits",
] as const;

function metricValue(metrics: Metrics, metric: string): number | null {
  const value = (metrics as unknown as Record<string, unknown>)[metric];
  if (typeof value === "number") {
    return value;
  }
  if (isEstimate(value)) {
    return value.value;
  }
  return null;
}

/**
 * Build the panel rows from committed metrics only.
 *
 * Both columns are the agentic ("after") numbers: Q9's 600 recorded cases and
 * the 150 cases the desk had never seen before Q14. A withheld value stays
 * `null` and renders as an em dash rather than as zero.
 */
export function finalLiveRows(data: FinalLiveData): FinalLiveRow[] {
  return ROW_METRICS.map((metric) => {
    const meta = metricMeta(metric);
    return {
      metric,
      label: meta.label,
      kind: meta.kind,
      q9: metricValue(data.q9.after, metric),
      final: metricValue(data.final.after, metric),
    };
  });
}

/** Whether anything in the panel changed enough to call out. */
export function finalLiveRowsChanged(rows: FinalLiveRow[]): number {
  return rows.filter(
    (row) =>
      row.q9 !== null &&
      row.final !== null &&
      Math.abs(row.final - row.q9) > 0.0005,
  ).length;
}
