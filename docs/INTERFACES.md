# Interfaces: modules, API and dashboard data

This document freezes the boundaries that let Q1-Q7 work in parallel against
fixtures. The domain objects live in
`src/field_quality_agents/contracts.py`; this file names the functions and
transport shapes around them. A signature change is a contract change and needs
a captain decision (PLAN §1-11 are frozen).

All timestamps are ISO 8601 UTC (`2026-10-31T11:51:00Z`); dates are
`YYYY-MM-DD`. JSON uses `snake_case`. Ids are opaque strings; never parse them.
Every list endpoint is deterministic: sort by the documented key, then by id.

## Shared invariants

- `Case.status` is one of `new`, `intake`, `analysis`, `needs_engineer`,
  `decided`, `issue_linked`. The UI groups `intake` + `analysis` as "in agent".
- A case reaches `decided` only with a matching `HumanDecision`.
- A quote is evidence only when `Citation.verified` is true and
  `verify_quotes` found the span in the cited source.
- A lane that cannot build its real dependency uses a fake implementing the
  signature below, never an ad-hoc shape.
- No module opens the key file except Q4's credential loader. No module prints
  or serialises credentials.

## Q1: data (`src/field_quality_agents/data/`)

Owned files: `fetch.py`, `build.py`, `groups.py`, `pii.py`, `schema.py`,
`stats.py`, `scripts/fetch_nhtsa.py`, `tests/data/`.

```python
# data/fetch.py
@dataclass(frozen=True)
class DownloadedFile:
    name: str
    path: Path
    sha256: str
    size_bytes: int
    last_modified: str | None
    downloaded_at: datetime

def fetch_nhtsa(dest: Path, *, force: bool = False) -> list[DownloadedFile]: ...

# data/groups.py
@dataclass(frozen=True)
class Group:
    id: str
    description: str
    prefixes: tuple[str, ...]

def load_groups(path: Path = Path("data/groups.toml")) -> dict[str, Group]: ...
def map_group(component: str, groups: Mapping[str, Group]) -> str | None: ...

# data/pii.py
def contains_pii(text: str) -> bool: ...
def screen_counts(narratives: Iterable[str]) -> dict[str, int]: ...

# data/build.py
@dataclass(frozen=True)
class DataBuild:
    snapshot: dict[str, object]
    outputs: tuple[Path, ...]
    stats: dict[str, object]

def build_all(raw_dir: Path = Path("data/raw"), out_dir: Path = Path("data")) -> DataBuild: ...
```

Committed outputs (Q1 owns the exact schema): `data/kb_complaints.parquet`,
`data/recalls.parquet`, `data/investigations.parquet`,
`data/replay_2025.parquet`, `data/final_live.parquet`,
`data/fleet_weekly.parquet`, `data/events.parquet`, plus
`data/SNAPSHOT.json`, `data/groups.toml`, `data/STATS.md`.

Required columns for the tool layer:

- complaints: `id`, `received_at`, `make`, `model`, `year`, `component`,
  `group`, `narrative`, `safety_relevant`, `mileage`
- recalls: `id`, `make`, `model`, `year`, `component`, `group`, `summary`,
  `open_date`
- investigations: `id`, `make`, `model`, `year`, `component`, `group`,
  `summary`, `open_date`
- events: `make`, `model`, `year`, `group`, `event_type`
  (`recall` | `investigation`), `event_date`, `source_id`
- fleet_weekly: `week_start`, `make`, `model`, `year`, `group`, `count`

## Q2: tools and MCP (`src/field_quality_agents/tools/`, `mcp_server.py`)

Owned files: `tools/*.py`, `mcp_server.py`, `tests/tools/`.

```python
@dataclass(frozen=True)
class CaseFilters:
    make: str | None = None
    model: str | None = None
    year: int | None = None
    group: str | None = None
    safety_relevant: bool | None = None

@dataclass(frozen=True)
class SimilarCase:
    id: str
    score: float          # rounded to 4 decimals
    make: str
    model: str
    year: int
    group: str
    excerpt: str

@dataclass(frozen=True)
class ClusterStats:
    make: str
    model: str
    year: int
    group: str
    until_date: date
    weekly: tuple[WeekCount, ...]
    trailing_mean: float
    threshold: float       # Poisson 99.9% rule, mean floored at 0.5
    observed: int
    spike: bool

@dataclass(frozen=True)
class QuoteVerification:
    quote: str
    verified: bool

def similar_cases(text: str, filters: CaseFilters | None = None, k: int = 10) -> list[SimilarCase]: ...
def recalls_for(make: str, model: str, year: int, group: str) -> list[dict[str, object]]: ...
def investigations_for(make: str, model: str, year: int, group: str) -> list[dict[str, object]]: ...
def cluster_stats(make: str, model: str, year: int, group: str, until_date: date) -> ClusterStats: ...
def verify_quotes(text: str, quotes: Sequence[Clue]) -> list[QuoteVerification]: ...
def rulebook(conditions: Sequence[str]) -> list[dict[str, object]]: ...
def case_lookup(id: str) -> Case | None: ...
```

`similar_cases` scores are rounded to 4 decimals, ties broken by id.
`verify_quotes` checks each quote as a verbatim substring after whitespace
normalisation; it never returns a fuzzy match.

The MCP server exposes exactly these seven names with the same parameter names
and JSON-compatible results. `fqa mcp` runs it over stdio. Tests use a fixture
DuckDB under `tests/fixtures/`, not the real committed data.

## Q3: baseline and metrics (`baseline/`, `metrics/`)

```python
# baseline/pipeline.py
@dataclass(frozen=True)
class BaselineDecision:
    case_id: str
    group: str
    safety_relevant: bool
    route: Literal["priority", "standard_test"]
    closed_no_trouble_found: bool
    keywords: tuple[str, ...]

def run_linear(cases: Sequence[Case], keywords: KeywordRules) -> list[BaselineDecision]: ...
def run_tfidf_logreg(train: Sequence[Case], test: Sequence[Case]) -> list[str]: ...

# metrics/__init__.py
def macro_f1(y_true: Sequence[str], y_pred: Sequence[str]) -> MetricEstimate: ...
def safety_scores(y_true: Sequence[bool], y_pred: Sequence[bool]) -> tuple[MetricEstimate, MetricEstimate]: ...
def quote_grounding(checks: Sequence[QuoteVerification]) -> MetricEstimate: ...
def citation_validity(citations: Sequence[Citation], sources: SourceIndex) -> MetricEstimate: ...
def targeted_test_share(proposals: Sequence[Proposal]) -> MetricEstimate: ...
def issue_detection(issues: Sequence[Issue], truth: Sequence[Event], *, cases: Sequence[Case]) -> dict[str, float]: ...
def workload(runs: Sequence[CaseRun]) -> dict[str, float]: ...
def compare(before: Metrics, after: Metrics) -> Comparison: ...
```

`metrics/` functions are pure: no I/O, no model calls, no randomness except a
seeded bootstrap passed as `rng`. Every estimate includes its CI where PLAN §7
requires one. Q3 commits `config/keywords.toml` **before** any model result
exists.

## Q4: model client and record/replay (`llm/`)

```python
@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, object]

@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: float | None = None
    list_cost_usd: float | None = None
    allowance_usd: float | None = None

@dataclass(frozen=True)
class ChatResponse:
    text: str
    tool_calls: tuple[ToolCall, ...]
    finish_reason: str
    usage: Usage
    raw: dict[str, object]
    latency_ms: int

class OpenAIChatClient:
    def __init__(self, *, transport: httpx.BaseTransport | None = None,
                 clock: Callable[[], float] = time.monotonic) -> None: ...
    def chat(self, *, messages: Sequence[dict[str, object]],
             tools: Sequence[dict[str, object]] = (),
             tool_choice: str = "auto",
             temperature: float = 0.0,
             max_tokens: int = 1024) -> ChatResponse: ...

class RecordReplayStore:
    def __init__(self, root: Path, mode: Literal["record", "replay"]) -> None: ...
    def key(self, *, model: str, prompt_version: str,
            messages: Sequence[dict[str, object]],
            tools: Sequence[dict[str, object]]) -> str: ...
    def get(self, key: str) -> ChatResponse: ...   # raises ReplayMiss
    def put(self, key: str, response: ChatResponse) -> None: ...

class LangChainChatModel(BaseChatModel):
    def bind_tools(self, tools: Sequence[object], **kwargs: object) -> LangChainChatModel: ...
```

Errors: `TransportError`, `RateLimitError(retry_after: float | None)`,
`PolicyStopError` (writes `reports/STOP.md`), `BadAnswerError`,
`ReplayMissError`. Q4 owns `config/prices.toml`, `config/budget.toml`.
Pacing: 2 concurrent, 30 requests/minute. Credentials only from `FQA_ENV_FILE`
then `.env`; the loader never exposes the value in `repr` or logs.

## Q5: agents (`agents/`, `prompts/`)

```python
# agents/state.py
class DeskState(TypedDict, total=False):
    case: Case
    extraction: Extraction
    proposal: Proposal
    trace: list[TraceStep]
    steps: int
    tokens: int
    safety_relevant: bool
    pending_decision: HumanDecision | None
    decision: HumanDecision | None
    issue_ids: list[str]

# agents/graph.py
def build_desk_graph(*, tools: ToolRegistry, model: LangChainChatModel,
                     checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph: ...
def run_case(case: Case, graph: CompiledStateGraph) -> CaseRun: ...
def run_day(cases: Sequence[Case], until: date, graph: CompiledStateGraph) -> list[Issue]: ...

# agents/simulated_engineer.py
def decide(state: DeskState) -> HumanDecision: ...
```

`ToolRegistry` is Q2's typed function set, injected rather than imported at
module import time so tests use fakes. Prompts are versioned files
`prompts/<agent>/p1.md`; `load_prompt(agent, version)` returns the text and
records the version in the trace/manifest.

Budgets: 12 steps and 40,000 tokens per case. Exceeding either routes to
`needs_engineer` and records the reason. Hard rules are code-level guards, not
prompt instructions: safety first, drop unverified quotes, no close/scrap/
return/charge action exists.

## Q6: dashboard (`web/`)

Owned files: `web/src/`, `web/public/`, `tests/web/`.

```ts
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
}
```

Two implementations: `LiveDataSource` (fetch + SSE to Q7) and
`StaticDataSource` (bundled JSON under `data/`, no network). The page must
render identically from either shape. Q6 builds all PLAN §6 pages; Q10 only
polishes and wires real results.

## Q7: backend API (`src/field_quality_agents/api/`)

```python
def create_app(*, store: ResultStore, graph: CompiledStateGraph | None = None,
               mode: Literal["live", "replay", "static"] = "replay") -> FastAPI: ...
```

### REST endpoints

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/api/health` | - | `{"status":"ok","mode":"replay","version":"0.1.0"}` |
| GET | `/api/kpis?window=30d` | - | `CommandCentreData` |
| GET | `/api/cases?status=&group=&safety=&q=&limit=50&offset=0` | - | `CaseListPage` |
| GET | `/api/cases/{case_id}` | - | `CaseDetail` |
| GET | `/api/cases/{case_id}/trace` | - | `{"case_id":...,"steps":[TraceStep...]}` |
| POST | `/api/cases/{case_id}/decision` | `DecisionRequest` | `DecisionResponse` |
| GET | `/api/issues?status=` | - | `{"items":[IssueSummary...]}` |
| GET | `/api/issues/{issue_id}` | - | `IssueDetail` |
| GET | `/api/comparison` | - | `ComparisonData` |
| GET | `/api/reports/weekly?week_start=` | - | `WeeklyReport` |
| GET | `/api/replay/runs` | - | `{"items":[ReplayRun...]}` |
| GET | `/api/replay/runs/{run_id}/events?after=0` | - | `{"items":[ReplayEvent...]}` |
| GET | `/api/events` | - | `text/event-stream` (SSE) |
| GET | `/` and `/{path:path}` | - | `web/dist` static files, SPA fallback |

`DecisionRequest`:

```json
{
  "action": "approve | override | ask | request_info",
  "rationale": "short reason shown in the trace",
  "edited_proposal": null
}
```

`DecisionResponse`:

```json
{"case": "Case", "trace": ["TraceStep"], "pending": null, "issue_ids": []}
```

Approve/override resume the LangGraph thread with `Command(resume=...)` and
return the updated case state. In replay/static mode the endpoint returns 409
and the UI shows the recorded decision read-only. `ask` and `request_info`
append a human step and leave the case at `needs_engineer`.

### SSE contract

Each event has an `event:` name and a JSON `data:` object:

| Event | Data |
|---|---|
| `heartbeat` | `{"at": "..."}` every 15 s |
| `case_status` | `{"case_id": "...", "status": "analysis"}` |
| `trace` | `{"case_id": "...", "step": TraceStep}` |
| `issue` | `{"issue_id": "...", "status": "open"}` |
| `run` | `{"run_id": "...", "status": "complete"}` |

The client reconnects with `Last-Event-ID`; the server retains the current run's
events in order.

## Dashboard JSON shapes

These are the transport shapes for Q6 fixtures and Q10's static export. They
are `contracts.py` objects plus the small wrappers below; field names match the
Python models exactly.

```ts
interface CaseListItem {
  id: string; received_at: string; make: string; model: string; year: number;
  component: string; group: string | null; status: CaseStatus;
  safety_relevant: boolean; evidence_count: number; human_touches: number;
}

interface CommandCentreData {
  window: string;
  kpis: Kpi[];                 // id, label, value, unit, context, delta?, tone?, series?
  live_feed: StreamEvent[];    // most recent first, capped at 50
  comparison: ComparisonSummary;
  final_live?: FinalLiveData | null;  // Q14 panel; absent until results/final-live/
}

// Additive at Q14: the final live test beside the Q9 replay run.
interface FinalLiveData {
  run_id: string; set_name: string;
  window_start: string; window_end: string;
  spend_usd: number; steps: number; budget_hits: number;
  final: { cases: number; before: Metrics; after: Metrics };
  q9: { cases: number; before: Metrics; after: Metrics };
  q9_run_id: string;
}

interface Kpi {
  id: string; label: string; value: number | string; unit?: string;
  context: string; delta?: number; tone?: "neutral"|"good"|"watch"|"issue";
  series?: number[];           // optional sparkline, oldest first
}

interface CaseListPage { items: CaseListItem[]; total: number; limit: number; offset: number; }

interface CaseDetail {
  case: Case;
  extraction: Extraction | null;
  proposal: Proposal | null;
  trace: TraceStep[];
  decision: HumanDecision | null;
  similar_cases: SimilarCase[];
  recalls: RecallRef[];
  investigations: InvestigationRef[];
}

interface RecallRef { id: string; summary: string; open_date: string; match: boolean; }
interface InvestigationRef { id: string; summary: string; open_date: string; match: boolean; }

interface IssueSummary {
  id: string; title: string; status: IssueStatus; opened_at: string;
  make: string; model: string; year: number; group: string;
  observed: number; threshold: number; spike_ratio: number;
  linked_case_count: number;
}

interface IssueDetail extends IssueSummary {
  weekly_counts: WeekCount[];
  linked_case_ids: string[];
  linked_recall_ids: string[];
  linked_investigation_ids: string[];
  eight_d: EightD | null;
  memo: DecisionMemo | null;
}

interface ComparisonSummary {
  headline: { id: string; label: string; before: number; after: number; unit: string }[];
  examples: { case_id: string; before: string; after: string; note: string }[];
}

interface ComparisonData {
  before: Metrics; after: Metrics;
  summary: ComparisonSummary;
  rows: { metric: string; label: string; before: MetricEstimate | number | null;
          after: MetricEstimate | number | null; note?: string }[];
}

interface ReplayRun { run_id: string; set_name: string; started_at: string;
  status: "running"|"complete"|"failed"; case_count: number; }

interface ReplayEvent { seq: number; at: string; kind: "case"|"trace"|"decision"|"issue"|"report";
  case_id?: string; issue_id?: string; payload: Record<string, unknown>; }
```

`WeeklyReport` is the contract object. `Case` is the contract object. Static
export files (Q10):

```text
dist/field-quality-agents/
  index.html
  assets/*                     # hashed JS/CSS
  data/manifest.json           # run id, generated_at, file list, counts
  data/command_centre.json
  data/cases.json              # CaseListItem[]
  data/cases/<case_id>.json    # CaseDetail
  data/issues.json             # IssueDetail[]
  data/comparison.json
  data/weekly_report.json
  data/replay.json             # ReplayRun + events
```

The export is read-only and offline: no fetch outside `data/`, no SSE.

## Fixtures and fakes

- `tests/fixtures/` holds small JSON documents in these shapes, never the real
  data.
- Q7's tests use a fake graph and a fixture result store.
- Q6's `npm run test` uses fixtures; Playwright specs (Q6/Q8) may run against
  `make serve` with fixture recordings.
- Q2's MCP harness uses a fixture DuckDB and asserts every tool is listed and
  callable.
