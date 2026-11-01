# Q12: independent review

**Reviewed:** local `main` at `7a2f468` (`feat: Q9 600-case live run with recordings and results`), in a fresh clone.
**Reviewer:** a worker that wrote none of this code.
**Scope:** `plan/TASKS.md` §Q12; this file is the only repository file changed.
**Model calls:** none. The review used replay mode only and never read a key or environment variable.

**Verdict: not ready for v1.** Two headline metrics are invalid because the evaluation
labels are in the model input, one PLAN §4 hard rule is not enforced for intake
clues, the committed reproducibility manifest does not reproduce from a clean
clone, and the PII screen misses personal names. The release-scope items that
depend on Q10/Q11 (README, static export, facts check) are also absent at this
commit and must be re-checked after those lanes land.

## How this was reviewed

A clean clone was made outside the worktree at
`/home/saber_s13/firstmate/data/fqa-q12/clean-clone` (local clone, remote removed,
no network use). Then:

- `make release-check` — green: Ruff, mypy (79 files), pytest (332 passed),
  dashboard build, forbidden-name scan (1,065 files and 16 commit messages),
  secrets scan (1,065 files and 16 commit messages), facts check.
- `make all` twice; every file under `results/` compared by sha256; the two
  regenerated passes were byte-identical. `scripts/results_manifest.py check`
  was run against the committed manifest as well.
- 50 uniformly random narratives were read from the three committed narrative
  files (40,000 knowledge-base + 600 replay + 150 final-live rows); all 40,750
  were then swept with the committed PII regexes and a signature-name
  heuristic.
- The agent graph, hard rules, issue agent, metrics modules and their tests were
  read directly; `tests/agents/test_hard_rules.py` and `tests/metrics` were run.
- The committed run was replayed and compared with `results/runs/live-2025/`;
  the `make serve` API was queried read-only and its numbers compared with
  `results/runs/replay/metrics.json`.

Proof files (outside the repository):
`/home/saber_s13/firstmate/data/fqa-q12/{release-check.log,make-all-1.log,make-all-2.log,results-pass1.sha256,results-pass2.sha256,manifest-check.log,narratives-50.txt,name-ids.txt}`.

---

## Blockers

### B1. The component-group metric is invalid: the truth label is in the model input

`Case.group` is the NHTSA-derived target (loaded from `replay_2025.parquet` in
`src/field_quality_agents/run/data.py:25,57`). The intake node sends the whole
case, including `group`, to the model:

- `src/field_quality_agents/agents/intake.py:62` —
  `json.dumps(case.model_dump(mode="json"), sort_keys=True)`;
- `src/field_quality_agents/contracts.py:135` — `group: str | None = None`;
- the intake prompt even says “or the given group”
  (`prompts/intake/p1.md`, `"group": "the electrical/electronic component group, or the given group"`).

The model copies it. In `results/runs/live-2025/`:

- 596 of 600 `extractions.json` groups are exactly equal to `cases.json` groups;
- the other four are wrong labels (for example case `2108854`: truth `adas`,
  prediction `airbag/SRS`), so the copy is not perfect, but it is still a copy
  of the input rather than an independent classification.

The metric then compares `run.extraction.group` with `case.group`
(`src/field_quality_agents/run/metrics.py:115`), producing
`group_macro_f1 = 0.989785 [0.974512, 0.999703]` against the linear baseline’s
`0.733967 [0.686986, 0.769053]` (`results/runs/live-2025/metrics.json`). The
headline “0.734 → 0.990” is therefore a copy of the answer key, not a
measurement of the agent. The issue agent also keys its clusters on
`case.group` (`src/field_quality_agents/agents/issue.py:377`), so fleet
detection receives the same target label.

**Evidence:** `results/runs/live-2025/extractions.json` vs `cases.json`;
`results/runs/live-2025/metrics.json`; `reports/RUN.md:119`.

**Fix:** remove `group` from every model-visible case payload (intake and
analysis, `intake.py:62` and `analysis.py:159`), and score a label the model
actually produced without seeing the answer. Re-run the replay from the
committed recordings and replace the affected numbers. If the group is meant to
be an input, drop the “component group macro-F1” comparison rather than present
it as an agent result.

### B2. The safety recall metric is 1.0 by construction: truth is ORed into the prediction

The same case payload carries `safety_relevant` (the NHTSA crash/fire/injury
target; `contracts.py:137`). Intake and analysis then force the state flag true
whenever the truth flag is true:

- `src/field_quality_agents/agents/intake.py:148,155` —
  `case.safety_relevant or extraction.safety_relevant`;
- `src/field_quality_agents/agents/analysis.py:285,292`.

The metric scores `run.case.safety_relevant` (`run/metrics.py:125-126`), so it is
scoring `truth OR model`, not the model. The result is the expected tautology:

- `safety_recall = 1.000000 [0.975967, 1.000000]`, `n = 156`;
- `safety_precision = 0.337662 [0.296035, 0.381967]`, `n = 462`;
- 462 predicted positives against 156 truth positives
  (`results/runs/live-2025/metrics.json`).

`reports/RUN.md:122` presents the perfect recall as a headline. It cannot be
anything else while the truth flag is in the prediction.

**Evidence:** `results/runs/live-2025/metrics.json`; `reports/RUN.md:121-122`;
the code paths above.

**Fix:** score the model’s own extraction flag only. Keep the truth flag out of
the model input and out of the predicted value. Recompute the metric; the real
recall is unknown until then.

### B3. Failing intake quotes are persisted, not dropped

PLAN §4 makes this a hard rule in code: “a clue whose quote fails verification is
dropped”. Analysis does verify and drop (`analysis.py:207-217`), but intake does
not: `intake.py:100` stores `clues=as_clues(payload)` straight from the model.
Safety cases and information-request cases never reach analysis, so their
intake extraction keeps the unchecked clues.

Measured on the committed run:

- 4,154 clues in `results/runs/live-2025/extractions.json`;
- 333 clues in 330 cases are not verbatim in the narrative;
- 330 of those are `component_group` quotes taken from the `component` field,
  which is not part of the narrative (for example, case `2052372`);
- the dashboard deliberately renders them as “not verified”
  (`web/src/components/Narrative.tsx`), which is honest display but is not the
  plan’s “drop” rule.

**Evidence:** `results/runs/live-2025/extractions.json` (the count is reproducible
by normalising whitespace and testing each `quote` against its case narrative);
`src/field_quality_agents/agents/intake.py:100`.

**Fix:** run `verify_quotes` at intake too and persist only verified clues (or do
not persist intake clues at all until analysis verifies them). Add the intake
case to `tests/agents/test_hard_rules.py`; the current test only covers analysis
(`tests/agents/test_hard_rules.py:109-122`). Re-run the replay.

### B4. Committed narratives contain personal names; the PII screen only covers four patterns

The 50-narrative sample contained no VIN, e-mail, phone number or street address
(a fresh sweep with the committed PII patterns found 0 hits across all 40,750
committed narratives), so the four implemented patterns work as designed. The sample did
contain a narrative ending in a self-identified first name and last initial
(case `1808202`). A sweep of all committed narratives found at least 15 distinct
narratives (17 case ids where two texts repeat) with a closing signature that
gives a personal name, several of them a full first and last name. The case ids
are:

`1672849`, `1717837`, `1733750`, `1759731`, `1781106`, `1808202`, `1837887`,
`1839692`, `1839693`, `1860759`, `1864832`, `1881163`, `1909008`, `1910694`,
`2001969`, `2001970`, `2033657`.

These are public NHTSA complaints, and a few may be no more than a first name.
But PLAN §2.3 says no private data, PLAN §5 defines the PII screen, and PLAN
§10.2 makes “a committed file contains suspected personal data” a stop
condition. Several of these are full personal names; the current screen cannot
see any of them. This is a suspected-personal-data stop condition. Q12 owns only
`REVIEW.md`, so it is recorded here rather than in `reports/STOP.md`; the
captain must decide.

**Evidence:** `/home/saber_s13/firstmate/data/fqa-q12/name-ids.txt` (names are
deliberately not reproduced here), `data/STATS.md` §“PII screen” (only vin,
email, phone, street_address), `src/field_quality_agents/data/pii.py:15`.

**Fix / decision needed:** either extend the screen to signature-like names and
rebuild the committed sets (which will change the 600/150 case counts and every
downstream result), or record a captain-approved exception in
`DEVIATIONS.md` explaining why names in already-public NHTSA narratives are
accepted. The review cannot choose that for the captain.

### B5. A clean clone does not reproduce the committed `results/MANIFEST.sha256`

At `7a2f468` the committed manifest has 644 lines. Sixteen of them are
`dist/field-quality-agents/data/cases/C-2025-*.json` files left by a prior
fixture/e2e export:

```
$ git show 7a2f468:results/MANIFEST.sha256 | wc -l
644
$ git show 7a2f468:results/MANIFEST.sha256 | grep -c 'C-2025'
16
```

In a clean clone, `make all` writes 628 hashes (it does not create those stale
fixture files), so the first `make all` rewrites the manifest:

```
make-all-1.log: manifest: wrote 628 file hash(es) to results/MANIFEST.sha256
```

`scripts/results_manifest.py check` against the committed file fails:

```
manifest: FAIL the reproducible results changed
manifest:   was ... dist/field-quality-agents/data/cases/C-2025-0007.json
...
EXIT=1
```

The two regenerated `make all` passes are byte-identical (`BYTE_IDENTICAL` in the
proof files), so the pipeline itself is deterministic; the committed manifest is
polluted by untracked build output. This contradicts PLAN §8 and the replay-check
claim in `reports/RUN.md:105-106`. `make release-check` does not run the manifest
check, so the green release gate misses it.

**Evidence:** `manifest-check.log`, `make-all-1.log`, `results-pass1.sha256`,
`results-pass2.sha256`; `scripts/results_manifest.py:24-32` includes
`dist/field-quality-agents/`, which `.gitignore` excludes.

**Fix:** clean `dist/field-quality-agents/data/cases` (or write the export to a
fresh directory), regenerate the manifest from a clean tree, and add
`results_manifest.py check` to `release-check`. Re-run `make all` twice from the
clean clone and confirm the tree is unchanged.

### B6. Release-scope blockers: Q10/Q11 artefacts are absent at this commit

These are not Q9 code defects; they are missing release deliverables because
Q10 and Q11 are not merged at `7a2f468`. They still block v1 and the Q12
number-trace check.

- `README.md`, `METHOD.md`, `CHANGELOG.md` and `project-facts.yml` are absent.
  `make facts` prints “project-facts.yml not present yet (Q11); nothing to
  verify” and exits 0 (`scripts/check_facts.py:14-17`), so the facts gate in
  `release-check` is a no-op.
- `dist/field-quality-agents/` contains only `data/`; there is no `index.html`
  or bundled JS. `make export` writes JSON, but the built app does not load it:
  static mode constructs `StaticDataSource()` with `fixtureBundle`
  (`web/src/App.tsx:78`, `web/src/data/static.ts:58`). The fixture comparison
  still carries invented numbers (for example issue precision 0.71 and base
  rate 0.021 in `web/src/data/fixtures/comparison.json`) where the committed
  results say 0.40 and 0.20. A static/portfolio page would therefore not show
  the project’s numbers.
- `results/screenshots/` does not exist.
- The Q12 item “every dashboard and README number traces to `results/`” cannot
  be completed until Q10/Q11 land.

**Evidence:** the file listing of this clone; `Makefile:86`; `dist/` listing;
`web/src/data/fixtures/index.ts`.

**Fix:** re-run this check after Q10/Q11 merge, with a real static export that
reads `results/` and a real `project-facts.yml`; require `make facts` to fail
when the file is missing.

---

## Should-fix

### S1. `quote_grounding_rate = 1.0` is computed over only the quotes that already passed

`run/metrics.py:54-64` builds `_quote_checks` from `proposal.evidence` only, and
analysis has already removed the unverified clues before creating the proposal
(`analysis.py:207-217`). The 333 unverified intake clues in B3 are not in the
denominator. The reported `1.000000 [0.994611, 1.000000]` over 709 quotes
therefore measures the survivors, not the model’s quote grounding.

**Evidence:** `results/runs/live-2025/metrics.json`; `run/metrics.py:54-64`;
`reports/RUN.md:125`.

**Fix:** count every quote the model proposed, mark each verified or dropped, and
report both “verified share” and “dropped count”; or rename the metric to
“verified-evidence share” and stop calling it a grounding rate.

### S2. `targeted_test_with_quote_share` does not tie the quote to the condition

PLAN §7 asks for targeted tests that “carry a condition with a verified quote”.
`metrics/evidence.py:101-110` actually requires (a) any non-empty `conditions`
tuple and (b) any verified quote anywhere in the proposal evidence. A test with
condition X and a verified quote about symptom Y counts as grounded.

**Evidence:** `src/field_quality_agents/metrics/evidence.py:101-110`; the metric
is 55/55 in `results/runs/live-2025/metrics.json`.

**Fix:** match the quoted clue to the condition it supports, or document the
looser definition in PLAN/DEVIATIONS and label the column accordingly.

### S3. The dashboard misstates what the issue base rate is

`web/src/pages/Comparison.tsx:128` says:

> “Issue precision is read beside the base rate: 0.2 of cases in this set belong
> to a cluster that later matched a recall or investigation.”

The metric is the share of random weeks in the issue’s own series that have a
following event within 365 days (`metrics/issues.py:96-107`), not a share of
cases. The number 0.2 is right; the sentence is wrong.

**Evidence:** `results/runs/live-2025/metrics.json` `issue_base_rate = 0.2`;
`metrics/issues.py`.

**Fix:** say “0.2 of random weeks in the same vehicle/group series have a
following recall or investigation within 365 days.”

### S4. `RUN.md` labels the budget-step counter as “trace steps”

`reports/RUN.md:27` reports “trace steps | 2,542”. That number is the run’s
counted-step total (`manifest.json` `steps = 2542`, `steps_per_case = 4.236667`).
The committed `traces.json` contains **6,669** `TraceStep` records (median 10 per
case, maximum 16). The same table’s “median trace 10 steps, max 16” uses the other
meaning. The number traces to a file, but the label is misleading.

**Evidence:** `results/runs/live-2025/traces.json` (sum of per-case list lengths);
`results/runs/live-2025/manifest.json`; `reports/RUN.md:27-28`.

**Fix:** label 2,542 as “counted agent steps (budget)” and add “trace records |
6,669”, or drop the ambiguous line.

### S5. No `reports/DEVIATIONS.md`, although `RUN.md` records deviations

PLAN §0 says a deviation goes to `reports/DEVIATIONS.md` with its reason.
`reports/RUN.md:67-95` lists the output-allowance/reasoning-effort change,
the intake mileage/date gate, and the `BadAnswerError` handling, and calls them
deviations, but no `DEVIATIONS.md` exists.

**Evidence:** `ls reports`; `reports/RUN.md:67-95`; `PLAN.md:3`.

**Fix:** move or copy the deviation list into `reports/DEVIATIONS.md`; keep
`RUN.md` as the narrative.

### S6. `verify_quotes` accepts any non-empty substring, including a single word

`tools/quotes.py:26-31` verifies a quote when `normalise(quote) in normalise(text)`.
There is no minimum length, word boundary or sentence check. A model quote of
“the” or “car” would be “verified” and could enter evidence. The prompt asks for
verbatim spans, but the code does not enforce a meaningful span.

**Evidence:** `src/field_quality_agents/tools/quotes.py:26-31`; the analysis
evidence path (`analysis.py:207-217`).

**Fix:** require a minimum character/word count and a word-boundary match, or
require the quote to be a sentence-like span; add a test with a one-word quote.

### S7. The intake quote-drop path has no regression test

The only quote-verification hard-rule test drives analysis
(`tests/agents/test_hard_rules.py:109-122`). Nothing asserts that intake stores
only verified clues, which is why B3 went unnoticed.

**Evidence:** `tests/agents/test_hard_rules.py`; `tests/agents/` contains no
intake-clue verification test.

**Fix:** add a scripted fake intake response with one true and one invented quote;
assert the extraction (and the trace) keeps only the true quote.

### S8. The manifest check is not part of `release-check`

`scripts/results_manifest.py` has a `check` mode, but `Makefile:85` only runs
lint, typecheck, test, web-build, the two scans and facts. A stale or polluted
manifest (B5) cannot fail the release gate.

**Evidence:** `Makefile:72-86`; `scripts/results_manifest.py:63-82`.

**Fix:** add a `results-manifest-check` target and make `release-check` depend on
it (after `make all` in the release sequence).

---

## Nits

- **N1. Stale scaffold messages.** `Makefile:86` prints “release-check: green on
  the Q0 scaffold”; `Makefile:68-70` says screenshots land with Q6/Q10 and exits
  2. Both read as unfinished scaffolding in a v1 review.
- **N2. Software licences promised but not listed.** `THIRD_PARTY.md:46` says
  “All other software licences are recorded here as later lanes add
  dependencies.” No Python or npm licence is listed. Q11 polish.
- **N3. Simulated timestamps in the run manifest.** `results/runs/live-2025/manifest.json`
  has `started_at 2025-01-01T06:00:00Z` and `completed_at 2025-12-30T23:59:00Z`,
  the simulated case dates, not the real run date (2026-11-01) recorded in the
  Q9 narrative. Useful for replay, confusing for provenance; add a real
  `recorded_at` or label the fields “simulated run clock”.
- **N4. `data/STATS.md` should state the PII screen’s scope.** It reports four
  pattern families and “PII screen”, which reads as complete. Say explicitly
  that names are not screened (or fix B4 and then say names are screened).
- **N5. Fixture numbers remain in the production bundle.** Even after Q10 wires
  the static export, `web/src/data/fixtures/` is imported by default; keep it
  test-only or make a missing real bundle a build error, so fixture numbers can
  never ship silently.
- **N6. The recall-linking sample is tiny.** 6 links, 1 match
  (`recall_link_match_rate 0.166667 [0.030053, 0.563503]`). The interval is
  reported honestly, but any prose that treats this as a stable rate should say
  “1 of 6”.

---

## What passed

- **Clean-clone release gate.** `make release-check` is green on a fresh clone:
  Ruff, mypy, 332 tests, Vite build, forbidden names, secrets, facts (see B6 for
  the facts no-op). Test sockets are guarded (`tests/conftest.py`).
- **Deterministic replay.** Two consecutive `make all` runs produce identical
  `results/` content; `results/runs/replay/` matches `results/runs/live-2025/`
  for all content files (only `manifest.json` and `events.json` differ by run id).
- **Column drop.** The committed narrative schemas contain only
  `id, received_at, make, model, year, component, group, narrative,
  safety_relevant, mileage`; `CITY`, `STATE`, `VIN`, dealer fields and
  `VEHICLE_OPERATOR` are read from the raw layout but never written.
  `tests/data/test_build.py::test_outputs_and_schemas` asserts the drop.
- **Licence wording.** `THIRD_PARTY.md` quotes NHTSA’s public-information
  statement, gives the URL and access date, and cites 17 U.S.C. §105; the MIT
  `LICENSE` is present.
- **Data selection.** 600 replay cases with 156 safety-relevant (PLAN asks at
  least 120); 150 sealed final-live cases; 40,000 knowledge-base rows; 8.4 MiB
  committed data; the final window is the last four complete weeks
  (`data/STATS.md`).
- **No close/scrap/charge path.** `DecisionAction` has only approve, override, ask
  and request_info; `CaseStatus` has no closed state; `finish` sets
  `needs_engineer` when no human decision exists; the trace-word test passes.
- **Safety first.** A safety-flagged case routes to the safety node and then the
  human gate before analysis; `test_a_safety_case_reaches_a_human_before_any_analysis_step`
  passes.
- **Citation validation.** `checked_citations` resolves every case/recall/
  investigation id and re-finds every quoted span; the metric re-checks the
  source instead of trusting the `verified` flag; `citation_validity_rate = 1.0`
  over 751 citations in the committed run.
- **Metrics coverage.** The modules implement every PLAN §7 metric: macro-F1
  with a 2,000-resample bootstrap, Wilson safety intervals, quote grounding,
  citation validity, targeted-test shares, issue precision/median lead/base
  rate, recall-link match, workload (touches, edits, steps, cost, latency,
  budget hits) and both baselines. Issue detection reports the base rate
  (0.20) beside precision (0.40) and median lead (65 days).
- **Keywords predate model results.** `config/keywords.toml` was added in
  `0b309e3` (“linear keyword rules before any model result”, 05:54), before the
  baseline results (`d15f369`, 06:01) and the live run (`7a2f468`, 11:55). Git
  log confirms the order.
- **Numbers trace.** The `make serve` API returns the committed metrics
  (`comparison.json` after values equal `results/runs/replay/metrics.json`), and
  the `RUN.md` spend (USD 0.798998), cases (600), issues (5), weekly reports
  (52 + 1), decisions (600) and statuses (587 decided / 13 needs engineer) all
  reproduce from `results/` and `recordings/` (746 recordings, list cost sums to
  USD 0.798998). The exceptions are S3/S4 and the missing README/static export
  in B6.
- **Scans.** `make scan-forbidden` and `make scan-secrets` pass on 1,065 tracked
  files and 16 commit messages; no `.env`, credential file or key pattern is
  tracked. The recordings store responses only, and the scan does not find a
  key.

## Open questions for the captain

1. **Names (B4):** extend the PII screen and rebuild the data, or record an
   explicit exception for names in public NHTSA narratives? The committed data
   contains full personal names, not just first names.
2. **Leakage (B1/B2):** if the desk is meant to receive the component group and
   safety flag as operational inputs, then the corresponding metrics must be
   removed or relabelled; if they are evaluation targets, they must leave the
   model input. Which is the intended design?
3. **Static export (B6):** Q10 is expected to wire it; confirm the release check
   must include a built `dist/field-quality-agents/index.html` that reads
   `results/`, not the fixture bundle.

## Q13 fix-up status

Q13 fixed or answered every item below in the local branch `fm/fqa-q13`, with no
model call (`make all` and `make release-check` are green). “Fixed” means the
code, a regression test and the documentation changed. Where the frozen Q9
recordings made a number impossible to re-derive offline, the metric is
withheld instead of republished; `reports/DEVIATIONS.md` records why.

| item | status | evidence |
|---|---|---|
| B1 group label in the model input | **Fixed** | `agents/payload.py` removes `group` and `safety_relevant` from every request; intake/analysis use it; `tests/agents/test_hard_rules.py::test_the_model_never_sees_the_evaluation_labels`. The recorded run's group metric is withheld (it measured a copy) and is measured at Q14. |
| B2 safety truth ORed into the prediction | **Fixed** | the prediction is the desk's own flag (`intake.py`); same payload scrub; `test_the_truth_safety_flag_is_not_copied_into_the_prediction`; safety rows withheld for the recorded run. |
| B3 intake quotes persisted unchecked | **Fixed** | `intake.py::_intake_clues` verifies and drops, with a trace step; `test_intake_drops_an_invented_quote_before_persisting_it`. The frozen recorded run keeps its pre-fix `extractions.json`; the quote metric now re-checks every kept clue and counts the failures (`0.9064` of `4,166`, `27` dropped). |
| B4 personal names in narratives | **Open — captain decision** | `data/STATS.md` and `README.md` now state the screen's scope and the finding; no committed set was rebuilt, because that changes the 600-case set and needs a new live run. Options and the PLAN §10.2 question are in `reports/DEVIATIONS.md`. |
| B5 manifest polluted by `dist/` leftovers | **Fixed** | the committed manifest has 631 hashes, none under `dist/…/cases`; `scripts/results_manifest.py check` passes and is now part of `release-check` (`Makefile`). |
| B6 Q10/Q11 artefacts absent | **Fixed** | README, METHOD, CHANGELOG, `project-facts.yml` and the static export are present; `make facts` fails when `project-facts.yml` is missing (checked); the export loads the committed run and fixture numbers are no longer shipped (`web/src/data/bundled.ts`, `static.ts`). |
| S1 quote grounding measured survivors | **Fixed** | `run/metrics.py` re-checks every kept clue against its narrative and adds trace-dropped quotes to the denominator; `tests/metrics/test_run_metrics.py`. |
| S2 quote not tied to the condition | **Fixed** | `metrics/evidence.py::targeted_test_with_quote_share` requires a shared condition word; `test_targeted_test_quote_must_support_the_condition`. |
| S3 issue base-rate sentence | **Fixed (Q10)** | `web/src/pages/Comparison.tsx` now reads “a random week of the same series hits the same early-issue rule … of the time”. |
| S4 budget steps labelled “trace steps” | **Fixed (Q10)** | `reports/RUN.md` separates “counted agent steps (budget counter)” from “trace records”. |
| S5 no `DEVIATIONS.md` | **Fixed** | `reports/DEVIATIONS.md` carries the run deviations and the fix-up's own. |
| S6 one-word quote is “verified” | **Fixed** | `tools/quotes.py` needs two words or an identifier with a digit, matched on word boundaries; `tests/tools/test_quotes.py` adds the one-word and boundary cases. |
| S7 no intake quote-drop test | **Fixed** | `test_intake_drops_an_invented_quote_before_persisting_it`. |
| S8 manifest check outside `release-check` | **Fixed** | `results-manifest-check` is a `release-check` dependency. |
| N1 stale scaffold messages | **Fixed** | `Makefile` prints “release-check: green”; the screenshot target names the static export. |
| N2 software licences missing | **Fixed (Q11)** | `THIRD_PARTY.md` lists the Python, dev-tool and npm direct dependencies with versions and licences. |
| N3 simulated timestamps in the manifest | **Fixed** | `reports/RUN.md` labels `started_at`/`completed_at` as the simulated run clock and gives the real date; no wall-clock field was added, because that would break byte-identical replay. |
| N4 PII screen scope unstated | **Fixed** | `data/STATS.md` states that only VIN, e-mail, phone and street address are screened. |
| N5 fixture numbers in the production bundle | **Fixed** | `bundled.ts` has no fixture fallback and `StaticDataSource` refuses to serve without an export; the fixtures now load only in the unit tests; `web/src/data/static.test.ts` covers the missing-bundle error. |
| N6 thin recall-linking sample | **Fixed** | README and `RUN.md` say “1 of 6” beside the share. |

Two items deserve emphasis. **B1/B2 are fixed in the code, not in the recorded
numbers**: the Q9 recordings were made with the labels visible, and Q13 may not
call the model (PLAN §2.6), so the recorded run's group and safety rows are
blank rather than replaced with made-up values; Q14 measures them. **B4 is a
stop-condition question under PLAN §10.2** and belongs to the captain, not to a
fix-up worker; Q13 has recorded the finding and the options without editing the
committed data or the review's evidence.
