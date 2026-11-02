# Q6 — project repository and portfolio publication

## Authorization and scope

The owner explicitly requested pushing the project repository to GitHub,
replacing the profile link with the project source link, and publishing the page
on the existing portfolio. This supersedes the earlier local-only stopping point
for these specific operations. The owner also clarified that the naming rule
protects the client/employer identity and permits public data-source attribution.
The original-public-data publication decision is recorded in
`reports/DEVIATIONS.md`; the incomplete name screen remains disclosed.

Repositories and destinations:

- Source: `https://github.com/sabers13/field-quality-agents`, default branch main.
- Portfolio: `https://github.com/sabers13/sabers13.github.io`, existing main/Pages deployment.
- Project page: `https://sabersojudi.com/field-quality-agents/`.

## Changes

The overview GitHub button links to the project repository, with an accessible
source-code label. README links to the project. Added public NHTSA, Inter and
Feather credits and retained the font/icon licences in the exported payload.
The portfolio receives the complete static export plus a project-specific SVG
card. Its homepage has one new matching project card; neighboring content and
site configuration are unchanged. The deployed project reads its bundled replay
results and needs no backend, API key or model calls.

The naming-rule clarification is in AGENTS.md. PLAN §§1–11 were not edited.
Historical release/review records point to the new publication decision without
claiming the PII screen removes all personal names or changing scientific facts.

## Verification before push

- Ruff passed; mypy passed on 84 source files; all 358 Python tests passed.
- Strict TypeScript and production build passed; all 52 frontend unit tests
  passed; the focused browser test confirms the project source URL.
- All source-history text blobs scanned for secret patterns: 1,515 checked,
  zero matches. Standard staged forbidden-name and secret scans run before commit.
- Facts check passed: 18 headline rows, 28 facts, all traced to committed results.
- 54 static-subpath screenshots: nine views × 375/768/1280px × both actual themes.
  No API requests, console errors, missing fonts or document overflow. Verified
  real case navigation, playback, exact comparison download, source link and
  credits. Offline data-source options correctly expose saved results only.
- The portfolio copy matches all 613 exported files byte-for-byte; the SVG card
  is one additional file. The homepage card is checked separately on phone and
  desktop before publication.
- Taste lint: 0 FAIL, 3 WARN; inspector: 0 FAIL, 2 WARN. Warnings are existing
  workflow step numbers and the approved public title/scroll-navigation cue.
- Updated `results/MANIFEST.sha256` for distribution changes only (5 added,
  2 removed lines). Its 634 hashes pass `make results-manifest-check`. All
  baseline/replay result hash entries are unchanged. Inputs, recordings, run
  outputs, final-live results and frozen PLAN are byte-identical to the prior
  commit. No `make all`, model calls or scientific reruns were needed.

## Publication receipt

- Source main was pushed at `64dae4ce0ec476d8ce9a992857c64ed68e3b9c9f`.
  The existing `v1.0.0` tag was also pushed without moving it.
- Portfolio main was pushed at `66fc679c4e0898f76f26a9ecde2ec37b97fce027`.
  [Pages run 41400644943](https://github.com/sabers13/sabers13.github.io/actions/runs/41400644943)
  completed successfully, with its head SHA matching the portfolio commit.
- `https://sabersojudi.com/field-quality-agents/` is live. The served HTML,
  application script, data bundle, credit notice and SVG card each returned 200
  and matched the committed portfolio bytes. The public homepage contains the
  project card and its project link.
- Repeated the nine-view / two-theme / three-width verification against the
  public URL: 54 screenshots; correct GitHub source link, real case, playback,
  exact JSON download and credits; no API requests, script/console errors or
  document overflow. The published demo is the real recorded static export.
- NHTSA remains credited as the public data source. The client/employer naming
  restriction remains in force. Original dataset/results were not rewritten.

The follow-up receipt commit changes this report only; the verified website
payload and scientific results remain the same.

## Live performance observation

Chrome reload trace on the public Pages URL, 390×844 mobile, Slow 4G, CPU ×4:
FCP 0.83s, LCP 1.68s, CLS 0.00. The observed LCP/CLS meet 2.5s/0.1 thresholds,
but this is a warm-cache reload (three of four responses were cached), not a cold
network benchmark or field measurement. Five long tasks totalled 1,095ms, with
634ms maximum. INP was not measured. The large bundled replay data and application
remain the existing cold-load limitation; this publication does not claim to fix
their architecture. Trace and summary are in ignored `.taste-skill/` files.

## orch-ui tool report

| Tool | Status | Evidence or reason |
|---|---|---|
| Intake | Reused | Explicit publication request, approved style |
| taste-start.sh + draw.mjs | Ran | Fresh publication receipt |
| Prototypes / proto-review.sh | Skipped | Existing-design short path |
| taste-pick.sh | Ran | Existing style retained |
| taste-check / lint / inspector | Ran | Static subpath, counts above |
| Playwright screenshots | Ran | 54 project screenshots; homepage card review |
| shoot.sh | Prior pass retained | Same page design; actual theme/subpath matrix rerun |
| Hygiene review | Ran | Correct source URL, credits, static-only mode, card alt/link |
| Original Claude hooks | Skipped | Not registered in this environment |
| DESIGN.md | Updated | Explicit publication authorization and source URL |
| shadcn / Kokonut / Bklit / Motion | Skipped | Existing stack; no component/dependency change |
| scenes.mjs | Skipped | No scroll scene |
| assets.mjs | Skipped | Project diagram is repo-native SVG, no stock media |
| DevTools speed check | Ran | Public Pages reload trace; warm-cache limitation disclosed above |
| reference-image workflow | Skipped | No image reconstruction |
| Lavish | Skipped | No new design decision |
| Package installs | Skipped | None needed |
