import type {
  CaseDetail,
  CaseListPage,
  CaseQuery,
  CommandCentreData,
  ComparisonData,
  DecisionRequest,
  DecisionResponse,
  IssueDetail,
  IssueSummary,
  ReplayEvent,
  ReplayRun,
  StreamEvent,
  StreamEventKind,
  WeeklyReport,
} from "../types";

/**
 * The frozen dashboard data layer from docs/INTERFACES.md.
 *
 * `getReplayEvents` and `submitDecision` are additive optional members: the
 * frozen interface names the REST endpoint for replay events and a POST for
 * decisions but no method to reach them, so Q6 adds them without changing the
 * required surface.
 */
export interface DashboardDataSource {
  getCommandCentre(): Promise<CommandCentreData>;
  getCases(query?: CaseQuery): Promise<CaseListPage>;
  getCase(id: string): Promise<CaseDetail>;
  getIssues(): Promise<IssueSummary[]>;
  getIssue(id: string): Promise<IssueDetail>;
  getComparison(): Promise<ComparisonData>;
  getWeeklyReport(weekStart?: string): Promise<WeeklyReport>;
  getReplayRuns(): Promise<ReplayRun[]>;
  subscribe?(onEvent: (event: StreamEvent) => void): () => void;
  getReplayEvents?(runId: string): Promise<ReplayEvent[]>;
}

export interface DecisionClient {
  submitDecision(caseId: string, request: DecisionRequest): Promise<DecisionResponse>;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export class NotFoundError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NotFoundError";
  }
}

export class ReadOnlyError extends Error {
  constructor(message = "This mode shows recorded decisions and cannot write.") {
    super(message);
    this.name = "ReadOnlyError";
  }
}

const STREAM_EVENTS: readonly StreamEventKind[] = ["heartbeat", "case_status", "trace", "issue", "run"];

export interface LiveDataSourceOptions {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  eventSourceFactory?: (url: string) => EventSource;
}

function buildUrl(baseUrl: string, path: string): string {
  return `${baseUrl.replace(/\/+$/, "")}${path}`;
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = "";
    try {
      detail = await response.text();
    } catch {
      detail = "";
    }
    const suffix = detail ? `: ${detail.slice(0, 200)}` : "";
    throw new ApiError(`Request failed with ${response.status}${suffix}`, response.status);
  }
  return (await response.json()) as T;
}

/** Live mode: REST reads, SSE stream and decision writes to Q7's API. */
export class LiveDataSource implements DashboardDataSource, DecisionClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;
  private readonly eventSourceFactory: ((url: string) => EventSource) | null;

  constructor(options: LiveDataSourceOptions = {}) {
    this.baseUrl = options.baseUrl ?? "/api";
    this.fetchImpl = options.fetchImpl ?? ((...args) => fetch(...args));
    this.eventSourceFactory =
      options.eventSourceFactory ??
      (typeof EventSource === "undefined" ? null : (url) => new EventSource(url));
  }

  private async get<T>(path: string): Promise<T> {
    let response: Response;
    try {
      response = await this.fetchImpl(buildUrl(this.baseUrl, path), {
        headers: { accept: "application/json" },
      });
    } catch (error) {
      throw new ApiError(`Cannot reach the API at ${this.baseUrl}: ${String(error)}`);
    }
    return readJson<T>(response);
  }

  async getCommandCentre(): Promise<CommandCentreData> {
    return this.get<CommandCentreData>("/kpis?window=30d");
  }

  async getCases(query: CaseQuery = {}): Promise<CaseListPage> {
    const params = new URLSearchParams();
    if (query.status) params.set("status", query.status);
    if (query.group) params.set("group", query.group);
    if (query.safety !== undefined) params.set("safety", String(query.safety));
    if (query.q) params.set("q", query.q);
    params.set("limit", String(query.limit ?? 50));
    params.set("offset", String(query.offset ?? 0));
    return this.get<CaseListPage>(`/cases?${params.toString()}`);
  }

  async getCase(id: string): Promise<CaseDetail> {
    return this.get<CaseDetail>(`/cases/${encodeURIComponent(id)}`);
  }

  async getIssues(): Promise<IssueSummary[]> {
    const page = await this.get<{ items: IssueSummary[] }>("/issues");
    return page.items;
  }

  async getIssue(id: string): Promise<IssueDetail> {
    return this.get<IssueDetail>(`/issues/${encodeURIComponent(id)}`);
  }

  async getComparison(): Promise<ComparisonData> {
    return this.get<ComparisonData>("/comparison");
  }

  async getWeeklyReport(weekStart?: string): Promise<WeeklyReport> {
    const suffix = weekStart ? `?week_start=${encodeURIComponent(weekStart)}` : "";
    return this.get<WeeklyReport>(`/reports/weekly${suffix}`);
  }

  async getReplayRuns(): Promise<ReplayRun[]> {
    const page = await this.get<{ items: ReplayRun[] }>("/replay/runs");
    return page.items;
  }

  async getReplayEvents(runId: string): Promise<ReplayEvent[]> {
    const page = await this.get<{ items: ReplayEvent[] }>(
      `/replay/runs/${encodeURIComponent(runId)}/events?after=0`,
    );
    return page.items;
  }

  async submitDecision(caseId: string, request: DecisionRequest): Promise<DecisionResponse> {
    let response: Response;
    try {
      response = await this.fetchImpl(
        buildUrl(this.baseUrl, `/cases/${encodeURIComponent(caseId)}/decision`),
        {
          method: "POST",
          headers: { "content-type": "application/json", accept: "application/json" },
          body: JSON.stringify(request),
        },
      );
    } catch (error) {
      throw new ApiError(`Cannot reach the API at ${this.baseUrl}: ${String(error)}`);
    }
    return readJson<DecisionResponse>(response);
  }

  subscribe(onEvent: (event: StreamEvent) => void): () => void {
    if (!this.eventSourceFactory) {
      return () => undefined;
    }
    const source = this.eventSourceFactory(buildUrl(this.baseUrl, "/events"));
    const emit = (kind: StreamEventKind) => (message: MessageEvent<string>) => {
      let data: Record<string, unknown> = {};
      try {
        const parsed: unknown = JSON.parse(message.data);
        if (typeof parsed === "object" && parsed !== null) {
          data = parsed as Record<string, unknown>;
        }
      } catch {
        data = { raw: message.data };
      }
      const at = typeof data["at"] === "string" ? data["at"] : new Date().toISOString();
      onEvent({
        ...(message.lastEventId ? { id: message.lastEventId } : {}),
        kind,
        at,
        data,
      });
    };

    const listeners = STREAM_EVENTS.map((kind) => {
      const listener = emit(kind) as EventListener;
      source.addEventListener(kind, listener);
      return { kind, listener };
    });

    source.addEventListener("open", () => {
      onEvent({ kind: "connection", at: new Date().toISOString(), data: { status: "open" } });
    });
    source.addEventListener("error", () => {
      onEvent({ kind: "connection", at: new Date().toISOString(), data: { status: "error" } });
    });

    return () => {
      for (const { kind, listener } of listeners) {
        source.removeEventListener(kind, listener);
      }
      source.close();
    };
  }
}
