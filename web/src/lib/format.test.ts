import { describe, expect, it } from "vitest";

import {
  describeStreamEvent,
  formatDateTime,
  formatEstimate,
  formatInteger,
  formatMetricValue,
  formatMoney,
  formatPercent,
  formatRelative,
  isEstimate,
  metricMeta,
} from "./format";

describe("formatting", () => {
  it("formats integers and percentages to the design rules", () => {
    expect(formatInteger(12345)).toBe("12,345");
    expect(formatPercent(0.523)).toBe("52.3%");
    expect(formatMetricValue(0.68, "score")).toBe("0.68");
    expect(formatMetricValue(11.2, "days")).toBe("11.2 d");
  });

  it("formats spend and per-case money at the documented precision", () => {
    expect(formatMoney(5.4)).toBe("$5.40");
    expect(formatMoney(0.0054, { perCase: true })).toBe("$0.0054");
    expect(formatMetricValue(0.12, "money")).toBe("$0.12");
  });

  it("formats dates and relative times deterministically", () => {
    expect(formatDateTime("2025-06-09T09:41:12Z")).toBe("2025-06-09 09:41 UTC");
    const now = Date.parse("2025-06-09T12:00:00Z");
    expect(formatRelative("2025-06-09T11:55:00Z", now)).toBe("5 min ago");
    expect(formatRelative("2025-06-08T12:00:00Z", now)).toBe("1 d ago");
  });

  it("keeps confidence intervals beside the estimate", () => {
    const estimate = { value: 0.68, ci_low: 0.64, ci_high: 0.71, n: 600 };
    expect(formatEstimate(estimate, "score")).toBe("0.68 (0.64–0.71)");
    expect(isEstimate(estimate)).toBe(true);
    expect(isEstimate(0.68)).toBe(false);
  });

  it("knows the PLAN metric labels and kinds", () => {
    expect(metricMeta("quote_grounding_rate")).toEqual({
      label: "Quote grounding",
      kind: "percent",
    });
    expect(metricMeta("unknown_metric", "Custom label").label).toBe("Custom label");
  });

  it("describes stream events without exposing raw payloads", () => {
    expect(
      describeStreamEvent({
        kind: "case_status",
        at: "2025-06-09T09:00:00Z",
        data: { case_id: "C-1", status: "analysis" },
      }),
    ).toBe("C-1 moved to analysis");
  });
});
