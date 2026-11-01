# Q9: the main live run

Status: **complete.** 600 cases were played through the agentic desk in record
mode as run `live-2025`, and the whole run replays byte-identically from the
committed recordings with no key and no network.

## What the run is

`FQA_LIVE_APPROVED=1 make run-live` plays the committed `replay_2025` set (600
NHTSA complaints received during 2025) through the agentic desk in record mode,
run id `live-2025`. Every model turn is stored under `recordings/`, keyed by
`sha256(model + prompt version + canonical messages + tools)`. Record mode
reuses an existing key, so a stopped run resumes where it left off: the next
invocation replays the completed turns from disk and calls the model only for
the turns still missing.

No key is printed, logged or recorded. The key is read only by
`llm/credentials.py` from the file named by `FQA_ENV_FILE`
(`~/.config/field-quality-agents/upstream.env`, mode 0600).

## Run totals

| item | value |
|---|---:|
| cases | 600 |
| model turns recorded | 746 (600 intake + 146 analysis) |
| trace steps | 2,542 |
| steps per case | 4.24 (median trace 10 steps, max 16) |
| budget hits | 0 |
| issues opened | 5 |
| weekly reports | 53 (52 in `reports.json`, the latest in `report.json`) |
| decisions | 600 approve (simulated engineer) |
| cases decided | 587 |
| cases that need an engineer | 13 (info requests) |
| **spend (gateway list cost)** | **USD 0.798998** |
| cost per 1,000 cases | USD 1.3317 |
| wall clock | 2 h 36 min across two attempts (16 min before the pause, 2 h 20 min after) |
| model latency | p50 14.8 s, p95 29.5 s |

PLAN §9 expected USD 1–4; the run cost USD 0.80. The figure is the sum of the
gateway's own list cost in each recorded turn, so it includes the smoke run's
calls (they are the first 20 cases of the same recording set).

## Smoke run

The smoke run used the same command with `--limit 20`, run id
`live-2025-smoke`, over the first 20 cases in received-date order.

| item | value |
|---|---:|
| cases | 20 |
| trace steps | 82 |
| model calls recorded | 24 |
| spend (gateway list cost) | USD 0.029799 |
| budget hits | 0 |
| cases reaching analysis | 4 |
| cases routed to safety priority | 16 |
| unreadable model answers | 0 |

The first smoke attempt failed: the endpoint returned an empty answer because
DeepSeek V4.1 Flash spent the whole `max_tokens` allowance on reasoning tokens.
Both run-enabling fixes below were made only after that trace was inspected.
The smoke traces then looked sane: intake extraction, duplicate search, a
safety proposal or an evidence-backed analysis proposal, a human decision and
a finish step per case.

## Deviations found by the live run (and fixed before the main run)

1. **Output allowance and reasoning effort.** With `max_tokens = 1024` (the
   PLAN minimum) the model used all 1024 tokens as reasoning and returned an
   empty answer (`finish_reason: length`). The request now asks for 8192
   tokens and pins `reasoning_effort = "low"` (both verified against the
   endpoint on 2026-11-01). PLAN §3 says "at least 1,024", so this stays
   inside the method. `config/budget.toml` carries the values.
2. **Intake blocked almost every case on mileage/date.** The model listed
   `mileage` and/or `date` as missing information for 19 of 20 smoke cases,
   so those cases stopped at intake and never reached analysis; `date` is
   always known from the received date. Intake now treats only `component`
   and `symptom` as blocking and records the rest in the trace as
   `note_missing_info` (540 cases took that path).
3. **A 2xx answer with no content crashed the whole run.** Intake and
   analysis now treat `BadAnswerError` like unreadable output: the case goes
   to the engineer instead of aborting the batch. In the main run there were
   no unreadable answers.
4. **A policy stop exits cleanly.** `fqa run` catches `PolicyStopError`,
   prints its reason, and exits 3 after the error has written
   `reports/STOP.md`. No policy stop occurred.
5. **Reproducibility tooling.** `make all` now exports the `replay` run
   explicitly and exports only that run, so the bundled dashboard data does
   not depend on which record-mode runs sit beside it. It ends with
   `scripts/results_manifest.py write`, which hashes `results/baseline/`,
   `results/runs/replay/` and `dist/field-quality-agents/` into
   `results/MANIFEST.sha256`. The record-mode run is outside that manifest
   because `make all` cannot create it offline; it is checked by replaying the
   same recordings under run id `replay` and comparing every content file.

## Replay check

`bash /home/saber_s13/firstmate/data/fqa-q9/replay-check.sh`:

1. `make all` with `FQA_ENV_FILE` pointing at a missing file and
   `HTTPS_PROXY`/`HTTP_PROXY` pointed at a closed port; 140 s.
2. The record-mode directory was moved aside, `results/` was deleted, and
   `make all` ran again under the same no-key/no-network conditions.
3. `results/MANIFEST.sha256` was byte-identical (644 files: baseline, the
   replay run and the dashboard data).
4. Every content file of `results/runs/live-2025/` was byte-identical to the
   replayed `results/runs/replay/`. Only `manifest.json` (`mode`, `run_id`)
   and `events.json` (the run id in report events) differ by design.
5. The record-mode directory was restored.

## Headline metrics, same 600 cases

From `results/runs/live-2025/metrics.json`. Intervals are 95%; the component
metric bootstraps 2,000 resamples with seed 20261031.

| metric | before (linear) | after (agentic) |
|---|---:|---:|
| component group macro-F1 | 0.7340 [0.6870, 0.7691] | **0.9898 [0.9745, 0.9997]** |
| group coverage | 1.0000 | 1.0000 |
| safety precision | 0.4482 [0.3928, 0.5048] | 0.3377 [0.2960, 0.3820] |
| safety recall | 0.8590 [0.7957, 0.9050] | **1.0000 [0.9760, 1.0000]** |
| targeted load test share | not offered | 0.4198 [0.3388, 0.5055] (55 of 131) |
| targeted test with a verified quote | — | 1.0000 (55 of 55) |
| quote grounding | — | 1.0000 [0.9946, 1.0000] (709 quotes) |
| citation validity | — | 1.0000 [0.9949, 1.0000] (751 citations) |
| recall link match | — | 0.1667 [0.0301, 0.5635] (1 of 6) |
| issue precision | — | 0.40 (2 of 5) |
| issue base rate | — | 0.20 |
| issue median lead time | — | 65 days |
| human touches per case | 1.0 | 1.0 |
| decided without edits | — | 1.0000 |
| steps per case | 4 (fixed model) | 4.24 |
| budget hits | 0 | 0 |
| cost per 1,000 cases | USD 0.00 | USD 1.33 |
| latency p50 / p95 | — | 14.8 s / 29.5 s |

Proposal mix: 456 safety priority, 76 standard test, 55 targeted load test,
13 information requests. The 13 information requests were approved as
requests and left the case with an engineer, as intended.

The five issues the fleet agent opened:

| issue | opened | vehicle | group | observed / threshold | linked cases |
|---|---|---|---|---:|---:|
| I-20250217-001 | 2025-02-17 | FISKER OCEAN 2023 | adas | 36 / 17.0 | 2 |
| I-20250711-002 | 2025-07-11 | POLESTAR POLESTAR 2 2021 | adas | 26 / 8.0 | 3 |
| I-20250713-003 | 2025-07-13 | POLESTAR POLESTAR 2 2022 | adas | 43 / 12.0 | 2 |
| I-20250916-004 | 2025-09-16 | TESLA MODEL Y 2021 | power_and_wiring | 6 / 5.0 | 2 |
| I-20251023-005 | 2025-10-23 | VOLKSWAGEN ID.4 2025 | adas | 6 / 5.0 | 2 |

## What did not go well

- **Safety over-flagging.** The intake model marked 462 of 600 cases
  safety-relevant (77%), against 156 cases in the NHTSA crash/fire/injury
  fields. Recall is perfect but precision falls from 0.45 to 0.34, and only
  146 cases reach the analysis agent because safety cases go to a human
  first. This is reported as behaviour, not tuned after seeing the replay
  set. A later prompt revision should separate "mentions a crash risk" from
  "the report is safety-relevant".
- **Recall linking is thin.** Only 6 recalls were linked across the five
  issues, and 1 of the 6 matched on make, model, year and group. The knowledge
  base rarely has a recall for the exact vehicle/group pair.
- **The batch engineer approves everything.** All 600 decisions were
  approvals, so "decided without edits" is 1.0 by construction; it measures
  the simulated engineer's rule, not a person's judgement.

## Artifacts

- `results/runs/live-2025/` — the record-mode run (manifest mode `record`,
  recording digest `69350c43bd033816`).
- `results/runs/replay/` — the same run rebuilt from the recordings.
- `recordings/` — 746 recorded turns (600 intake + 146 analysis); the 24 smoke
  turns are among them and replay in the full run.
- `results/baseline/` — the linear pipeline on the same 600 cases.
- `results/MANIFEST.sha256` — hashes of the reproducible results and
  dashboard data.
