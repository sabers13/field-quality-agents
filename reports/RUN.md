# Q9: the main live run

Status: **in progress, paused at a safe point.** The 600-case run is resumable
from its recordings; see "Where the run stands" below. The final numbers and
the replay check are filled in when the run completes.

## What the run is

`FQA_LIVE_APPROVED=1 make run-live` plays the committed `replay_2025` set (600
NHTSA complaints received during 2025) through the agentic desk in record mode,
run id `live-2025`. Every model turn is stored under `recordings/`, keyed by
`sha256(model + prompt version + canonical messages + tools)`. Recording mode
reuses any existing key, so a stopped run resumes where it left off: the next
invocation replays the completed turns from disk and calls the model only for
the turns still missing.

No key is printed, logged or recorded. The key is read only by
`llm/credentials.py` from the file named by `FQA_ENV_FILE`
(`~/.config/field-quality-agents/upstream.env`, mode 0600).

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
   `note_missing_info`.
3. **A 2xx answer with no content crashed the whole run.** Intake and
   analysis now treat `BadAnswerError` like unreadable output: the case goes
   to the engineer instead of aborting the batch.
4. **A policy stop exits cleanly.** `fqa run` catches `PolicyStopError`,
   prints its reason, and exits 3 after the error has written
   `reports/STOP.md`.
5. **Reproducibility tooling.** `make all` now exports the `replay` run
   explicitly (so the bundled dashboard data does not depend on whichever
   record-mode run is newest) and ends with
   `scripts/results_manifest.py write`, which hashes `results/baseline/`,
   `results/runs/replay/` and `dist/field-quality-agents/` into
   `results/MANIFEST.sha256`. The record-mode run is outside that manifest
   because `make all` cannot create it offline; it is checked by replaying the
   same recordings under run id `replay` and comparing the content files.

## Where the run stands (paused 2026-11-01T09:0xZ)

- Recordings committed: 75 turns (24 smoke + 51 from the main run), USD
  0.08774 of gateway list cost in total.
- The main run stopped cleanly with SIGTERM after the in-flight call finished;
  `make run-live` reported `Error 143`. No `reports/STOP.md` was written, so
  there was no policy stop.
- No `results/runs/live-2025/` directory exists yet: the pipeline writes it
  only after all 600 cases complete.
- Resume with `FQA_LIVE_APPROVED=1 make run-live`. Completed turns replay from
  disk; the model is called only for the turns still missing.

## Spend, timing, steps per case

To be filled in when the run completes.

## Headline metrics

To be filled in when the run completes, from `results/runs/live-2025/metrics.json`
and `results/baseline/metrics.json` (same 600 cases).
