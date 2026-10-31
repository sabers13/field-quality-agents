import { describe, expect, it } from "vitest";

import { StaticDataSource } from "./static";
import { NotFoundError } from "./source";

describe("static data source", () => {
  const source = new StaticDataSource();

  it("serves the command centre fixture", async () => {
    const data = await source.getCommandCentre();
    expect(data.kpis.length).toBeGreaterThanOrEqual(7);
    expect(data.live_feed.length).toBeGreaterThan(0);
    expect(data.window).toContain("replay set 2025");
  });

  it("filters and pages cases deterministically", async () => {
    const all = await source.getCases();
    expect(all.total).toBe(6);
    expect(all.items[0]?.received_at).toBe("2025-06-09");

    const nimbus = await source.getCases({ q: "nimbus" });
    expect(nimbus.items.map((item) => item.id)).toEqual(["C-2025-0004", "C-2025-0006"]);

    const safety = await source.getCases({ safety: true });
    expect(safety.items.map((item) => item.id)).toEqual(["C-2025-0006"]);

    const decision = await source.getCases({ status: "needs_engineer" });
    expect(decision.items.map((item) => item.id)).toEqual(["C-2025-0004"]);

    const page = await source.getCases({ limit: 2, offset: 1 });
    expect(page.total).toBe(6);
    expect(page.items).toHaveLength(2);
    expect(page.items[0]?.id).toBe("C-2025-0002");
  });

  it("returns a case detail and never leaks mutations into the bundle", async () => {
    const detail = await source.getCase("C-2025-0006");
    expect(detail.case.id).toBe("C-2025-0006");
    expect(detail.trace).toHaveLength(9);
    detail.case.narrative = "mutated";
    const again = await source.getCase("C-2025-0006");
    expect(again.case.narrative).not.toBe("mutated");
  });

  it("throws a typed not-found error for unknown ids", async () => {
    await expect(source.getCase("missing")).rejects.toBeInstanceOf(NotFoundError);
    await expect(source.getIssue("missing")).rejects.toBeInstanceOf(NotFoundError);
    await expect(source.getReplayEvents("missing")).rejects.toBeInstanceOf(NotFoundError);
  });

  it("serves issue summaries and details", async () => {
    const issues = await source.getIssues();
    expect(issues).toHaveLength(2);
    expect(issues[0]?.id).toBe("I-2025-0001");
    expect(issues[0] && "eight_d" in issues[0]).toBe(false);

    const detail = await source.getIssue("I-2025-0001");
    expect(detail.eight_d?.d4_root_cause_hypotheses).toHaveLength(3);
    expect(detail.weekly_counts.at(-1)?.count).toBe(12);
  });

  it("serves the comparison, weekly report and replay events", async () => {
    const comparison = await source.getComparison();
    expect(comparison.after.cases).toBe(600);
    expect(comparison.rows.length).toBeGreaterThan(10);

    const report = await source.getWeeklyReport();
    expect(report.week_start).toBe("2025-06-02");
    await expect(source.getWeeklyReport("2025-01-01")).rejects.toBeInstanceOf(NotFoundError);

    const runs = await source.getReplayRuns();
    expect(runs).toHaveLength(1);
    const events = await source.getReplayEvents(runs[0]?.run_id ?? "");
    expect(events.length).toBe(19);
    expect(events[0]?.seq).toBe(1);
  });

  it("is read-only", () => {
    expect("submitDecision" in source).toBe(false);
    expect("subscribe" in source).toBe(false);
  });
});
