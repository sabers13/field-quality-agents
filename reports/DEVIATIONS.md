# Deviations from `PLAN.md`

`PLAN.md` §1–§11 are frozen. This file records every place where the
implementation departs from the method, and why. Q13 created it from the list
that `reports/RUN.md` used to carry, and added the fix-up's own deviations.

## From the live run (Q9)

1. **Output allowance and reasoning effort.** With `max_tokens = 1024` (the
   PLAN §3 minimum) DeepSeek V4.1 Flash spent the whole allowance on reasoning
   and returned an empty answer (`finish_reason: length`). The request asks for
   8192 tokens and pins `reasoning_effort = "low"`, both verified against the
   endpoint on 2026-11-01. PLAN says "at least 1,024", so this stays inside the
   method. `config/budget.toml` carries the values.
2. **Intake blocked almost every case on mileage/date.** The model listed
   `mileage` and/or `date` as missing for 19 of 20 smoke cases, so those cases
   stopped at intake and never reached analysis; the received date is always
   known. Intake treats only `component` and `symptom` as blocking and records
   the rest in the trace as `note_missing_info` (540 cases).
3. **A 2xx answer with no content crashed the whole run.** Intake and analysis
   treat `BadAnswerError` like unreadable output: the case goes to the engineer
   instead of aborting the batch. No unreadable answer occurred in the main run.
4. **A policy stop exits cleanly.** `fqa run` catches `PolicyStopError`, prints
   its reason and exits 3 after the error has written `reports/STOP.md`.
5. **Reproducibility tooling.** `make all` exports only the `replay` run and
   ends with `scripts/results_manifest.py write`. The record-mode run sits
   outside the manifest because `make all` cannot create it offline; it is
   checked by replaying the same recordings.

## From the Q13 fix-up

6. **The frozen Q9 recordings keep their historical request payload.** The
   review (B1/B2) found the component group and the safety flag in the model
   input. Removing them changes every request, and the committed recordings
   cannot answer a request they were not made for; Q13 may not make new model
   calls (PLAN §2.6). The desk therefore builds a clean payload for every new
   run, and `--legacy-recorded-input` exists only in replay mode to reproduce
   the Q9 bytes. The CLI refuses the flag in record mode, and the manifest and
   metrics record the policy. Consequence: the group and safety metrics are
   withheld for the recorded run rather than recomputed. Q14 measures them on
   unseen reports.
7. **The recorded run's step counters are recomputed.** Adding quote
   verification to intake and the stricter span rule add trace steps, so the
   replay counts 2,556 budget steps and 6,683 trace records where the record
   run counted 2,542 and 6,669. The content files under
   `results/runs/live-2025/` are the replayed ones; its `manifest.json` keeps
   the counters the live run measured, and `scripts/check_facts.py` compares
   the record and replay manifests on everything except the step count.
8. **Quote verification is stricter than "any substring".** A quote must be a
   verbatim span of at least two words, or an identifier with a digit of at
   least four characters, matched on word boundaries (`tools/quotes.py`). The
   plan only says a quote must be verbatim; this adds a minimum meaningful
   span. It is why the evidence shares are no longer 1.0 on the recorded run.
9. **The condition-quote metric ties the quote to the test.** PLAN §7 asks for a
   targeted test that carries "a condition with a verified quote". The metric
   requires the quoted span to share a condition word with the test (allowing
   simple inflection, `vibration`/`vibrates`). A proposal whose verified quote
   is about a different clue no longer counts.

## Publication decision

- **Original public NHTSA narratives (review B4), 2026-11-02.** The owner
  explicitly requested publication of the project repository and website. After
  the B4 finding and PLAN §10.2 hold were presented, the owner clarified that
  the naming rule protects the client/employer identity, permits NHTSA
  attribution, and requested that the rule be changed accordingly. Publication
  therefore retains the original public NHTSA dataset and recorded results
  under this scoped owner exception; no frozen input or result was rebuilt.
  The client/employer identity remains excluded. This resolves the publication
  decision, not the review's technical finding: the PII screen covers VINs,
  e-mail addresses, phone numbers and street addresses, and signature-style
  personal names may remain in the public narratives. The README, review and
  third-party notice retain that limitation. This decision makes no claim that
  the data is fully anonymised or that publication has no legal obligations.
