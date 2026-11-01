# v1.0.0 release dossier

**Status: local release candidate, tagged `v1.0.0`.** Nothing was pushed, no
remote exists, nothing was published. The captain publishes (§6).

| item | value |
|---|---|
| branch | `fm/fqa-q15`, fast-forward on `main` at `73eeff6` (Q14) |
| tag | `v1.0.0`, local only, on the release commit that carries this file |
| remote | none (`git remote -v` is empty) |
| clean-clone gate | `make release-check` green; `make all` byte-identical twice |
| tests | 358 passed |
| committed data | 8.4 MiB under `data/`; 36 MiB under `results/`; 13 MiB of recordings |
| total spend | USD 0.983849 (Q9 0.798998 + Q14 0.184851) |

## 1. What was checked

The check ran from a real clean clone outside the worktree:
`/home/saber_s13/firstmate/data/fqa-q15/clean-clone`, cloned from local `main`,
its `origin` removed, no network used (`FQA_ENV_FILE` pointed at a missing file
and `HTTP_PROXY`/`HTTPS_PROXY` at a closed port).

1. **`make setup`** — `uv sync --all-groups` and `npm install`, exit 0.
2. **`make release-check`** — green, exit 0:
   - Ruff: all checks passed;
   - mypy on `src/`: no issues in 84 source files;
   - pytest: **358 passed** (sockets guarded, no network);
   - dashboard type-check and Vite production build;
   - `scan-forbidden`: ok, 1,291 tracked files and 24 commit messages;
   - `scan-secrets`: ok, same scope;
   - `facts`: ok, 18 headline rows and 28 facts, all traced to committed
     `results/`;
   - `results_manifest.py check`: **631 files byte-identical** to
     `results/MANIFEST.sha256`.
   The same gate was re-run in the same clean clone after this dossier was
   added (fresh checkout of the release branch, same no-key/no-network
   environment) and is green again: 1,293 tracked files, 25 commit messages,
   631 file hashes unchanged. The only difference from the run above is the two
   new Markdown files.
3. **`make all` twice** from the clean clone, same no-key/no-network
   environment:
   - pass 1 and pass 2 produce byte-identical output: 106 files under
     `results/` and 610 files under `dist/field-quality-agents/` compare equal
     by sha256 (`results-pass1.sha256` vs `results-pass2.sha256`,
     `dist-pass1.sha256` vs `dist-pass2.sha256`);
   - `git status` stays clean after both passes, and
     `scripts/results_manifest.py check` passes again — the committed manifest
     is the one a clean clone reproduces.
4. **Scans re-run in the release worktree** — `make scan-forbidden` and
   `make scan-secrets` both green over the same 1,291 files (including the Q14
   recordings, results and screenshots). No key or credential file is tracked;
   the key is only ever read from the file named by `FQA_ENV_FILE`.
5. **Repository state** — `git remote -v` is empty; `git branch --no-merged
   main` is empty and `git stash list` is empty (no unlanded work); `HEAD` and
   `main` are both `73eeff6`; no tags existed before `v1.0.0`.

Proof logs (outside the repository):
`/home/saber_s13/firstmate/data/fqa-q15/{setup.log,release-check.log,make-all-1.log,make-all-2.log,results-pass1.sha256,results-pass2.sha256,dist-pass1.sha256,dist-pass2.sha256,tracked-before.sha256}`.

The manifest deliberately hashes exactly what `make all` regenerates:
`results/baseline/`, `results/runs/replay/` and `dist/field-quality-agents/`.
The record-mode runs (`results/runs/live-2025/`, `results/final-live/`) are made
from recordings, not rebuilt by `make all`, and are checked by replaying the
same recordings (see `reports/RUN.md`).

## 2. Headline numbers and their files

Intervals are 95%. The component metric bootstraps 2,000 resamples with seed
20261031. Every number below is copied from a committed file; an em dash means
the row has no valid measurement, and the reason is given under the table.

**Q9, the 600-case replay set** — before from
`results/baseline/metrics.json`, after from `results/runs/replay/metrics.json`
(identical content to `results/runs/live-2025/metrics.json`):

| metric | before (linear) | after (agentic) |
|---|---:|---:|
| component group macro-F1 | 0.7340 [0.6870, 0.7691] | — withheld |
| group coverage | 1.0000 | — withheld |
| safety precision | 0.4482 [0.3928, 0.5048] | — withheld |
| safety recall | 0.8590 [0.7957, 0.9050] | — withheld |
| targeted load test share | 0.0000 (not offered) | 0.4198 [0.3388, 0.5055] (55 of 131) |
| targeted test with a verified condition quote | — | 0.5636 [0.4327, 0.6863] (31 of 55) |
| quote grounding | — | 0.9064 [0.8972, 0.9149] (4,166 proposed, 27 dropped) |
| citation validity | — | 1.0000 [0.9948, 1.0000] (736) |
| recall link match | — | 0.1667 [0.0301, 0.5635] (1 of 6) |
| issue precision / base rate / median lead | — | 0.40 (2 of 5) / 0.20 / 65 days |
| human touches per case | 1.0 | 1.0 |
| decided without edits | — | 1.0000 (the simulated engineer's rule) |
| steps per case (budget counter) | 4 | 4.26 |
| budget hits | 0 | 0 |
| cost per 1,000 cases | USD 0.00 | USD 1.33 |
| latency p50 / p95 | — | 14.8 s / 29.5 s |

**Q14, the 150 unseen cases** — before from
`results/final-live/baseline/metrics.json`, after from
`results/final-live/metrics.json`:

| metric | before (linear) | after (agentic) |
|---|---:|---:|
| component group macro-F1 | 0.7330 [0.6543, 0.7968] | **0.0333** [0.0000, 0.0800] |
| group coverage | 1.0000 | 1.0000 [0.9750, 1.0000] |
| safety precision | 0.2206 [0.1385, 0.3326] (68 predicted) | **0.1311** [0.0824, 0.2025] (122 predicted) |
| safety recall | 0.9375 [0.7167, 0.9889] | 1.0000 [0.8064, 1.0000] |
| targeted load test share | 0.0000 (not offered) | 0.3913 [0.2216, 0.5921] (9 of 23) |
| targeted test with a verified condition quote | — | 0.4444 [0.1888, 0.7333] (4 of 9) |
| quote grounding | — | 0.8889 [0.8689, 0.9061] (1,098 proposed, 122 dropped) |
| citation validity | — | 1.0000 [0.9663, 1.0000] (110) |
| fleet issues opened | — | 0 in 4 weeks |
| steps per case (budget counter) | 4 | 4.81 |
| cost per 1,000 cases | USD 0.00 | USD 1.2323 |
| latency p50 / p95 | — | 12.7 s / 27.1 s |
| closed no trouble found | 82 of 150 | — (no close action exists) |

Why the Q9 rows are blank: the frozen Q9 recordings carried the component
group and the NHTSA safety flag in the model input, so those two metrics were
copies of the answer key (`reports/REVIEW.md` B1/B2). The desk no longer sends
either field and the rows are withheld rather than republished; Q14 measures
them on unseen reports. Full narrative: `reports/RUN.md`,
`reports/FINAL-LIVE.md`, `reports/DEVIATIONS.md`.

Run totals, from the manifests and result files:
`results/runs/live-2025/manifest.json` (600 cases, 2,542 recorded steps,
0 budget hits, digest `69350c43bd033816`, 746 recorded turns under
`recordings/`), `results/runs/replay/manifest.json` (2,556 replayed steps,
6,683 trace records), `results/final-live/manifest.json` (150 cases, 722 steps,
digest `5253c49f3d821005`, 174 turns under `recordings/final-live/`,
1,856 trace records, 0 issues, 4 weekly reports).

## 3. Spend

| run | file | spend |
|---|---|---:|
| Q9 main live run (incl. smoke turns) | `results/runs/live-2025/manifest.json` → `spend_usd` | USD 0.798998 |
| Q14 final live test (incl. 5-case smoke) | `results/final-live/manifest.json` → `spend_usd` | USD 0.184851 |
| **total, gateway list cost** | | **USD 0.983849** |

PLAN §9 expected USD 1–4 for Q9 and under USD 1 for Q14. Q9 came in under its
range at USD 0.80; Q14 at USD 0.18. The figures are each run's own recorded
gateway list cost and include their smoke turns, which replay from the same
recording sets, so the total is not an undercount.

## 4. Open review items and deviations

**Open review item (captain decision): review B4, personal names in narratives.**
The PII screen covers VINs, e-mail addresses, phone numbers and street
addresses, not signature-style personal names in already-public NHTSA
narratives. Q12 found 17 case ids with such a signature. Q13 documented the
finding in `data/STATS.md`, `README.md`, `THIRD_PARTY.md` and
`reports/DEVIATIONS.md` and did not rebuild the committed sets, because that
changes the 600-case set and needs a new live run. This remains an open
PLAN §10.2 question for the captain: extend the screen and rebuild, or record an
explicit exception. Evidence: `reports/REVIEW.md` B4.

**Known limitation, not a deviation: Q14's group metric.** The desk answered
with a component description instead of a group id in 149 of 150 cases, because
`prompts/intake/p1.md` never names the ten valid ids after Q13 removed the given
group. That is a prompt defect, and it is deliberately not fixed on the 150-case
test set. The dashboard's final-live panel says so in one line. A v1.1 prompt
fix needs a fresh test set.

Other limitations stated in `README.md` "Limits" and unchanged by the release
check: US vehicle data stands in for supplier returns; the batch engineer is
simulated (all 600 decisions were approvals, so "decided without edits" is 1.0
by construction); the rulebook is an example; one model and one prompt version;
the comparison is a simulation.

All review blockers and should-fix items other than B4 are recorded as fixed by
Q13 in `reports/REVIEW.md` "Q13 fix-up status".

**Deviations** from `PLAN.md` are listed with reasons in
`reports/DEVIATIONS.md`:

1. output allowance 8,192 and `reasoning_effort = "low"` (a 1,024-token answer
   came back empty);
2. intake blocks only on component and symptom, not on mileage/date;
3. an unreadable 2xx answer sends the case to the engineer instead of aborting;
4. a policy stop exits cleanly with code 3 after writing `reports/STOP.md`;
5. `make all` exports only the replay run and owns the manifest;
6. the frozen Q9 recordings keep their historical payload
   (`--legacy-recorded-input`, replay only), so Q9's group and safety rows are
   withheld;
7. replayed step counters differ from the record run's (2,556 / 6,683 vs
   2,542 / 6,669) because Q13 added verification steps;
8. quote verification requires two words or an identifier with a digit, on word
   boundaries;
9. the condition-quote metric requires the quote to share a condition word with
   the targeted test.

Cosmetic nit seen during this pass and left alone (outside this lane):
`README.md` "Limits" numbers two consecutive items as 5.

## 5. Screenshots

- **Dashboard pages, 360 px and 1280 px, light and dark (32 PNGs):**
  `results/screenshots/` —
  `command-centre-{360,1280}-{light,dark}.png`,
  `case-board-…`, `case-detail-…`, `issue-room-…`, `issue-detail-…`,
  `before-after-…`, `replay-…`, `weekly-report-…`.
- **Hand-driven live session, Q14 (14 PNGs and a GIF):**
  `results/final-live/playwright/` — `case-2251191-trace.png`,
  `case-2251191-trace-steps.png`, `case-2251191-approved.png`,
  `case-2251307-trace.png`, `case-2251307-overridden.png`,
  `case-2251350-trace.png`, `case-2251350-asked.png`,
  `case-2251369-trace.png`, `case-2251369-trace-dark.png`,
  `case-2251512-trace.png`, `command-centre-final-live-panel.png`,
  `command-centre-final-live-panel-360.png`,
  `command-centre-final-live-panel-dark.png`, `replay-page.png`, `replay.gif`.

The static export that carries the same pages is `dist/field-quality-agents/`
(610 files, 23 MiB, built by `make all`; it is git-ignored and must be rebuilt
before publishing). It is offline: no API and no network, reading the bundled
JSON under `data/`.

## 6. Publish checklist for the captain

Everything below is the captain's action. This lane did none of it; the tag is
local only and no remote exists.

```bash
# 1. Create the public repository and add it as origin (from the repo root).
gh repo create sabers13/field-quality-agents --public --source . --remote origin

# 2. Push the release branch as main.
git push -u origin main

# 3. Push the local tag.
git push origin v1.0.0
```

Then, for the portfolio site:

1. Rebuild the export from a clean tree: `make all` (writes
   `dist/field-quality-agents/`), and open `dist/field-quality-agents/index.html`
   once offline to confirm it renders.
2. Copy the whole `dist/field-quality-agents/` directory into the portfolio's
   static root as a subdirectory, for example `field-quality-agents/`, and link
   to it. The export uses relative asset paths (`./assets/…`, `./data/bundle.js`)
   and hash routing (`#/cases`, `#/replay`), so it needs no server rewrite rule
   and works from any subpath.
3. Keep the directory together (23 MiB); the bundled JSON is the dashboard's
   only data source in static mode.

Optional after publishing: check the repository renders `README.md`, that
`v1.0.0` appears under Tags, and that the Actions/security tabs are as expected
for a public MIT project.
