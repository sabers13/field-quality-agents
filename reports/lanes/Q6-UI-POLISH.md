# Q6 — portfolio motion and loading polish

## Result

Kept the approved B framed-sheet layout. Added Python, LangGraph, DuckDB,
React, TypeScript and Evaluation skill chips; GitHub and Hire Me buttons; a clear
connected report → evidence → engineer workflow; and chart typography and spacing
that follow the portfolio tokens. The case has its own prominent exploration
button. Phone actions wrap as complete buttons without shrinking their icons.

Added an opening screen in the initial HTML, case/list/metric/content skeletons,
and brief page, sheet, disclosure and action feedback. Motion uses only transform
and opacity, respects reduced motion, and loading pulses settle after 4.8 seconds.
No dependency was installed. Data values do not animate or count up.

Inspected the current public GitHub sources, rather than relying on screenshots:

- [LIVECell overview and actions](https://github.com/sabers13/sabers13.github.io/blob/main/livecell-audit/index.html),
  [styles and motion](https://github.com/sabers13/sabers13.github.io/blob/main/livecell-audit/assets/review.css),
  and [interaction code](https://github.com/sabers13/sabers13.github.io/blob/main/livecell-audit/assets/review.js).
- [AI Privacy Filter overview](https://github.com/sabers13/sabers13.github.io/blob/main/ai-privacy-filter/index.html)
  and [styles](https://github.com/sabers13/sabers13.github.io/blob/main/ai-privacy-filter/assets/page.css).

The GitHub repository inventory contains no Field quality agents repository.
The button therefore says GitHub and links to the verified `sabers13` profile,
with an accessible name identifying it as a profile. Hire Me links to the existing
portfolio contact section. No repository was created and nothing was published.

## Validation

- Strict TypeScript and production build passed; 52 unit tests passed.
- Browser suite: all 13 tests passed with exit status 0. Includes keyboard approve/override/ask,
  stream failure, case navigation, filters, replay, downloads, real portfolio
  destinations, held-request loading and retry, opening state and reduced motion.
- Axe checks cover seven routes in light desktop and dark phone configurations.
  Contrast checks use reduced motion so they measure settled colours rather than
  intermediate opacity during the short page entrance.
- 54 production screenshots: nine views × 375/768/1440px × both actual themes.
  Reviewed all viewport combinations. No page overflow, font failures or console
  errors. Twenty additional captures inspect opening, case and metric loading,
  workflow connectors and the chart at 375/1440px in both themes. The standard
  `shoot.sh` six-shot matrix also passed after motion was added.
- Offline export refreshed and verified at `file://`: seven routes, local font,
  comparison download, no HTTP requests or script errors.
- Facts check passed: 18 headline rows and 28 facts traced to committed results.
  `git diff HEAD -- results/ PLAN.md` is empty. No model calls or new recordings.
- Staged secret and forbidden-name scans passed: 1,301 tracked files checked.

## Taste and hygiene review

Short path: the request is a polish of the existing chosen design, so the prior
intake and B selection remain authoritative. A fresh taste-start receipt and
`taste-pick.sh existing` record the requested additions. No new prototype choice
was needed. Static layout was checked before adding motion, then rechecked.

Final source check: **0 FAIL, 16 WARN** across the six main changed sources.
These are the approved portfolio blue, existing overlay-only shadows, existing
metadata class, and workflow step numbers. The step numbers express the three
ordered workflow stages rather than project measurements. Overview inspector:
**0 FAIL, 2 WARN**. The public project title intentionally uses the approved 40px
size; the partial next navigation label is a horizontal-scroll cue inside the
navigation region, not document overflow. All nine final per-view checks passed:

| View | Inspector FAIL | Inspector WARN |
|---|---:|---:|
| Overview | 0 | 2 |
| Cases | 0 | 1 |
| Case detail | 0 | 3 |
| Issues | 0 | 1 |
| Issue detail | 0 | 1 |
| Results | 0 | 2 |
| Dashboard | 0 | 1 |
| Replay | 0 | 2 |
| Weekly report | 0 | 1 |

The 14 inspector warnings total include repeated scroll-navigation cues, existing
11–12px metadata/axis labels allowed by DESIGN.md, and the case overlay's
documented corner-radius hierarchy. Main report and proposal text remain larger.
Only the real case overlay uses the inspector's existing `heavy-shadow` and
`covered-text` exceptions because it intentionally covers an inert background.

Hygiene findings fixed:

- `web/src/pages/Overview.tsx`: replaced the SVG whose connectors and arrowheads
  passed beneath its nodes with a semantic connected HTML trail. Text now retains
  its actual readable size on phones and at zoom.
- `web/src/pages/IssueRoom.tsx`: moved the threshold explanation to the existing
  caption, contained axis labels and confined tooltips to the plot.
- `web/src/theme/echartsTheme.ts`: replaced stale chart fonts/colours with the
  documented Inter and light/dark portfolio palette; raised axis labels to 12px.
- `web/src/styles/portfolio.css`: prevented phone button text/icon compression,
  preserved loading space, and limited animation to transform/opacity with a
  reduced-motion alternative.
- `web/index.html`: supplied an immediate labelled opening state, theme-aware
  colours, storage-safe theme restoration and a JavaScript-disabled explanation.
- `web/src/components/States.tsx`: loading shapes are hidden from assistive tech;
  one live status announces the actual operation. Error recovery remains usable.

The hierarchy still leads with the problem and a real report. Shared sheet edges,
quiet surfaces and the final blue engineer-review step preserve the chosen face.
The new trail is useful at its real phone size; no unrelated stock artwork or
invented data was introduced. Case overlays intentionally cover an inert
background and retain their approved shadow and focus management.

## Performance and open issues

Production overview, Chrome mobile 390×844, Slow 4G, CPU ×4:

| Measurement | Observed | Assessment |
|---|---:|---|
| First contentful paint | 0.73s | Opening screen appears before the app bundle |
| Largest contentful paint | 7.62s | Above 2.5s; existing large bundle remains the main limit |
| Layout shift | 0.00 | Within 0.1 |
| Long tasks | 5; total 500ms; maximum 201ms | Lab observation |
| INP | Not measured | No representative interaction in this load trace |

The classic single application bundle is 978.01kB raw / 333.95kB gzip. The prior
build was about 970kB raw; no animation library was added. The preview server
transfers the uncompressed bundle, so the largest content still arrives late.
The previous slow-phone measurement was 7.32s LCP / 0.07 CLS; this pass supplies
an early opening screen and reserves loading space, but does not claim a speed
fix. Bundle splitting or serving compression remains separate work. The raw trace
and state/screenshot receipts are in ignored `.taste-skill/` and `.ui-shots/`.

## Scope and deviations

Edited Q6-owned frontend and browser tests, plus `DESIGN.md` and this lane report.
The design additions record the user's explicit request for motion, loading and
portfolio actions. Existing DESIGN.md requires native CSS without new libraries;
this also matches the inspected reference implementations. No backend, method,
results, secrets, remote configuration or publication changes. Historical
screenshot-generation specs that overwrite committed results were not run.

## orch-ui tool report

Generated with `scripts/tool-report.sh`, then annotated for the `web/` subproject
(the helper's repository-root package detection incorrectly reports React=no).

| Group | Tool | Status / evidence | Reason if skipped |
|---|---|---|---|
| Always | Intake | Reused approved answers and current polish request | Existing-design short path; no unanswered design decision |
| Always | taste-start.sh + draw.mjs | Ran; fresh receipt and polish brief | |
| Always | New prototypes + proto-review.sh | Skipped; prior B retained | Explicit polish, existing DESIGN.md; short path |
| Ask | Pick + notes | Ran `taste-pick.sh existing` | Existing selection already authorized |
| Always | taste-check.sh / lint.mjs / inspect.mjs | Ran before and after changes | |
| Always | shoot.sh / Playwright screenshots | Ran; six-shot script plus 54-screen matrix and 20 state captures | |
| Always | Hygiene review | Ran; findings fixed above | |
| Always | Original Claude hooks | Skipped; manual workflow checks ran | Not registered in this desktop environment |
| Ask | DESIGN.md update | Ran; requested actions/loading/motion documented | User explicitly requested these additions |
| Situational | shadcn/ui | Skipped | Existing React/plain-CSS components; no Tailwind or install needed |
| Situational | Kokonut UI | Skipped | No matching component or dependency needed |
| Situational | Bklit UI | Skipped | Existing ECharts plot retained and corrected |
| Situational | Motion (`motion/react`) | Skipped | DESIGN.md native-CSS contract; no animation dependency needed |
| Situational | scenes.mjs | Skipped | No scroll-linked scene |
| Situational | assets.mjs | Skipped | Source-backed interface graphics; no photos or video needed |
| Situational | DevTools speed check | Ran | Production load trace recorded after opening-state change |
| Situational | reference-image.md | Skipped | GitHub source references supplied, no image matching request |
| Situational | Lavish Editor | Skipped this pass | No new design choice; review occurs in the working browser |
| Ask | Project installs | Skipped | No packages installed |
