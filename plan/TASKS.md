# field-quality-agents: task briefs Q0–Q15

Every brief: first read `PLAN.md` §2 and `AGENTS.md`, plus `docs/INTERFACES.md` and `DESIGN.md` once Q0 has written them. Run `make test` and `make scan-forbidden` before committing. Finish with `reports/lanes/<ID>.md`. Never push.

---

## Q0: Foundation, verified notes, design system, model probe (Wave 0)

The repo exists as an empty local git repo at `projects/field-quality-agents` (created by firstmate, no remote).

### Build
1. **Commit 1, `plan: frozen method`.** Copy `PLAN.md` and `AGENTS.md` from `~/fm-plans/field-quality-agents/field-quality-agents/` to the repo root, and `TASKS.md` to `plan/TASKS.md`. Add `CLAUDE.md` containing `@AGENTS.md`.
2. **Verified notes** (sources, versions, dates; no memory):
   - **`docs/NOTES-model.md`:**
     - the OpenCode Go OpenAI-compatible endpoint and model id for DeepSeek V4.1 Flash (`https://opencode.ai/docs/go/`);
     - the tool-calling request and response format;
     - the usage and cost fields;
     - rate-limit behaviour.
     - **One real probe:** one chat call with one tiny tool through the endpoint, using the key from `FQA_ENV_FILE`. It must return a valid tool call. Record the outcome; if tool calling fails, see PLAN §10.5.
   - **`docs/NOTES-langgraph.md`:** the current LangGraph and LangChain versions; the supervisor/agent graph pattern; tool binding to an OpenAI-compatible chat model; human-in-the-loop `interrupt`/resume; the checkpointer.
   - **`docs/NOTES-mcp.md`:** the official MCP Python SDK; serving existing functions as tools over stdio.
   - **`docs/NOTES-duckdb.md`:** DuckDB version; full-text search (BM25) extension; reading tab-delimited NHTSA files; writing parquet.
3. **`DESIGN.md`:**
   - the dashboard's visual system: tokens (light and dark), type scale, spacing, status colours (new / in agent / needs engineer / decided / issue);
   - components: KPI tile, kanban card, trace step, evidence highlight, chart style (ECharts theme);
   - layout: left nav on desktop, bottom nav on phones;
   - a calm, data-dense operations look.
4. **Commit 2, the scaffold:**
   - **Backend:** `pyproject.toml` (uv, Python 3.12; Ruff, mypy, pytest with a socket guard), `src/field_quality_agents/`.
   - **`contracts.py`** (pydantic, frozen after Q0): `Case`, `Clue` (kind, quote), `Extraction`, `Proposal`, `TraceStep`, `HumanDecision`, `Issue`, `EightD`, `DecisionMemo`, `WeeklyReport`, `RunManifest`, `Metrics`.
   - **CLI stubs** (`fqa`): `data`, `baseline`, `run --mode replay|record`, `issues`, `report`, `serve`, `export`, `mcp`.
   - **`web/`:** Vite + React + TypeScript strict, ECharts; `npm` scripts `build`, `typecheck`, `test`.
   - **`Makefile`:** `setup`, `fetch-data`, `data`, `test`, `lint`, `typecheck`, `web-build`, `scan-forbidden`, `scan-secrets`, `facts`, `baseline`, `run-replay`, `run-live` (Q9/Q14 only), `serve`, `export`, `screenshots`, `all`, `release-check`.
   - **Scanners:**
     - `scripts/scan_forbidden.py`:
       - lowercase the text and find tokens with `[a-z0-9][a-z0-9._+-]*`;
       - strip `._+-` at the edges;
       - hash each token, and each part split on `[._+-]+`, with sha256;
       - compare against `config/forbidden.sha256`;
       - check tracked files under 8 MB and the last N commit messages;
       - print file:line and a hash prefix only.
     - `scripts/scan_secrets.py`.
   - **`config/forbidden.sha256`** contains exactly:
     ```
     cfce5f52343e7724c1094803ef0a40354d3aa42ea20482a31e21e1e62bb0b0e7
     3ea71aca1b48bf563154e32f22a39afc4070bc92d7d08ea43b730992a164fa5d
     1137a227a70b670d93dff321e41d904f04d115a3d2c70318310bd1aaba0e46ec
     3d9ba13112739a0d112d800bb3944c93eefdefb34a083c7d851362d76fc27bb7
     e05f05aaf5f3c8caf5a05ad0e9a58cb97de6c36614fe494a1229fd91e0c3f9c9
     50df79aaa0d0b5fb849a6797c8b286681444e5e306b2dba53ddeadf02c1c368d
     9c3125a008064087e6d93acf34289862fd3a625256787183f3b05ed503050809
     ```
   - **`docs/INTERFACES.md`:** module boundaries and signatures for Q1–Q7, the REST API, and the dashboard data shapes, so lanes can work in parallel against fakes and fixtures.
   - `LICENSE` (MIT, Saber Sojudi, 2026) and `.gitignore` (`.env`, `data/raw/`, caches, `node_modules`, `web/dist`).

**Done when:** `make release-check` is green on the scaffold, the probe result is recorded, and lane report `reports/lanes/Q0.md` exists.

---

## Q1: NHTSA data (Wave 1)

**Owns:** `src/field_quality_agents/data/`, `scripts/fetch_nhtsa.py`, `data/` (derived), `tests/data/`, the NHTSA rows in `THIRD_PARTY.md`.

### Build
1. **Licence:** find and quote the NHTSA / data.gov statement. If it's restrictive, follow PLAN §10.
2. **Download** per PLAN §5 to `data/raw/` (gitignored), with sha256, size, `Last-Modified` and download time in `data/SNAPSHOT.json`. Look for the current manufacturer-communications file (optional); note it if absent.
3. **Groups:** from component value counts, build `data/groups.toml` with 8–12 electrical/electronic groups, each with an id, a one-line description and its prefixes. Merge thin groups.
4. **Derive per PLAN §5** into DuckDB and committed parquet (zstd), keeping total committed data under 60 MB:
   - `data/kb_complaints.parquet` (2020–2024, at most 40,000 items stratified by group);
   - `data/recalls.parquet`;
   - `data/investigations.parquet`;
   - `data/replay_2025.parquet` (600 cases);
   - `data/final_live.parquet` (150 cases, the latest 4 complete weeks; sealed until Q14);
   - `data/fleet_weekly.parquet`;
   - `data/events.parquet` (investigation and recall open dates per make + model + year + group, as ground truth).
5. **PII screen:** drop any narrative matching a pattern, and report counts.
6. **`data/STATS.md`:** counts per group, safety rates, PII drops, investigation and recall mapping rates.

**Tests:** fixtures only, covering parsing, column drop, the single-group rule, the PII patterns, seed determinism, and the event join.

**Done when:** the derived files and STATS are committed, `make test` is green, and the lane report exists.

---

## Q2: Tools and MCP server (Wave 1)

**Owns:** `src/field_quality_agents/tools/`, `src/field_quality_agents/mcp_server.py`, `tests/tools/`.

### Build
Typed functions over DuckDB, per `docs/INTERFACES.md`:
- `similar_cases(text, filters, k)`: BM25 search, scores rounded to 4 decimals, ties broken by id;
- `recalls_for(make, model, year, group)`;
- `investigations_for(...)`;
- `cluster_stats(make, model, year, group, until_date)`: the weekly series and the PLAN §4 spike rule;
- `verify_quotes(text, quotes)`;
- `rulebook(conditions)`: `config/rulebook.toml`, an example rulebook mapping condition to targeted test (moisture → humidity/condensation test, cold → low-temperature cycling, heat → high-temperature operation, vibration → vibration test, intermittent → long-run power cycling, after service → check installation first, charging → electrical load test);
- `case_lookup(id)`.

`fqa mcp` serves them over stdio. Tests run against a small fixture DuckDB.

**Done when:** tests are green, an MCP client harness lists and calls each tool, and the lane report exists.

---

## Q3: Linear baseline pipeline and metrics (Wave 1)

**Owns:** `src/field_quality_agents/baseline/`, `src/field_quality_agents/metrics/`, `config/keywords.toml`, `tests/baseline/`, `tests/metrics/`.

### Build
- **The "before" pipeline:**
  - register;
  - keyword component sort (`config/keywords.toml`);
  - keyword safety flag;
  - fixed routing: safety → priority, else standard test;
  - close as "no trouble found" when the standard test is simulated as passing. The simulation always passes, which is the realistic default with no clues.
  - Commit the keyword files in their own commit before any model result exists.
- **TF-IDF + logistic regression** reference for the group.
- **Every PLAN §7 metric** as a pure function with CIs, used identically for both pipelines.

**Done when:** `make baseline` writes `results/baseline/`, metrics are tested on hand-computed fixtures, and the lane report exists.

---

## Q4: Model client and record/replay (Wave 1)

**Owns:** `src/field_quality_agents/llm/`, `config/prices.toml`, `config/budget.toml`, `tests/llm/`.

### Build
- **OpenAI-compatible chat client** (httpx) with tool calling, per `docs/NOTES-model.md`:
  - retries on transport errors and 429 (honouring `Retry-After`), never on a bad answer;
  - pacing at 2 concurrent and 30 per minute;
  - its own User-Agent;
  - cost from usage;
  - policy stop on 403 or abuse/policy text (writes `STOP.md`).
- **Credentials** only from `FQA_ENV_FILE`, then `.env`, never exposed.
- **Record/replay** per PLAN §3. Replay raises on a miss.
- **A LangChain-compatible chat-model wrapper**, so LangGraph can bind tools to it in record and replay modes.

**Done when:** tests pass with a fake transport (success, 429, 403, bad answer, replay hit and miss), and the lane report exists.

---

## Q5: Agents graph (Wave 1)

**Owns:** `src/field_quality_agents/agents/`, `prompts/`, `tests/agents/`.

### Build
LangGraph per PLAN §4: supervisor, intake agent and analysis agent, with tools from Q2's interfaces (fakes until Q2 lands).
- **Human checkpoints** via `interrupt`, plus the deterministic **simulated engineer** for batch runs.
- **Budgets:** 12 steps and 40k tokens per case.
- **Hard rules in code:** safety → human first; failing quotes dropped; no close/scrap/charge action exists.
- **Every step appended as a `TraceStep`.**
- **Prompts:** versioned files in `prompts/` (`p1`).

**Tests:** a scripted fake model drives every branch (safety, missing info, targeted test, budget hit, human override), plus a property test that no path closes a case without a `HumanDecision`.

**Done when:** tests are green and the lane report exists.

---

## Q6: Dashboard frontend (Wave 1)

**Owns:** `web/`, `tests/web/` (Playwright specs).

### Build
Every PLAN §6 page per `DESIGN.md`, against the fixture JSON shapes in `docs/INTERFACES.md`:
- command centre;
- case board with case detail and the trace;
- issue room;
- before vs after;
- replay (play, pause, speed);
- weekly report.

Also:
- a data layer that reads either the live API (with SSE) or bundled JSON (static export);
- light and dark, 360 px, keyboard-accessible approve/override;
- Playwright specs with axe checks.

**Done when:** `npm run typecheck build test` is green on fixtures, screenshots are in the task folder, and the lane report exists.

---

## Q7: Backend API (Wave 1)

**Owns:** `src/field_quality_agents/api/`, `tests/api/`.

### Build
A FastAPI app:
- cases, case detail, trace, issues, KPIs, the before/after summary, weekly report;
- `POST` approve/override/ask for live mode, resuming the graph from its checkpoint;
- an SSE stream of agent actions;
- replay endpoints that serve a recorded run;
- static file serving for `web/dist`.

**Tests:** run against a fixture database with a fake graph.

**Done when:** tests are green and the lane report exists.

---

## Q8: Issue and report agents, end-to-end wiring (Wave 2; needs Q1–Q7)

**Owns:** `src/field_quality_agents/agents/issue.py`, `src/field_quality_agents/agents/report.py`, `src/field_quality_agents/run/`, `tests/e2e/`, `tests/fixtures/recordings/`.

### Build
- **Issue agent and report agent** per PLAN §4. 8D drafts and memos cite ids; citation validity is checked in code.
- **`fqa run --mode replay|record --set replay_2025 --run-id <id>`** plays the cases in date order, day by day:
  - calls the issue agent after each simulated day and the report agent after each simulated week;
  - writes `results/runs/<id>/` (cases, traces, proposals, decisions, issues, 8D, memos, report, metrics, manifest).
- **`make all`** = data check → baseline → run (replay) → metrics → export dashboard data → web build. Byte-identical twice on fixture recordings.
- **e2e:** Playwright over `make serve` with fixture recordings: open a case, approve, see it move, open an issue.

**Done when:** `make all` works on fixtures, e2e is green, and the lane report exists.

---

## Q9: Main live run (Wave 3; real model calls)

**Owns:** `recordings/`, `results/`, `reports/RUN.md`.

**Key:** `FQA_ENV_FILE=~/.config/field-quality-agents/upstream.env`. Never open or print it.

### Steps
1. **Smoke run:** 20 cases, recorded. Check the traces look sane.
2. **Full run:** `make run-live` on `replay_2025` (600 cases) with the agentic desk, run id `live-2025`. Resumable. Stop on 403 or abuse.
3. **Metrics:** baseline and agentic metrics on the same cases.
4. **Replay check:** delete `results/`, run `make all` with no key and no network, and confirm it's byte-identical.
5. **`reports/RUN.md`:** spend, timing, steps per case, budget hits, deviations, headline metrics.

**Done when:** everything is committed and the lane report exists.

---

## Q10: Dashboard with real results and the static export (Wave 4; needs Q9)

**Owns:** `web/` (polish only), `src/field_quality_agents/export/`, `dist/field-quality-agents/`.

### Build
- Wire the real run into every page.
- Choose showcase examples by fixed rules: the earliest issue that preceded an investigation; the case with the longest agent trace that ended in a targeted test; a case the linear pipeline closed as no-trouble-found while the agent found a clue.
- Build the **static export** (offline, bundled JSON) to `dist/field-quality-agents/`.
- Take Playwright screenshots of every page at 360 and 1280 px, light and dark, into `results/screenshots/`.

**Done when:** the export opens offline, `make facts` is green, and the lane report exists.

---

## Q11: Docs (Wave 4; needs Q9)

**Owns:** `README.md`, `METHOD.md`, `THIRD_PARTY.md` (polish), `CHANGELOG.md`, `project-facts.yml`, the facts check script.

- **README:** the plain question; a 3-step quickstart (`make setup`, `make all`, `make serve`); before vs after headline numbers with files; screenshots; limits (US vehicle data stands in for supplier returns; the engineer is simulated in the batch run; the rulebook is an example).
- **METHOD:** PLAN §3–§8 in plain words.
- `make facts` green.

**Done when:** `make release-check` is green and the lane report exists.

---

## Q12: Independent review (Wave 4; needs Q9; a fresh worker that wrote none of this code)

**Owns:** `reports/REVIEW.md` only.

### Check
1. **A clean clone:** `make release-check`; `make all` byte-identical.
2. **Data:** read 50 random committed narratives for personal data; verify the column drop and the licence wording.
3. **Agent safety:**
   - no path closes, scraps or charges without a human decision;
   - safety cases reach a human first;
   - failing quotes are dropped;
   - citations are validated.
4. **Metrics:** match PLAN §7; issue detection shows the base rate; the keyword files predate model results (git log).
5. **Numbers:** every dashboard and README number traces to `results/`.
6. **Scans:** forbidden names, secrets.

Write items as **blocker / should-fix / nit**, each with evidence.

**Done when:** `REVIEW.md` is committed.

---

## Q13: Fix-up (Wave 5; needs Q10, Q11, Q12)

**Owns:** any file named by a REVIEW blocker.

Fix every blocker and cheap should-fix. Re-run `make all` and `make release-check`. Mark each review item fixed or open.

**Done when:** green, and the lane report exists.

---

## Q14: Final live test on unseen data (Wave 6; needs Q13; real model calls)

**Owns:** `recordings/final-live/`, `results/final-live/`, `reports/FINAL-LIVE.md`.

### Steps
1. Unseal `final_live` (150 cases, the latest 4 weeks).
2. Run it through **both pipelines** live: the agentic desk with recording, as it would run in production.
3. Start `make serve` in **live mode** and drive 5 cases by hand through Playwright: open, read the trace, approve one, override one, ask on one. Capture screenshots and a short GIF of the replay page.
4. **Compare** with Q9: did the numbers hold on new data? Report plainly, including anything that got worse.
5. Add a "Final live test" panel to the dashboard and the static export (numbers from `results/final-live/`).

**Done when:** everything is committed, `make all` is still byte-identical, and the lane report exists.

---

## Q15: Release and dossier (Wave 7; needs Q14)

**Owns:** `reports/RELEASE.md`.

1. Run `make release-check` from a clean clone and confirm `make all` is byte-identical.
2. Check that `git remote -v` is empty and there is no unlanded work.
3. Re-run the scans.
4. **`reports/RELEASE.md`:**
   - what was checked;
   - headline numbers with files;
   - spend (Q9 + Q14);
   - open review items and deviations;
   - the screenshot paths;
   - the **publish checklist** for the captain: `gh repo create sabers13/field-quality-agents --public --source . --remote origin`, then `git push -u origin main`, then `git push origin v1.0.0`, plus how to add the static export to the portfolio site.
5. Create the local tag `v1.0.0`.

**Done when:** the tag exists, nothing was pushed, and the lane report exists.
