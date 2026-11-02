# Q6 UI refresh — portfolio overview and evidence desk

## Result and scope

Prepared locally on `codex/portfolio-ui-polish`. The project now opens with the
problem and solution, a real recorded case, a visual evidence/review workflow,
results with visible limits, and entry points into the working tools. No push,
remote addition or publication. The portfolio checkout was read as a reference;
its files were not changed. Source results, recordings, Python code and PLAN.md
were not changed. A digest of every tracked results file matched before/after.

Preview: http://127.0.0.1:8000/?mode=replay#/
Offline output: `dist/field-quality-agents/index.html` (ignored build output).
The local preview is a transient user service, `fqa-portfolio-preview.service`;
stop it with `systemctl --user stop fqa-portfolio-preview.service`.

## Design and structure

The owner chose B, framed-sheet (seed 954241747). Notes, verbatim:
“B — framed layout with a prominent real case (recommended)”. The confirmed
brief was calm and clear, comfortable spacing, portfolio visitors/hiring
reviewers first, English, both themes, desktop and phone.

Design source: the owner's selected portfolio identity, inspected in current
LIVECell Audit and AI Privacy Filter source. Retained its author/header treatment,
blue underline, Inter, neutral surfaces and rounded frame. Three layout
prototypes used the same actual case and results; no other brand was imposed.
DESIGN.md records the selected direction, tokens and screen questions.

Completed views: overview, cases, case detail, issues, issue detail, results,
dashboard, replay and weekly report. Main navigation is Overview / Cases /
Issues / Results. Dashboard, Replay and Report remain accessible in the desktop
tool rail and mobile navigation. Ordinary links preserve deep links and Back.

- Added a problem-first overview and verified report-to-test example, using the
  actual proposal and citations for case 2156317.
- Cases default to readable rows with server-backed pagination. Search, status,
  group and safety filters remain; a board view is available. No API contract
  changed. Full trace, extraction and related-source details are disclosures.
- Replaced the empty issue landing pane with the recorded cluster list. Detail
  retains its chart, citations, memo and investigation draft, with a plain-language
  explanation of the 8D format.
- Results keep the truth-field leakage and unseen classification failure visible;
  complete measurements and denominators remain inspectable. Download exports
  the same comparison the page reads. Fixed the counterexample grouping so the
  committed “pipeline was right” example is actually shown in that section.
- Dashboard prioritizes four operational values and a short activity feed;
  detailed evaluation lives on Results and the full feed remains expandable.
- Weekly narrative precedes detailed measurements. Playback controls work.
- Fixed missing-bundle errors at the normal HTTP entry by defaulting to recorded
  replay. Offline exports still select their real bundle. No invented fixtures
  are used as production evidence.
- Dialogs make the background inert, restore its original state after nested
  overlays, trap keyboard focus and retain Escape/focus restoration.

## Verification

- Strict TypeScript and production Vite build: passed.
- Existing unit suite: 12 files, 52 tests passed.
- Scoped browser suite: 10 tests passed, including approve/override/ask keyboard
  flows with fake API responses, navigation/Back, list/board, search, theme,
  playback and a comparison download checked against its exact source object.
- Axe checks in those tests: seven routes in light desktop and dark mobile.
  This is a scoped automated check, not a claim of complete accessibility.
- Final production screenshot matrix: nine views × three widths (375, 768,
  1440) × two actual themes = 54 viewport captures, plus desktop full-page
  captures. All reviewed via contact sheets and detailed views. No document
  overflow, console errors, failed data states or unloaded fonts.
- Offline `file://` verification: all seven routes, local font and comparison
  download passed; zero HTTP requests and zero script errors.
- `make facts`, `make scan-forbidden`, `make scan-secrets`, `git diff --check`:
  passed. Scans were repeated after staging the scoped files.
- Protected committed result files: byte-for-byte unchanged.

Local review evidence is ignored under `.ui-shots/` and `.taste-skill/`, rather
than replacing the committed scientific evidence or its original screenshots.
Some concurrent CLI screenshot processes received SIGTERM; the final complete
matrix was captured and asserted with the already-installed Playwright runtime.
No dependencies were installed for this redesign.

## Taste and hygiene review

Final source lint: **0 FAIL, 17 WARN**. Final inspectors across nine views:
**0 FAIL, 14 WARN**. Each inspector ran at 1440, 768 and 390px.

Warnings retained deliberately:

- The overview is a public portfolio page: its 40px/30px title follows the
  approved portfolio contract, rather than the generic app-title limit.
- The horizontal mobile navigation deliberately shows a partial next link as a
  scroll cue; its container scrolls, the document does not. Keyboard focus brings
  each link into view. This accounts for the edge-text warnings.
- Detailed IDs, dates, verified-quote labels and source metadata keep 11–12px
  typography; narrative/proposal copy is 14–15px. Dense detail views consequently
  retain tiny-text warnings.
- Controls, inset panels, main panels and full-screen mobile dialogs use distinct
  documented radii; the generic radius-count warning does not reflect accidental
  mixing.
- Source lint recognizes the explicit portfolio blues as framework defaults,
  variable definitions for ID/code monospace, real overlay shadows, the legacy
  class name `eyebrow` (now normal sentence-case metadata), and withheld-value
  dashes. These are intentional, documented uses rather than visual ornaments.

Case-sheet inspector allowances: `heavy-shadow` and `covered-text`, restricted to
that view. A real modal is allowed an overlay shadow and intentionally covers its
inactive background heading. This was visually checked; no resting panel gets
that shadow. No other inspector rule was allowed.

Hygiene findings fixed (line numbers refer to the final files approximately):

- `web/src/App.tsx`: skip link changing the hash route; fixed by focusing main
  without changing the current route. Theme and mode controls remain labelled.
- `web/src/components/Overlay.tsx`: background remained interactive; fixed with
  an inert/background state lock that survives nested modal cleanup.
- `web/src/pages/Overview.tsx`: invalid definition-list metadata; moved to proper
  definition elements. Quote verification checks the actual narrative text.
- `web/src/styles/portfolio.css`: shrinking mobile navigation/status labels and
  a long component string; fixed flex sizing, internal scroll and wrapping.
- `web/src/styles/portfolio.css`: missing grid display after removing the old
  scaffold; fixed. Removed coloured zero deltas and button underlines.
- `web/src/pages/IssueRoom.tsx`: narrow status badge overflow; fixed nonshrinking
  badge and tabular figures. Added the investigation-draft explanation.
- `web/vite.config.ts`: relative font asset in an injected IIFE stylesheet resolved
  against the page root; font is now embedded in the classic script. Local SIL
  OFL licence is included. Both HTTP and offline font loading were verified.

## Performance and remaining limits

Production overview, 390×844, Slow 4G, CPU 4× slowdown: LCP **7.32 s**, CLS **0.07**.
INP was not measured. Buffered long-task observation: three tasks, longest 266ms,
528ms total. The main classic-script request took about 6.61s; the observed
critical request chain was about 7.99s. These are lab observations, not field data.

Slow first load on this profile remains an open issue. The retained offline
classic-script build includes the existing chart stack in its single bundle;
Vite's large-bundle warning remains. The visual redesign did not migrate the
build/export architecture or backend compression. A future performance change
should preserve the verified offline export and measure this baseline again.
The raw DevTools trace was not available as a local file; the measured summary
is recorded in the ignored `.taste-skill/performance-summary.json`.

No configured source remote was present, so no guessed GitHub button was added.
The legacy fixture-only static browser suite still assumes the former default
route and implicit fixture fallback; the scoped new tests use explicit fakes,
and the actual offline export was separately verified. No real model calls ran.

## Deviations and shared files

Owns mainly `web/` and `tests/web/`, consistent with Q6. Shared edits were limited
to DESIGN.md (required to record the selected visual system), `.gitignore`
(local review output), and this lane report. PLAN.md and scientific evidence were
protected. Existing static screenshot tests were not used to overwrite results.
The helper's root-level stack detection says `react=no` because package.json is
under `web/`; the actual retained stack is React with plain CSS, without Tailwind.

## Tool report

Generated from `scripts/tool-report.sh`, with scope/skip reasons filled in:

| Group | Tool | Status | Evidence or reason |
|---|---|---|---|
| Always | Intake rounds | Ran / answered | Confirmed audience, jobs, feel, constraints and structure |
| Always | taste-start.sh + draw.mjs | Ran | Three full sheets; existing palette/type retained |
| Always | Three prototypes + proto-review.sh + inspect.mjs | Ran | A/B/C checked; comparison opened in Lavish |
| Ask | taste-pick.sh and notes | Asked / answered / ran | Owner selected B; notes recorded verbatim |
| Always | taste-check.sh, lint.mjs, inspect.mjs | Ran | All nine views; counts and allowances above |
| Always | shoot.sh | Ran | Supplemented interrupted CLI runs with complete final matrix |
| Always | Hygiene review | Ran | Accessibility, focus, overflow, typography and states reviewed |
| Ask | DESIGN.md update | Ran | Implements the chosen sheet and approved portfolio identity |
| Situational | shadcn/ui | Skipped | Existing React/plain-CSS stack; no Tailwind or install needed |
| Situational | Kokonut UI | Skipped | No matching new utility or Tailwind integration needed |
| Situational | Bklit UI | Skipped | Existing real chart retained; no new chart dependency |
| Situational | Motion | Skipped | No new animation library required; reduced motion preserved |
| Situational | scenes.mjs | Skipped | No scroll-driven scenes |
| Situational | assets.mjs | Skipped | Real project reports/UI supply the imagery; no stock photos needed |
| Situational | DevTools speed check | Ran | Production Slow 4G/CPU 4× results above |
| Situational | reference-image.md | Skipped | No user-supplied screenshot to reproduce; portfolio source inspected |
| Always | Hooks | Skipped | Claude hooks are not registered in this desktop installation; checks ran directly |
