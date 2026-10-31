import { describe, expect, it } from "vitest";

import { fixtureBundle } from "./fixtures";
import { CASE_STATUSES } from "../lib/status";

const VALID_KINDS = ["case", "trace", "decision", "issue", "report"];

describe("bundled fixtures", () => {
  it("covers every contract case status", () => {
    const statuses = new Set(fixtureBundle.cases.map((item) => item.status));
    for (const status of CASE_STATUSES) {
      expect(statuses.has(status)).toBe(true);
    }
  });

  it("keeps list and detail records in sync", () => {
    for (const item of fixtureBundle.cases) {
      const detail = fixtureBundle.caseDetails[item.id];
      expect(detail, item.id).toBeDefined();
      expect(detail?.case.id).toBe(item.id);
      expect(detail?.case.status).toBe(item.status);
      expect(detail?.case.make).toBe(item.make);
      expect(detail?.case.safety_relevant).toBe(item.safety_relevant);
    }
  });

  it("numbers trace steps contiguously from one", () => {
    for (const detail of Object.values(fixtureBundle.caseDetails)) {
      expect(detail.trace.map((step) => step.step)).toEqual(
        detail.trace.map((_, index) => index + 1),
      );
    }
  });

  it("links every issue case id to a real case", () => {
    for (const issue of fixtureBundle.issues) {
      for (const id of issue.linked_case_ids) {
        expect(fixtureBundle.caseDetails[id], id).toBeDefined();
      }
      expect(issue.weekly_counts.length).toBeGreaterThan(0);
      expect(issue.threshold).toBeGreaterThan(0);
    }
  });

  it("has a self-consistent comparison and replay set", () => {
    expect(fixtureBundle.comparison.before.cases).toBe(fixtureBundle.comparison.after.cases);
    expect(fixtureBundle.comparison.rows.length).toBeGreaterThan(0);
    const runs = fixtureBundle.replay.runs;
    expect(runs.length).toBeGreaterThan(0);
    for (const run of runs) {
      const events = fixtureBundle.replay.events[run.run_id] ?? [];
      expect(events.length).toBeGreaterThan(0);
      expect(events.map((event) => event.seq)).toEqual(
        [...events.map((event) => event.seq)].sort((a, b) => a - b),
      );
      for (const event of events) {
        expect(VALID_KINDS).toContain(event.kind);
      }
      expect(new Set(events.map((event) => event.seq)).size).toBe(events.length);
    }
  });

  it("uses no real-world private data in fixture narratives", () => {
    for (const detail of Object.values(fixtureBundle.caseDetails)) {
      expect(detail.case.narrative).not.toMatch(/@|https?:\/\//);
    }
  });
});
