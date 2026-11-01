# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
the project uses semantic versioning. This is a local-only project: nothing is
pushed and no package is published.

## [0.1.0] - 2026-11-01

The first complete local version: both pipelines, the recorded run, the
dashboard and the documentation.

### Added

- **Data build.** NHTSA complaint, recall and investigation flat files are
  downloaded with a recorded hash, screened for personal data, mapped to ten
  electrical and electronic component groups, and derived into committed
  parquet files. `data/STATS.md` records every count and drop reason.
- **Linear baseline.** A keyword pipeline (`config/keywords.toml`) that sorts a
  report, raises a safety flag, runs a simulated standard test and closes no
  trouble found when the test passes. A TF-IDF plus logistic-regression
  classifier is a second reference for the component group.
- **Agentic desk.** A LangGraph graph with a supervisor, intake, analysis,
  issue and report agents, typed tools, human checkpoints, per-case budgets and
  a full trace. Hard rules keep safety cases in front of a person, drop quotes
  that fail verification, and prevent any automatic close, scrap, return or
  charge acceptance.
- **Issue and report agents.** A weekly Poisson spike rule over fleet counts,
  linked recalls and investigations, 8D D1–D4 drafts, decision memos with
  checked citations, and a weekly quality report built from the run's tables.
- **Record and replay.** Every live model turn is stored under `recordings/`,
  keyed by model, prompt version, canonical messages and tools. Replay mode is
  offline, and `make all` rebuilds `results/` and the dashboard data from the
  recordings.
- **Dashboard.** A React + TypeScript application with a command centre, case
  board, case detail with trace and highlighted quotes, issue room,
  before/after comparison, replay player and weekly report, in light and dark
  at desktop and phone widths. It runs in replay mode, live mode with SSE and
  approve / override / ask, and as a static offline export.
- **MCP server.** The same search, lookup, quote-check and rulebook tools over
  stdio, for any MCP client.
- **Quality gates.** Ruff, mypy, offline pytest with a socket guard, the web
  type-check and build, a forbidden-name scan, a secrets scan and a facts check
  that traces every README number to `results/`.

### Recorded run

- Run `live-2025`: 600 reports from the 2025 replay set through the agentic
  desk, recorded from the real endpoint. All 600 decisions were made by the
  simulated engineer; the desk spent USD 0.798998 at gateway list cost, opened
  5 fleet issues and wrote 53 weekly reports.
- The baseline processed the same 600 reports, closing 301 as no trouble found
  and leaving 299 in a priority queue.
- The replay check re-ran `make all` with no key and the network blackholed;
  the results manifest was byte-identical, and every content file of the
  recorded run matched its replay. Details in `reports/RUN.md`.
- Headline metrics, both pipelines, in `results/runs/replay/metrics.json`:
  component macro-F1 0.7340 before and 0.9898 after; safety recall 0.8590 and
  1.0000; issue precision 0.4000 against a 0.2000 base rate; 709 verified
  quotes and 751 valid citations.

### Changed

Changes made after the first live attempts:

- The model request now asks for 8192 output tokens and pins reasoning effort
  to the documented low setting. The previous 1,024-token allowance was spent
  entirely on reasoning, producing an empty answer.
- Intake treats only a missing component or symptom as blocking; mileage and
  date are noted instead of stopping the case. The earlier rule sent almost
  every smoke-run case to a person.
- A 2xx answer with no usable content now sends the case to an engineer instead
  of aborting the batch.
- A policy stop exits the CLI cleanly after writing `reports/STOP.md`.
- `make all` exports one explicit run and writes a results manifest, so the
  reproducible output does not depend on which record-mode runs sit beside it.

### Known limits

- Safety is over-flagged: 462 reports were flagged against 156 in the NHTSA
  crash, fire, injury or death fields. Recall is 1.0000, precision 0.3377, and
  only 146 reports reach the analysis agent.
- Recall linking is thin: 0.1667 of linked recalls match make, model, model
  year and component group.
- The simulated engineer approved every proposal, so "decided without edits" is
  1.0000 by construction.
- One model and one prompt version; costs are gateway list prices.
- The vehicle data is public NHTSA data standing in for supplier returns, and
  the rulebook under `config/rulebook.toml` is an example, not a service
  manual.
