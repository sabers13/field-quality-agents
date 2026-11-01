# Q14: the final live test on unseen data

Status: **complete.** The sealed `final_live` set was unsealed and run once
through both pipelines: the linear baseline offline, and the agentic desk live
in record mode as run `final-live`. The 150 cases are the latest four complete
weeks in the snapshot (`2026-09-28` to `2026-10-25`) and were not used before
this task.

The numbers below come from `results/final-live/` and, for the comparison,
`results/runs/replay/`. The real run happened on 2026-11-01; the run manifest's
`started_at` and `completed_at` are the **simulated run clock** (the case
dates), as in Q9.

## What ran

| item | value |
|---|---:|
| cases | 150 |
| baseline | `results/final-live/baseline/` (no model call) |
| agentic run | `results/final-live/` (record mode, `model_input: clean`) |
| model turns recorded | 174 (150 intake + 24 analysis) |
| counted agent steps (budget counter) | 722 |
| trace records | 1,856 (median 12 per case, max 18) |
| cases that reached the analysis agent | 24 |
| budget hits | 0 |
| decisions | 150 approve (simulated engineer) |
| cases decided | 143 |
| cases that need an engineer | 7 (information requests) |
| fleet issues opened | 0 |
| weekly reports | 4 |
| **spend (gateway list cost)** | **USD 0.184851** |
| cost per case | USD 0.001232 |
| cost per 1,000 cases | USD 1.2323 |
| model latency | p50 12.7 s, p95 27.1 s |
| wall clock | 34 minutes (13:26–14:00 UTC) |

A 5-case smoke run (outside the repository) checked the live path first: 20
steps, USD 0.004637. Its turns are the first five cases' turns and replay from
the same recording set, so the USD 0.184851 above is the whole Q14 spend, not
an extra.

No key was printed, logged or recorded. The client read it only from the file
named by `FQA_ENV_FILE`. No 403, abuse or account warning occurred, so no
`reports/STOP.md` was written.

**The model saw no evaluation labels.** `manifest.json` records
`model_input: clean`: intake and analysis requests carried neither the NHTSA
component group nor the NHTSA safety flag. This is the first run in the project
where PLAN §7's two label-dependent metrics are real measurements rather than a
copy of the answer key.

## Q9 against the unseen set

Both columns are the agentic desk. Q9 is the 600 recorded 2025 cases; final
live is the 150 unseen cases. Intervals are 95%; the component metric
bootstraps 2,000 resamples with seed 20261031.

| metric | Q9 (600 cases) | final live (150 cases) | change |
|---|---:|---:|---|
| component group macro-F1 | withheld (labels in the request) | **0.0333** [0.0000, 0.0800] | measured for the first time; very low |
| group coverage | withheld | 1.0000 [0.9750, 1.0000] | the desk always answers |
| safety precision | withheld | **0.1311** [0.0824, 0.2025], 122 predicted | measured; poor |
| safety recall | withheld | 1.0000 [0.8064, 1.0000], 16 truth | measured; high by over-flagging |
| targeted load test share | 0.4198 [0.3388, 0.5055] (55 of 131) | 0.3913 [0.2216, 0.5921] (9 of 23) | 2.9 points lower |
| targeted test with a verified condition quote | 0.5636 [0.4327, 0.6863] (31 of 55) | 0.4444 [0.1888, 0.7333] (4 of 9) | 11.9 points lower |
| quote grounding | 0.9064 [0.8972, 0.9149] (4,166 proposed, 27 dropped) | 0.8889 [0.8689, 0.9061] (1,098 proposed, 122 dropped) | 1.8 points lower |
| citation validity | 1.0000 [0.9948, 1.0000] (736) | 1.0000 [0.9663, 1.0000] (110) | held |
| recall link match | 0.1667 (1 of 6) | no links (0 issues, 0 recalls) | not measurable |
| issue precision / base rate / lead | 0.40 (2 of 5) / 0.20 / 65 days | no issue opened | not measurable |
| human touches per case | 1.0 | 1.0 | held |
| decided without edits | 1.0000 | 1.0000 | held (the simulated engineer's rule) |
| steps per case | 4.26 | 4.81 | worse |
| latency p50 / p95 | 14.8 s / 29.5 s | 12.7 s / 27.1 s | slightly faster |
| cost per 1,000 cases | USD 1.3317 | USD 1.2323 | 7.5% cheaper |

The linear baseline on the same 150 cases, from
`results/final-live/baseline/metrics.json`:

| metric | value |
|---|---:|
| component group macro-F1 | 0.7330 [0.6543, 0.7968] |
| group coverage | 1.0000 |
| safety precision | 0.2206 [0.1385, 0.3326], 68 predicted |
| safety recall | 0.9375 [0.7167, 0.9889], 16 truth |
| targeted load test share | 0 (not offered) |
| closed no trouble found | 82 of 150 |
| TF-IDF reference macro-F1 | 0.4821 |

### Did the numbers hold? Plainly, no on quality; yes on cost and operations.

- **Component group: the measurement failed.** The desk answered with a
  component description (`ELECTRICAL SYSTEM`, `AIR BAGS`, `EXTERIOR
  LIGHTING`, …) instead of a group id in 149 of 150 cases; one case matched by
  chance. Macro-F1 is 0.0333, against the linear baseline's 0.7330. The cause is
  visible in the prompt: `prompts/intake/p1.md` asks for “the electrical/
  electronic component group, or the given group”, but Q13 removed the given
  group and the prompt never names the ten valid ids. Q9's 0.99 was a copy of
  that given group. So this is a **prompt defect**, not evidence that the model
  cannot classify, and it is the one thing to fix before publishing the number
  as a capability result. Q14 does not fix it on purpose: the 150 cases are the
  test set; tuning the prompt on them would make the test meaningless. The
  dashboard panel says the same in one line.
- **Safety: over-flagging got worse, and it is now measurable.** The desk
  flagged 122 of 150 cases (81%) as safety-relevant against 16 (10.7%) in the
  NHTSA crash/fire/injury fields. Recall is 1.0 by construction; precision is
  0.1311, below the linear baseline's 0.2206. The recorded Q9 run showed 77%
  flagged, but its flag was `truth OR model`; this is the first clean number and
  it is worse than the blended one suggested.
- **Evidence: slightly less grounded.** Quote grounding fell 1.8 points to
  0.8889 and the drop count rose to 122 of 1,098 quotes (11.1%, against 27 of
  4,166 in Q9). Many dropped clues are `component_group` quotes taken from the
  `component` field, which is not the narrative; intake now drops them instead
  of keeping them. Citation validity held at 1.0.
- **Targeted tests: a little less often and less grounded.** 9 of 23 test
  proposals asked for a targeted load test, and 4 of the 9 had a verified
  condition quote.
- **Fleet issues: none in four weeks.** With 150 cases over 20 days no
  vehicle/group key reached the spike rule with two linked cases, so the issue
  room is empty and issue precision, base rate, lead time and recall linking
  cannot be measured. This is a short window, not a failure; Q9's five issues
  covered a year.
- **Cost, latency and workload held.** USD 1.23 per 1,000 cases (7.5% cheaper),
  p50 12.7 s, one human touch per case, no budget hit. Steps per case rose from
  4.26 to 4.81; the extra work is intake quote verification (Q13's fix) and more
  routing, and it is the one operational number that moved the wrong way.

## The hand-driven live session

`make serve-live` started the live dashboard over `results/final-live` and its
recordings (25 case threads, no model call during the session). Five cases were
driven by hand through Playwright, oldest first:

| case | component | what was done | result |
|---|---|---|---|
| 2251191 | ELECTRICAL SYSTEM | opened, read the trace, **approved** the safety proposal | decided, decision recorded |
| 2251307 | HYBRID PROPULSION SYSTEM | opened, read the trace, **overrode** with a low-temperature soak and a reason | decided, edited proposal recorded |
| 2251350 | EXTERIOR LIGHTING | opened, read the trace, **asked** a question about the harness repair | stays with the engineer; the ask is a live step |
| 2251369 | ELECTRICAL SYSTEM | opened, read the trace | no action |
| 2251512 | ELECTRICAL SYSTEM | opened, read the trace | no action |

The overridden and approved decisions are visible in
`/api/cases/<id>` with `actor: live_engineer`; the ask appends a
`decision:ask` trace step and leaves the case at `needs_engineer`, by design.

Screenshots and the GIF are in `results/final-live/playwright/`:

- `case-2251191-trace.png`, `case-2251191-trace-steps.png`,
  `case-2251191-approved.png`
- `case-2251307-trace.png`, `case-2251307-overridden.png`
- `case-2251350-trace.png`, `case-2251350-asked.png`
- `case-2251369-trace.png`, `case-2251512-trace.png`
- `command-centre-final-live-panel.png`, `...-360.png`, `...-dark.png`
- `case-2251369-trace-dark.png`, `replay-page.png`
- `replay.gif` (12 frames of the replay page playing at 4x)

## The dashboard panel

The command centre now has a **Final live test** panel. It reads
`results/final-live/metrics.json` and the exported run's own metrics
(`results/runs/replay/metrics.json`) and shows Q9 beside the unseen set. The
same panel is in the offline export: `fqa export` loads it from
`results/final-live/`, writes it into `data/command_centre.json` and the bundle,
and the static page renders it without a network. The panel is absent when
`results/final-live/` is missing, so `make all` before Q14 stays reproducible.

## Checks

- `make all` twice: every file under `results/baseline/`,
  `results/runs/replay/` and `dist/field-quality-agents/` was byte-identical,
  and `scripts/results_manifest.py check` passed (631 files).
- `make test` (355 tests), Ruff, mypy, the dashboard type-check and build passed.
- `make scan-forbidden` and `make scan-secrets` passed, including the new
  recordings and results.
- `make release-check` passed; the manifest check is part of it.
- The live server was stopped after the session.

## Artifacts

- `results/final-live/` — manifest, cases, traces, extractions, proposals,
  decisions, evidence, issues (empty), reports, metrics, events.
- `results/final-live/baseline/` — the linear pipeline on the same 150 cases.
- `recordings/final-live/` — 174 recorded turns.
- `results/final-live/playwright/` — the hand-driven screenshots and GIF.
