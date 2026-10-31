import { describe, expect, it } from "vitest";

import { groupReplayByDay, replayEventText, summariseReplay } from "./replay";
import type { ReplayEvent } from "../types";

const events: ReplayEvent[] = [
  {
    seq: 1,
    at: "2025-06-02T08:00:00Z",
    kind: "case",
    case_id: "C-1",
    payload: { status: "new", summary: "C-1 arrived" },
  },
  {
    seq: 2,
    at: "2025-06-02T08:05:00Z",
    kind: "trace",
    case_id: "C-1",
    payload: { status: "analysis", summary: "Analysis ran" },
  },
  {
    seq: 3,
    at: "2025-06-03T09:00:00Z",
    kind: "decision",
    case_id: "C-1",
    payload: { status: "decided", summary: "Approved" },
  },
  {
    seq: 4,
    at: "2025-06-03T10:00:00Z",
    kind: "issue",
    issue_id: "I-1",
    payload: { summary: "Issue opened" },
  },
];

describe("replay helpers", () => {
  it("counts revealed events and derives case state", () => {
    const summary = summariseReplay(events, 3);
    expect(summary.revealed).toBe(3);
    expect(summary.counts).toEqual({ case: 1, trace: 1, decision: 1, issue: 0, report: 0 });
    expect(summary.cases).toEqual([
      { caseId: "C-1", status: "decided", lastSummary: "Approved" },
    ]);
  });

  it("never reveals past the end or before the start", () => {
    expect(summariseReplay(events, 99).revealed).toBe(4);
    expect(summariseReplay(events, -3).revealed).toBe(0);
    expect(summariseReplay(events, 0).cases).toEqual([]);
  });

  it("groups events by day in order", () => {
    expect(groupReplayByDay(events).map((day) => [day.day, day.events.length])).toEqual([
      ["2025-06-02", 2],
      ["2025-06-03", 2],
    ]);
  });

  it("falls back to a plain kind label", () => {
    expect(replayEventText({ seq: 5, at: "2025-06-03T10:00:00Z", kind: "report", payload: {} })).toBe(
      "Weekly report generated",
    );
  });
});
