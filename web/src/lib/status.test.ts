import { describe, expect, it } from "vitest";

import { BOARD_COLUMNS, CASE_STATUSES, STATUS_META, statusLabel, statusTone } from "./status";

describe("case status mapping", () => {
  it("maps every contract status to a design tone", () => {
    expect(CASE_STATUSES).toHaveLength(6);
    for (const status of CASE_STATUSES) {
      expect(STATUS_META[status].cssVar.startsWith("--status-")).toBe(true);
      expect(STATUS_META[status].label.length).toBeGreaterThan(0);
    }
  });

  it("keeps six board columns while intake and analysis share the in-agent tone", () => {
    expect(BOARD_COLUMNS).toHaveLength(6);
    expect(BOARD_COLUMNS.map((column) => column.id)).toEqual([
      "new",
      "intake",
      "analysis",
      "needs_engineer",
      "decided",
      "issue_linked",
    ]);
    const intake = BOARD_COLUMNS.find((column) => column.id === "intake");
    const analysis = BOARD_COLUMNS.find((column) => column.id === "analysis");
    expect(intake?.statuses).toEqual(["intake"]);
    expect(analysis?.statuses).toEqual(["analysis"]);
    expect(intake?.tone).toBe("in_agent");
    expect(analysis?.tone).toBe("in_agent");
    expect(statusTone("analysis")).toBe("in_agent");
  });

  it("uses plain labels", () => {
    expect(statusLabel("needs_engineer")).toBe("Needs engineer");
    expect(statusLabel("issue_linked")).toBe("Issue linked");
  });
});
