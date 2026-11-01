# Method

This is the method behind the project, in plain words. The frozen version is
`PLAN.md` §3–§8; this document explains what those sections build and why, with
pointers to the code that does it. Where the project deviates, the reason is in
`reports/RUN.md`.

## 1. The experiment

Two pipelines, one data set, one set of metrics:

- **Before:** a linear pipeline that a small team could write today. Register
  the report, sort it with keyword rules, run the standard test, close. It is
  deterministic and it uses no model.
- **After:** an agentic desk. A supervisor routes each report to agents that
  call tools, collect evidence, draft documents and stop at human checkpoints.
  It uses one model and a fixed budget per case.

Both run on the same reports, so the comparison is about the way of working,
not about a different input. The dashboard shows them side by side.

## 2. Architecture

```
NHTSA flat files
      │  fetch, screen, de-identify, map components
      ▼
data/  committed parquet + DuckDB at run time
      │
      ├──────────────────────────────┐
      ▼                              ▼
Before: linear pipeline        After: agentic desk (LangGraph)
register → keyword sort →      supervisor → intake → safety / analysis
standard test → close                        → human gate → finish
      │                              │         issue agent (daily)
      │                              │         report agent (weekly)
      └──────────────┬───────────────┘
                     ▼
results/  cases, traces, proposals, decisions, issues, 8D, memos,
          weekly reports, metrics, manifests
                     │
                     ▼
FastAPI backend ──► React dashboard (live, replay, static export)
      └── MCP server ──► the same tools, for any MCP client
```

The code follows that layout: `data/` for the build, `baseline/` for the
before pipeline, `agents/` and `run/` for the desk, `tools/` for the shared
functions, `metrics/` for scoring, `api/` and `web/` for the dashboard, and
`mcp_server.py` for the MCP surface.

**Record and replay.** In record mode every model response is stored under
`recordings/`, keyed by the model, the prompt version, the canonical messages
and the tools offered. Replay mode looks each turn up in that store and never
touches the network. `make all` is a replay: no key, no network, same bytes.

**Budgets.** A case may use a fixed number of agent steps and tokens, read from
`config/budget.toml`. A case that hits either limit goes to a person, and the
reason is written to its trace. The batch run had no budget hits.

## 3. The agentic desk

### Supervisor

The supervisor reads the case state and picks the next step. Where the method
fixes the route, the route is code: a safety flag goes to a human first; an
unfinished intake goes back to intake; a case with no proposal goes to analysis;
a proposal goes to a human; a decision or a budget ends the case. Where the
method leaves a judgement to the model, the model makes it. Every routing choice
is written to the trace with its reason.

### Intake agent

Intake turns a raw report into a structured case: component, symptom,
conditions, mileage and date where they are present. It looks for duplicates
(same vehicle, similar text, close dates), records missing information and
drafts a short information request when something that matters is absent. In
the batch run, only a missing component or symptom blocks the case; a missing
mileage or date is noted and the case continues. That rule came from the live
run, where an over-strict intake stop was sending almost every case to a person.

### Analysis agent

The analysis agent works with tools, not with free text alone:

- `similar_cases` — full-text search over the knowledge base, with filters;
- `recalls_for` and `investigations_for` — the vehicle and component history;
- `extract_clues` — component group, symptoms, conditions and fault codes, each
  with a verbatim quote from the report;
- `verify_quotes` — checks that a quote really appears in the cited source;
- `rulebook` — reported condition to targeted test, from an example rulebook.

It proposes one of: a standard test, a targeted load test with its conditions
and reasons, or a safety priority. It can also assemble an evidence pack for a
warranty dispute: similar cases, linked recalls and verified quotes.

### Issue agent

Once per simulated day the issue agent looks at the fleet rather than one case.
`cluster_stats` counts reports per week for each make, model, model year and
component group, and applies a Poisson spike rule to the trailing series. When a
spike holds up after reading the linked reports, the agent opens an issue. It
links matching recalls and investigations, drafts the first four 8D sections
(D1 team roles as placeholders, D2 problem, D3 containment, D4 root-cause
hypotheses) and writes a one-page decision memo. Every statement in those drafts
cites a case id or a recall/investigation id, and the code checks the citations.

### Report agent

The report agent writes one weekly quality report from the run's own tables:
volumes, decisions, open issues and the workload numbers. It does not recount
the world; it reads what the run wrote.

### Human checkpoints

Every test decision, every opened issue, every 8D draft and memo, and every
safety-relevant or over-budget case stops at a human checkpoint. The graph
suspends there and resumes with a decision: approve, override with an edited
proposal, or ask for more work.

In a **batch run** a deterministic simulated engineer takes that seat. It
approves when all quotes verify and no hard rule is broken, and sends the case
back once otherwise. Every decision says "simulated" and the dashboard labels it
that way. In **live mode** a person at the dashboard is the decision-maker.

### Hard rules, in code

- A safety-relevant report always reaches a person before any test.
- A clue whose quote fails verification is dropped.
- No code path closes a case, scraps a part, returns a part or accepts a charge
  without a human decision.
- Every action and every routing reason is in the trace.

## 4. Data

The project uses public NHTSA flat files: owner complaints, recalls, defect
investigations and (optionally) manufacturer communications. The vehicle world
stands in for a supplier's returns because the reports are real, public,
de-identified and rich enough to contain symptoms, conditions and vehicle
identity. It is a stand-in, not the same business: see the limits in `README.md`.

The build:

1. downloads each source and records its URL, sha256, size, `Last-Modified`
   header and download time in `data/SNAPSHOT.json`;
2. keeps a report only when its component rows map to a single electrical or
   electronic group, its narrative is long enough to analyse, and the narrative
   passes the personal-data screen;
3. drops location and identity columns, and drops a whole narrative when it
   matches a VIN, e-mail, phone or street-address pattern;
4. derives the knowledge base (complaints 2020–2024 plus all recalls and
   investigations), the replay set used for the comparison, a count-only fleet
   series, an event table of recall and investigation dates, and a sealed final
   live set that no run may use before the final test;
5. writes committed parquet, with the counts and drop reasons in
   `data/STATS.md`.

NHTSA rebuilds its files often, so the committed derived parquet files are the
source of truth for reproduction; the snapshot record makes a refresh auditable.
The licence statement is in `THIRD_PARTY.md`.

## 5. Dashboard

One React + TypeScript application with three modes:

- **replay** — reads a recorded run from `results/runs/`; this is what
  `make serve` starts and what a reviewer sees;
- **live** — the same desk on new reports, with SSE for agent actions and real
  approve / override / ask buttons;
- **static export** — a build under `dist/field-quality-agents/` that opens
  offline with bundled JSON.

The pages are the command centre, the case board, case detail, the issue room,
the before/after comparison, the replay player and the weekly report. A case
detail shows the narrative with highlighted quotes, the full trace with tool
calls and reasons, the proposal, similar cases, linked recalls and the decision
controls. The issue room shows the cluster chart with the spike rule, the linked
events, the 8D draft, the memo and clickable citations. The design system is in
`DESIGN.md`; the data shapes and endpoints are in `docs/INTERFACES.md`.

## 6. Metrics

All scoring is deterministic; no model grades a model. Point estimates are
reported with confidence intervals where the metric supports one.

- **Component group.** Macro-F1 against the NHTSA component coding, with
  `unclear` counted as wrong, plus how much of the set got a group at all
  (coverage). The interval is a bootstrap over cases.
- **Safety.** Recall and precision against the NHTSA crash, fire, injury and
  death fields, with Wilson intervals. This is reported as behaviour; the flag
  is not tuned to the replay set.
- **Evidence.** Quote grounding is the share of quotes that are found verbatim
  in the cited source. Citation validity is the share of cited case, recall and
  investigation ids that exist and whose quoted span is found. A failing quote
  is dropped before the proposal is scored.
- **Test decision.** The share of cases routed to a targeted load test, and how
  many of those carry a condition backed by a verified quote. There is no ground
  truth for "the right test", so this is reported as behaviour.
- **Issue detection.** An opened issue is early when an NHTSA investigation or
  recall with the same make, model, model year and component group follows
  within a year. The project reports precision, median lead time, and the same
  share for random weeks of the same series. The base-rate comparison is the
  headline, because a spike rule that fires often will sometimes be right by
  chance.
- **Recall linking.** The share of linked recalls that match on make, model,
  model year and component group.
- **Workload.** Human touches per case, the share decided without edits, steps
  per case, cost per 1,000 cases, latency p50 and p95, and budget hits. The
  linear pipeline is modelled with one human touch and four fixed steps so both
  pipelines feed the same workload function; that model is stated, not hidden.
- **Baselines.** The linear pipeline is the main comparison. A TF-IDF plus
  logistic-regression classifier, trained on the knowledge base, is a second
  reference for the component group only.

## 7. Reproducibility

`make all` checks the committed data, rebuilds the baseline, replays the
recorded run, exports the dashboard data, builds the web app and writes
`results/MANIFEST.sha256`. Run it twice and the manifest is byte-identical.
Search scores are rounded to four decimals with ties broken by id, so ordering
cannot wobble between runs.

The live run is checked separately: its record-mode output is replayed from the
same recordings and every content file is compared with the recorded run. Only
the manifest (mode and run id) and the event feed (run id in report events)
differ, by design. `reports/RUN.md` records that check and the environment it
ran in.

Tests are offline. The pytest configuration blocks sockets, and the browser
tests run against fixture recordings, so `make test` and `make release-check`
never make a model call.

## 8. What the method does not claim

- It does not claim the targeted test was the right test; there is no ground
  truth for that, only behaviour and evidence.
- It does not claim the batch engineer behaves like a person; it is a rule set
  and it approved every proposal.
- It does not claim the vehicle data is a supplier's returns process.
- It does not claim a production deployment: one model, one prompt version, a
  laptop-sized run and public data.
