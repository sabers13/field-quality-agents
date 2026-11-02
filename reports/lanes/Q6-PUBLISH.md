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

Prepared and verified locally; final GitHub commits, Pages deployment and live
checks are recorded here after pushing.

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
| DevTools speed check | Pending live site | Measure the actual Pages delivery after deployment |
| reference-image workflow | Skipped | No image reconstruction |
| Lavish | Skipped | No new design decision |
| Package installs | Skipped | None needed |
