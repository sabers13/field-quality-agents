import type {
  CaseDetail,
  CaseListPage,
  CaseQuery,
  CommandCentreData,
  ComparisonData,
  IssueDetail,
  IssueSummary,
  ReplayEvent,
  ReplayRun,
  WeeklyReport,
} from "../types";
import type { DashboardDataSource } from "./source";
import { NotFoundError } from "./source";
import { staticBundle } from "./bundled";
import type { StaticBundle } from "./fixtures";

function clone<T>(value: T): T {
  if (typeof structuredClone === "function") {
    return structuredClone(value);
  }
  return JSON.parse(JSON.stringify(value)) as T;
}

function matches(item: CaseDetailSummary, query: CaseQuery): boolean {
  if (query.status && item.status !== query.status) {
    return false;
  }
  if (query.group && item.group !== query.group) {
    return false;
  }
  if (query.safety !== undefined && item.safety_relevant !== query.safety) {
    return false;
  }
  if (query.q) {
    const needle = query.q.trim().toLowerCase();
    const haystack = `${item.id} ${item.make} ${item.model} ${item.component} ${item.group ?? ""}`.toLowerCase();
    if (!haystack.includes(needle)) {
      return false;
    }
  }
  return true;
}

interface CaseDetailSummary {
  id: string;
  make: string;
  model: string;
  component: string;
  group: string | null;
  status: CaseListPage["items"][number]["status"];
  safety_relevant: boolean;
}

/** Static mode: bundled JSON, no network, read-only decisions. */
export class StaticDataSource implements DashboardDataSource {
  private readonly loaded: StaticBundle | null;

  constructor(bundle: StaticBundle | null = staticBundle()) {
    this.loaded = bundle;
  }

  /** Fail loudly rather than showing invented fixtures when no export is bundled. */
  private get bundle(): StaticBundle {
    if (this.loaded === null) {
      throw new Error(
        "No exported run is bundled: run `make all` to build dist/field-quality-agents, or use live mode.",
      );
    }
    return this.loaded;
  }

  async getCommandCentre(): Promise<CommandCentreData> {
    return clone(this.bundle.commandCentre);
  }

  async getCases(query: CaseQuery = {}): Promise<CaseListPage> {
    const limit = query.limit ?? 50;
    const offset = query.offset ?? 0;
    const filtered = this.bundle.cases
      .filter((item) => matches(item, query))
      .sort((a, b) => b.received_at.localeCompare(a.received_at) || a.id.localeCompare(b.id));
    return {
      items: clone(filtered.slice(offset, offset + limit)),
      total: filtered.length,
      limit,
      offset,
    };
  }

  async getCase(id: string): Promise<CaseDetail> {
    const detail = this.bundle.caseDetails[id];
    if (!detail) {
      throw new NotFoundError(`No bundled case ${id}`);
    }
    return clone(detail);
  }

  async getIssues(): Promise<IssueSummary[]> {
    return clone(this.bundle.issues.map(toSummary));
  }

  async getIssue(id: string): Promise<IssueDetail> {
    const issue = this.bundle.issues.find((candidate) => candidate.id === id);
    if (!issue) {
      throw new NotFoundError(`No bundled issue ${id}`);
    }
    return clone(issue);
  }

  async getComparison(): Promise<ComparisonData> {
    return clone(this.bundle.comparison);
  }

  async getWeeklyReport(weekStart?: string): Promise<WeeklyReport> {
    const report = this.bundle.weeklyReport;
    if (weekStart && !report.week_start.startsWith(weekStart)) {
      throw new NotFoundError(`No bundled report for week ${weekStart}`);
    }
    return clone(report);
  }

  async getReplayRuns(): Promise<ReplayRun[]> {
    return clone(this.bundle.replay.runs);
  }

  async getReplayEvents(runId: string): Promise<ReplayEvent[]> {
    const events = this.bundle.replay.events[runId];
    if (!events) {
      throw new NotFoundError(`No bundled replay events for ${runId}`);
    }
    return clone(events);
  }
}

export function toSummary(issue: IssueDetail): IssueSummary {
  return {
    id: issue.id,
    title: issue.title,
    status: issue.status,
    opened_at: issue.opened_at,
    make: issue.make,
    model: issue.model,
    year: issue.year,
    group: issue.group,
    observed: issue.observed,
    threshold: issue.threshold,
    spike_ratio: issue.spike_ratio,
    linked_case_count: issue.linked_case_count,
  };
}
