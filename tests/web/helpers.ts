import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { Page, Route } from "@playwright/test";

const FIXTURE_DIR = resolve(__dirname, "../../web/src/data/fixtures");

function readJson<T>(relativePath: string): T {
  return JSON.parse(readFileSync(resolve(FIXTURE_DIR, relativePath), "utf8")) as T;
}

export const fixtures = {
  commandCentre: readJson<Record<string, unknown>>("command_centre.json"),
  cases: readJson<Record<string, unknown>[]>("cases.json"),
  case4: readJson<Record<string, unknown>>("cases/C-2025-0004.json"),
  issues: readJson<Record<string, unknown>[]>("issues.json"),
  comparison: readJson<Record<string, unknown>>("comparison.json"),
  weekly: readJson<Record<string, unknown>>("weekly_report.json"),
  replay: readJson<{ runs: Record<string, unknown>[]; events: Record<string, Record<string, unknown>[]> }>(
    "replay.json",
  ),
};

async function json(route: Route, body: unknown, status = 200): Promise<void> {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

function issueSummary(issue: Record<string, unknown>): Record<string, unknown> {
  const keys = [
    "id",
    "title",
    "status",
    "opened_at",
    "make",
    "model",
    "year",
    "group",
    "observed",
    "threshold",
    "spike_ratio",
    "linked_case_count",
  ];
  return Object.fromEntries(keys.map((key) => [key, issue[key]]));
}

export interface LiveMockOptions {
  /** Called after a decision POST so the test can assert the posted body. */
  onDecision?: (body: Record<string, unknown>) => void;
}

/**
 * Mock Q7's API for the live-mode keyboard tests. The routes mirror
 * docs/INTERFACES.md; the SSE endpoint returns 503 so the UI shows the
 * reconnecting state without hanging the test.
 */
export async function mockLiveApi(page: Page, options: LiveMockOptions = {}): Promise<void> {
  let decided = false;

  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === "/api/events") {
      await route.fulfill({ status: 503, body: "" });
      return;
    }
    if (path === "/api/kpis") {
      await json(route, fixtures.commandCentre);
      return;
    }
    if (path === "/api/cases" && request.method() === "GET") {
      await json(route, {
        items: fixtures.cases,
        total: fixtures.cases.length,
        limit: 50,
        offset: 0,
      });
      return;
    }
    if (path === "/api/cases/C-2025-0004/decision" && request.method() === "POST") {
      const body = request.postDataJSON() as Record<string, unknown>;
      options.onDecision?.(body);
      decided = true;
      await json(route, {
        case: { ...(fixtures.case4.case as Record<string, unknown>), status: "decided" },
        trace: [],
        pending: null,
        issue_ids: [],
      });
      return;
    }
    if (path === "/api/cases/C-2025-0004") {
      const detail = fixtures.case4 as Record<string, unknown>;
      const baseCase = detail.case as Record<string, unknown>;
      await json(route, {
        ...detail,
        case: { ...baseCase, status: decided ? "decided" : baseCase.status },
        decision: decided
          ? {
              case_id: "C-2025-0004",
              action: "approve",
              actor: "live_engineer",
              rationale: "Approved in the keyboard test.",
              decided_at: "2025-06-09T12:00:00Z",
              proposal_kind: "targeted_load_test",
              edited_proposal: null,
            }
          : detail.decision,
      });
      return;
    }
    if (path.startsWith("/api/cases/")) {
      await json(route, { detail: "not found" }, 404);
      return;
    }
    if (path === "/api/issues") {
      await json(route, { items: fixtures.issues.map(issueSummary) });
      return;
    }
    if (path === "/api/issues/I-2025-0001") {
      await json(route, fixtures.issues[0]);
      return;
    }
    if (path === "/api/comparison") {
      await json(route, fixtures.comparison);
      return;
    }
    if (path === "/api/reports/weekly") {
      await json(route, fixtures.weekly);
      return;
    }
    if (path === "/api/replay/runs") {
      await json(route, { items: fixtures.replay.runs });
      return;
    }
    if (path.startsWith("/api/replay/runs/") && path.endsWith("/events")) {
      const runId = decodeURIComponent(path.split("/")[4] ?? "");
      await json(route, { items: fixtures.replay.events[runId] ?? [] });
      return;
    }
    await json(route, { detail: `unmocked ${path}` }, 404);
  });
}
