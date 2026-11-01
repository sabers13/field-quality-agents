# Q9: the main live run

Status: **complete.** 600 cases were played through the agentic desk in record
mode as run `live-2025`, and the whole run replays byte-identically from the
committed recordings with no key and no network. Q13 re-derived the replay from
the same recordings after the review fixes; the fixtures under
`results/runs/live-2025/` are those refreshed content files, and its
`manifest.json` and `events.json` stay as the record run wrote them.

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
| counted agent steps (budget counter) | 2,556 |
| trace records | 6,683 |
| steps per case | 4.26 counted; median trace 10 records, max 16 |
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

The step counters are the replay's. The record run counted 2,542 steps and
6,669 trace records on the same turns; Q13 added a verification step whenever a
quote is dropped, which accounts for the 14-step difference. `started_at` and
`completed_at` in `manifest.json` are the **simulated run clock** (the case
dates, 2025-01-01 to 2025-12-30), not the wall clock; the real run was recorded
on 2026-11-01.

PLAN §9 expected USD 1–4; the run cost USD 0.80. The figure is the sum of the
gateway's own list cost in each recorded turn, so it includes the smoke run's
calls (they are the first 20 cases of the same recording set).

## Smoke run

The smoke run used the same command with `--limit 20`, run id
`live-2025-smoke`, over the first 20 cases in received-date order.

| item | value |
|---|---:|
| cases | 20 |
| counted agent steps (budget counter) | 82 |
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

## Deviations

The deviations this run introduced, and the ones Q13 added while fixing the
review, are listed with their reasons in `reports/DEVIATIONS.md`. The live-run
ones are the output allowance and reasoning effort, the intake mileage/date
gate, `BadAnswerError` handling, the policy-stop exit, and the reproducibility
tooling described under “Replay check” below.

## Replay check

`bash /home/saber_s13/firstmate/data/fqa-q9/replay-check.sh`:

1. `make all` with `FQA_ENV_FILE` pointing at a missing file and
   `HTTPS_PROXY`/`HTTP_PROXY` pointed at a closed port; 140 s.
2. The record-mode directory was moved aside, `results/` was deleted, and
   `make all` ran again under the same no-key/no-network conditions.
3. `results/MANIFEST.sha256` was byte-identical. The committed manifest now
   hashes 631 files: `results/baseline/`, the replay run and the dashboard
   data. An earlier check counted 644 because the git-ignored `dist/` still
   held 16 leftover e2e fixture case files; `make all` no longer writes into a
   stale export and `make release-check` now runs
   `scripts/results_manifest.py check`, so that cannot pass unnoticed again.
4. Every content file of `results/runs/live-2025/` was byte-identical to the
   replayed `results/runs/replay/`. Only `manifest.json` (`mode`, `run_id`)
   and `events.json` (the run id in report events) differ by design.
5. The record-mode directory was restored.

## Headline metrics, same 600 cases

From `results/runs/replay/metrics.json` (identical content to
`results/runs/live-2025/metrics.json`). Intervals are 95%; the component metric
bootstraps 2,000 resamples with seed 20261031.

| metric | before (linear) | after (agentic) |
|---|---:|---:|
| component group macro-F1 | 0.7340 [0.6870, 0.7691] | — (withheld) |
| group coverage | 1.0000 | — (withheld) |
| safety precision | 0.4482 [0.3928, 0.5048] | — (withheld) |
| safety recall | 0.8590 [0.7957, 0.9050] | — (withheld) |
| targeted load test share | not offered | 0.4198 [0.3388, 0.5055] (55 of 131) |
| targeted test with a verified condition quote | — | 0.5636 [0.4327, 0.6863] (31 of 55) |
| quote grounding | — | 0.9064 [0.8972, 0.9149] (4,166 proposed, 27 dropped) |
| citation validity | — | 1.0000 [0.9948, 1.0000] (736 citations) |
| recall link match | — | 0.1667 [0.0301, 0.5635] (1 of 6) |
| issue precision | — | 0.40 (2 of 5) |
| issue base rate | — | 0.20 |
| issue median lead time | — | 65 days |
| human touches per case | 1.0 | 1.0 |
| decided without edits | — | 1.0000 |
| steps per case | 4 (fixed model) | 4.26 |
| budget hits | 0 | 0 |
| cost per 1,000 cases | USD 0.00 | USD 1.33 |
| latency p50 / p95 | — | 14.8 s / 29.5 s |

**Why four rows are withheld.** The recorded requests carried the component
group and the NHTSA safety flag, so the model could copy them (review B1 and
B2). Those two columns are PLAN §7's evaluation targets; the desk now removes
them from every request and a record run cannot send them
(`--legacy-recorded-input` is replay-only). The recordings cannot reveal what a
desk without the labels would have answered, so the group and safety rows are
left blank instead of publishing a copy of the answer key. The final live run
on unseen reports measures them. Everything above the evidence rows is computed
from the run's own records and is unaffected.

**Quote grounding counts what the model proposed, not the survivors.** The
metric re-checks every clue the desk kept against its narrative and adds the
quotes a verification step dropped, so a rejected quote stays in the
denominator (review S1). The stricter span rule — at least two words or an
identifier, matched on word boundaries — is why the share is no longer 1.0 and
why a few short citations left the proposals (review S6). The targeted-test
share now requires the quoted span to share a condition word with the test
(review S2), which is why it falls from 55 of 55 to 31 of 55.

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

- **Safety over-flagging.** The recorded intake model marked 462 of 600 cases
  safety-relevant (77%), against 156 cases in the NHTSA crash/fire/injury
  fields. Part of that is the desk's own judgement and part was the recorded
  pipeline ORing NHTSA's flag into the prediction; the label is now out of the
  request and out of the prediction, so the final live run measures the model's
  own flag. Only 146 cases reached the analysis agent because safety-flagged
  cases go to a human first. A later prompt revision should separate "mentions
  a crash risk" from "the report is safety-relevant".
- **Quote spans were loose.** The analysis agent suggested 709 quotes and every
  one was accepted; the stricter rule now also checks intake clues, rejects a
  single ordinary word and requires word boundaries. On the same recorded
  answers the desk proposes 4,166 quotes and drops 27, so the grounding share
  is 0.9064 rather than 1.0.
- **Recall linking is thin.** Only 6 recalls were linked across the five
  issues, and 1 of the 6 matched on make, model, year and group. The knowledge
  base rarely has a recall for the exact vehicle/group pair.
- **The batch engineer approves everything.** All 600 decisions were
  approvals, so "decided without edits" is 1.0 by construction; it measures
  the simulated engineer's rule, not a person's judgement.

## Q13 fix-up on the same recordings

Q13 fixed the review blockers without a model call. The desk's request payload
no longer carries PLAN §7's evaluation targets, intake verifies its own quotes,
and the evidence metrics count dropped quotes. The committed recordings were
made with the old payload, so `make run-replay` replays them with
`--legacy-recorded-input`; `manifest.json` records
`model_input: legacy-evaluation-labels` and `metrics.json` records
`evaluation_labels_in_model_input: true`. That flag is what withholds the group
and safety rows. `make all` and `make release-check` are green, and
`results/MANIFEST.sha256` re-hashes the reproducible results. The item list is
in `reports/lanes/Q13.md`; the deviations are in `reports/DEVIATIONS.md`.

## Artifacts

- `results/runs/live-2025/` — the record-mode run (manifest mode `record`,
  recording digest `69350c43bd033816`).
- `results/runs/replay/` — the same run rebuilt from the recordings.
- `recordings/` — 746 recorded turns (600 intake + 146 analysis); the 24 smoke
  turns are among them and replay in the full run.
- `results/baseline/` — the linear pipeline on the same 600 cases.
- `results/MANIFEST.sha256` — hashes of the reproducible results and
  dashboard data.
