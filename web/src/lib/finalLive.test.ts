import { describe, expect, it } from "vitest";

import { finalLiveRows, finalLiveRowsChanged } from "./finalLive";
import type { FinalLiveData, Metrics } from "../types";

function metrics(overrides: Record<string, unknown>): Metrics {
  return {
    cases: 150,
    group_macro_f1: null,
    group_coverage: null,
    safety_precision: null,
    safety_recall: null,
    quote_grounding_rate: null,
    citation_validity_rate: null,
    targeted_test_share: null,
    targeted_test_with_quote_share: null,
    issue_precision: null,
    issue_median_lead_days: null,
    issue_base_rate: null,
    recall_link_match_rate: null,
    human_touches_per_case: null,
    decided_without_edits_share: null,
    steps_per_case: null,
    cost_per_1000_cases_usd: null,
    latency_p50_ms: null,
    latency_p95_ms: null,
    budget_hits: 0,
    ...overrides,
  } as Metrics;
}

const data: FinalLiveData = {
  run_id: "final-live",
  set_name: "final_live",
  window_start: "2026-09-28",
  window_end: "2026-10-25",
  spend_usd: 0.25,
  steps: 600,
  budget_hits: 0,
  q9_run_id: "replay",
  q9: {
    cases: 600,
    before: metrics({ cases: 600 }),
    after: metrics({
      cases: 600,
      group_macro_f1: { value: 0.5, ci_low: null, ci_high: null, n: 600 },
      safety_recall: { value: 0.9, ci_low: null, ci_high: null, n: 600 },
    }),
  },
  final: {
    cases: 150,
    before: metrics({}),
    after: metrics({
      group_macro_f1: { value: 0.42, ci_low: null, ci_high: null, n: 150 },
      safety_recall: { value: 0.81, ci_low: null, ci_high: null, n: 150 },
    }),
  },
};

describe("finalLiveRows", () => {
  it("reads the agentic values from both runs", () => {
    const rows = finalLiveRows(data);
    const f1 = rows.find((row) => row.metric === "group_macro_f1");
    const recall = rows.find((row) => row.metric === "safety_recall");
    expect(f1?.q9).toBeCloseTo(0.5);
    expect(f1?.final).toBeCloseTo(0.42);
    expect(recall?.final).toBeCloseTo(0.81);
  });

  it("keeps a withheld value null instead of zero", () => {
    const rows = finalLiveRows(data);
    const coverage = rows.find((row) => row.metric === "safety_precision");
    expect(coverage?.q9).toBeNull();
    expect(coverage?.final).toBeNull();
  });

  it("counts the rows that moved", () => {
    expect(finalLiveRowsChanged(finalLiveRows(data))).toBeGreaterThan(0);
  });
});
