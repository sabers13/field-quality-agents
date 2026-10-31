import type { CaseStatus } from "./status";
import { isCaseStatus } from "./status";
import type { ReplayEvent, ReplayEventKind } from "../types";

export interface ReplayCaseState {
  caseId: string;
  status: CaseStatus | null;
  lastSummary: string;
}

export interface ReplaySummary {
  revealed: number;
  cases: ReplayCaseState[];
  counts: Record<ReplayEventKind, number>;
}

const EMPTY_COUNTS: Record<ReplayEventKind, number> = {
  case: 0,
  trace: 0,
  decision: 0,
  issue: 0,
  report: 0,
};

function summaryFor(event: ReplayEvent): string {
  const value = event.payload["summary"] ?? event.payload["action"] ?? event.kind;
  return String(value);
}

/**
 * Derive the visible case state after the first `upto` replay events.
 * Replay events are served in sequence order; this pure function keeps the
 * playback UI honest and testable without a timer.
 */
export function summariseReplay(events: readonly ReplayEvent[], upto: number): ReplaySummary {
  const bounded = Math.max(0, Math.min(upto, events.length));
  const cases = new Map<string, ReplayCaseState>();
  const counts = { ...EMPTY_COUNTS };

  for (const event of events.slice(0, bounded)) {
    counts[event.kind] += 1;
    const caseId = event.case_id ?? (typeof event.payload["case_id"] === "string" ? event.payload["case_id"] : undefined);
    if (!caseId) {
      continue;
    }
    const previous = cases.get(caseId) ?? { caseId, status: null, lastSummary: "" };
    const status = event.payload["status"];
    cases.set(caseId, {
      caseId,
      status: isCaseStatus(status) ? status : previous.status,
      lastSummary: summaryFor(event),
    });
  }

  return {
    revealed: bounded,
    cases: [...cases.values()].sort((a, b) => a.caseId.localeCompare(b.caseId)),
    counts,
  };
}

export interface ReplayDay {
  day: string;
  events: ReplayEvent[];
}

export function groupReplayByDay(events: readonly ReplayEvent[]): ReplayDay[] {
  const byDay = new Map<string, ReplayEvent[]>();
  for (const event of events) {
    const day = event.at.slice(0, 10);
    const bucket = byDay.get(day);
    if (bucket) {
      bucket.push(event);
    } else {
      byDay.set(day, [event]);
    }
  }
  return [...byDay.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, dayEvents]) => ({ day, events: dayEvents }));
}

export function replayEventText(event: ReplayEvent): string {
  const summary = event.payload["summary"];
  if (typeof summary === "string" && summary.length > 0) {
    return summary;
  }
  const action = event.payload["action"];
  if (typeof action === "string" && action.length > 0) {
    return action;
  }
  switch (event.kind) {
    case "case":
      return "Case arrived";
    case "trace":
      return "Agent step";
    case "decision":
      return "Human decision";
    case "issue":
      return "Issue opened";
    case "report":
      return "Weekly report generated";
  }
}
