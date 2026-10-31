# Field Quality Agents: project plan and frozen method

> **Status: FROZEN at commit 1.** Sections 1–11 are the method. A change needs the captain; a deviation goes to `reports/DEVIATIONS.md` with the reason.

## 1. What this project is

**Plain question (the dashboard headline):** *What happens when a returns pipeline becomes agentic: same process, agents doing the legwork between the steps, engineers approving?*

A supplier of electrical and electronic parts receives far more returned parts and complaint reports than its labs and engineers can analyse properly. Many parts get a standard test, find nothing ("no trouble found"), and go back without a root cause. The cost is money (warranty charges accepted without evidence), late warnings (fleet-wide problems seen late), and audit pressure. Today's pipeline is linear: register, sort, standard test, close, and people push each case from step to step.

This project builds **both pipelines on the same real data** and shows them side by side on a dashboard:
- **Before:** the linear, rule-based pipeline. A fixed sequence with keyword rules.
- **After:** an agentic version. A supervisor routes each case to agents (intake, analysis, issue, report) that use tools, gather evidence, draft documents and ask an engineer at defined checkpoints. **Agents never close a case, accept a charge or skip a human approval.**

**Real data:** public NHTSA vehicle owner complaints (as incoming reports), recalls and ODI investigations (as the knowledge base and ground truth). These are US vehicle data standing in for a supplier's return reports.

Independent portfolio project. It must make sense to someone who has never heard of any particular employer.

## 2. Rules (lighter than usual, but these hold)

1. **No employer or person names** anywhere, including commit messages. `make scan-forbidden` must pass (hashed list in `config/forbidden.sha256`).
2. **No secrets in git.** The model key is read only from the file named by `FQA_ENV_FILE` (default `~/.config/field-quality-agents/upstream.env`). It is never printed or logged.
3. **No private data.** Location and identity columns are dropped from NHTSA files. A narrative matching the PII screen (§5) is dropped.
4. **Numbers on the dashboard and in the README come only from committed files under `results/`.**
5. **Scoring is deterministic** (§7). No model grades a model.
6. **Real model calls only in Q0's one probe, Q9 (the main run) and Q14 (the final live test).** Tests use fakes or recordings and make no network calls.
7. **Never push, never add a remote, never publish.** The captain publishes.
8. Python 3.12 + `uv` + Ruff + pytest for the backend. TypeScript + Vite for the dashboard. MIT licence.

## 3. Architecture

```
NHTSA files ──► data/ (DuckDB + committed derived parquet)
                   │
     ┌─────────────┴──────────────┐
     ▼                            ▼
BEFORE: linear pipeline       AFTER: agentic desk (LangGraph)
register → keyword sort →     supervisor ──► intake agent   (dedupe, completeness, info request draft)
standard test → close           │  ├──────► analysis agent (tools: similar cases, recalls, investigations,
                                │  │                        component + clue extraction with quotes, rulebook)
                                │  ├──────► issue agent    (fleet clusters, spike stats, linked recalls,
                                │  │                        8D D1–D4 draft, decision memo)
                                │  └──────► report agent   (weekly quality report)
                                └── human checkpoints (approve / override / ask), budgets, full trace
     │                            │
     └────────────► results/ ◄────┘   (same cases, same metrics)
                       │
              FastAPI backend ──► React dashboard (live mode + replay mode + static portfolio export)
              MCP server ──► the same tools, usable from any MCP client
```

- **Model:** DeepSeek V4.1 Flash through the captain's OpenCode Go key, on the OpenAI-compatible endpoint, with tool calling. Temperature 0; output allowance at least 1,024 tokens.
- **Record/replay:**
  - every live response is stored under `recordings/`, keyed by `sha256(model + prompt version + canonical messages + tools)`;
  - replay mode never touches the network;
  - `make all` rebuilds `results/` and the dashboard data from recordings.
- **Tools** are plain Python functions with typed inputs and outputs. The agents call them. `fqa mcp` exposes the same functions over MCP.
- **Budgets per case:** at most 12 agent steps and 40k tokens. A case that hits a budget goes to a human, and the reason is recorded.

## 4. The agentic desk in detail

- **Supervisor:** reads the case state and picks the next agent or a human checkpoint. It follows a fixed routing policy where one applies (safety → human first) and decides with the model otherwise. Every decision records its reason.
- **Intake agent:**
  - normalises the report;
  - finds duplicates (same make, model and year, similar text, close dates);
  - checks completeness (component, symptom, conditions, mileage, date);
  - drafts a short information request when something important is missing.
- **Analysis agent.** Its tools:
  - `similar_cases` (BM25 full-text search in DuckDB plus filters);
  - `recalls_for` and `investigations_for` (make, model, year, component);
  - `extract_clues` (component group, symptoms, conditions, fault codes, each with a verbatim quote);
  - `verify_quotes`;
  - `rulebook` (condition → targeted test).

  It proposes:
  - **standard test**;
  - **targeted load test**, with its conditions and reasons;
  - **safety priority**;
  - **evidence pack** for a warranty dispute (similar cases, linked recalls, quotes).
- **Issue agent (fleet level):**
  - Runs after each simulated day over all cases so far. It calls `cluster_stats`: weekly counts per make + model + model year + component group, with a Poisson 99.9% spike rule (count ≥ 3, trailing 26-week mean floored at 0.5).
  - Opens an **issue** when a spike holds up after reading the cases.
  - Links matching recalls and investigations.
  - Drafts **8D D1–D4** (team roles as placeholders, problem description, containment proposal, root-cause hypotheses) and a one-page **decision memo**. Every statement cites case ids or recall/investigation ids.
- **Report agent:** a weekly quality report (volumes, decisions, open issues, KPIs), every number taken from the run's own tables.
- **Human checkpoints:**
  - Every test decision, every opened issue, every 8D draft and memo, and every case flagged safety-relevant or over budget.
  - **In the batch run**, a deterministic **simulated engineer** acts on these. It approves when quotes verify and no hard rule is broken, and sends the case back once otherwise. It is labelled "simulated" everywhere.
  - **In live mode**, the dashboard's approve/override buttons are the human.
- **Hard rules (code, not model):**
  - safety-relevant cases always reach a human first;
  - a clue whose quote fails verification is dropped;
  - no automatic close, scrap, return or charge acceptance exists;
  - every action is in the trace.

## 5. Data (all public, NHTSA)

- **Sources:** `https://static.nhtsa.gov/odi/ffdd/`:
  - complaints (`cmpl/COMPLAINTS_RECEIVED_2020-2024.zip`, `cmpl/COMPLAINTS_RECEIVED_2025-2026.zip`, layout `cmpl/CMPL.txt`);
  - recalls (`rcl/FLAT_RCL_POST_2010.zip`, layout `rcl/RCL.txt`);
  - investigations (`inv/FLAT_INV.zip`, layout `inv/INV.txt`);
  - manufacturer communications if Q1 finds the current file (layout `tsbs/TSBS.txt`; optional).
- **Licence:** Q1 confirms the US government work / public domain statement and quotes it in `THIRD_PARTY.md`.
- **Source of truth:** NHTSA rebuilds the files often. Q1 records each download's sha256 and date, and the committed derived files are the source of truth.
- **Selection:**
  - electrical/electronic component groups (8–12, built by Q1 from component-description prefixes, written to `data/groups.toml`);
  - complaints whose component rows all map to one group;
  - narrative of at least 80 characters;
  - PII screen (VIN, e-mail, phone, street address patterns → drop);
  - location and identity columns dropped.
- **Sets:**
  - **knowledge base:** complaints 2020–2024, plus all recalls and investigations;
  - **replay set** (the cases both pipelines process): 600 complaints received in 2025, seed 20261031, stratified by group, at least 120 safety-relevant, ordered by received date so a run plays like incoming days;
  - **fleet series:** weekly counts for all mapped complaints 2020 to the snapshot (counts only);
  - **final live test set (Q14):** the most recent 4 complete weeks of complaints in the snapshot, 150 cases, never used before Q14.

## 6. Dashboard

React + Vite + TypeScript. Charts with Apache ECharts. Light and dark. Works at 360 px.

| Page | Contents |
|---|---|
| **Command centre** | KPI tiles (cases in, prepared without human edits, human touches per case, time to decision, open issues, cost per case, NTF-without-evidence share), a live feed of agent actions, a before/after mini comparison |
| **Case board** | Columns: new, intake, analysis, needs engineer, decided, issue-linked. **Case detail:** narrative with highlighted quotes, the agent trace (step, agent, tool call, result, reason), the proposal, approve/override/ask, similar cases, linked recalls |
| **Issue room** | Cluster chart over time with the spike rule, the linked recalls and investigations timeline, 8D D1–D4 draft, decision memo, citations that open the case or recall |
| **Before vs after** | The same replay set through both pipelines: the §7 metrics side by side with CIs, plus examples where the agent found what the linear pipeline missed, and the reverse |
| **Replay** | Plays a recorded run day by day: cases arriving, agents acting, humans approving |
| **Weekly report** | The report agent's output |

**Modes:**
- **live:** FastAPI with SSE, real buttons;
- **replay:** from recordings, no model calls;
- **static portfolio export:** `dist/field-quality-agents/`, offline, reading bundled JSON.

`DESIGN.md` (from Q0) fixes the visual system: a calm, data-dense operations look.

## 7. Metrics (deterministic; both pipelines unless noted)

- **Component group:** macro-F1 against NHTSA coding, `unclear` counted as wrong (primary), with a bootstrap CI (2,000 resamples), plus coverage.
- **Safety:** recall and precision against crash/fire/injury/death fields, with Wilson CI.
- **Evidence (agentic):** quote-grounding rate, and citation validity (every cited case, recall and investigation id exists, and every quoted span is found in that source).
- **Test decision:** share routed to a targeted load test, and how many of those carry a condition with a verified quote. Reported as behaviour; there is no ground truth for the right test.
- **Issue detection:**
  - an opened issue counts as early when an NHTSA investigation or recall with the same make + model + model year + group follows within 365 days;
  - reported: precision, median lead time, and the same share for random weeks of the same series (base rate);
  - the base-rate comparison is the headline.
- **Recall linking:** the share of linked recalls matching make, model, year and group.
- **Workload:** human touches per case, the share decided without edits by the simulated engineer, steps per case, cost per 1,000 cases, latency p50/p95, and budget hits.
- **Baselines:** the linear pipeline (keyword rules). TF-IDF + logistic regression for the component group as a second reference.

## 8. Reproducibility

- `make all` (replay mode, no key, no network) rebuilds `results/` and the dashboard data byte-identically, checked by `results/MANIFEST.sha256`.
- Search scores are rounded to 4 decimals, with ties broken by id.

## 9. Spending

- There is no spending cap. Every call's cost is recorded (gateway list cost when present, else tokens × `config/prices.toml`) and reported.
- **Expected:** Q9 about USD 1–4 (600 cases × a few calls each, plus issue and report runs), Q14 under USD 1.
- **Stop at once** on HTTP 403, an abuse/policy message or an account warning.

## 10. Stop rules (write `reports/STOP.md` and stop)

1. The NHTSA licence turns out to be restrictive.
2. A committed file contains suspected personal data.
3. The model endpoint returns 403, an abuse/policy message or an account warning.
4. A key appears in a file, log or recording.
5. Tool calling with DeepSeek V4.1 Flash through OpenCode Go cannot be made to work (Q0 probe). The agents need tools.

## 11. Definition of done

- `make release-check` is green: Ruff, mypy on `src/`, pytest offline, the dashboard type-check and build, `scan-forbidden`, secrets scan, the facts check.
- `make all` is byte-identical twice.
- `results/` holds both pipelines' metrics, issues, 8D drafts, memos and the weekly report. `results/final-live/` holds the Q14 run.
- The dashboard runs live (`make serve`) and as a static export. Playwright screenshots exist at 360 px and 1280 px, light and dark.
- `README.md`, `METHOD.md`, `THIRD_PARTY.md`, `LICENSE` (MIT), `CHANGELOG.md` and `project-facts.yml` are complete.
- Local tag `v1.0.0`. No remote, nothing pushed.
