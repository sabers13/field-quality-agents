# Q6 — portfolio utility controls and reusable skill update

## Changes

Replaced the appearance select with adjacent sun/moon buttons, following the
current LIVECell Audit and AI Privacy Filter controls. Each selects its theme in
one click, exposes its pressed state, and retains keyboard focus and the existing
stored preference. The OS preference still applies before an explicit choice.

Data source now opens a compact chooser with direct, described choices, selected
state, a rotating chevron and a 140ms opacity/transform transition. Closing fades
and slides before visibility switches off; only opacity/transform are animated.
Closed content is inert and hidden from assistive technology. Escape, clicking
outside, leaving the control and selecting a choice dismiss it; Escape/selection
return focus to the trigger. The panel anchors to the utility group so its full
width stays inside the phone viewport. Reduced motion removes the transition.

Saved results is disabled with an explanation on the server preview because no
static export is bundled there. The offline export enables its saved results and
excludes server/live modes. This prevents choosing an unavailable source; no data
contract, backend method or evidence changed.

Updated these user-requested skill files outside this Git repository:

- `/home/saber/.agents/skills/portfolio-project-publish/SKILL.md`
- `/home/saber/.agents/skills/portfolio-project-publish/references/portfolio-design.md`

The skill now records accurate secondary skill tags, verified GitHub/contact
actions, sun/moon buttons, accessible smooth disclosures, meaningful loading and
motion, phone-readable diagrams/charts and source inspection. It preserves
project-specific initial-theme policy, layout, stack and publication boundaries.
It does not prescribe this project's dashboard, durations or loading counts to
future projects. `skill-creator/scripts/quick_validate.py` passed. Existing skill
metadata and automatic discovery settings remain intact.

## Verification

UI TWEAK fast gate; existing chosen design retained:

- Strict TypeScript and production build passed. No new dependencies.
- All ten scoped portfolio browser scenarios passed across the main run and
  focused rerun: persisted theme clicks, navigation, case/retry/loading, filters,
  replay, downloads, keyboard source selection and Escape/outside dismissal.
- Existing seven-route light/dark axe checks passed. Four additional open-menu
  axe checks passed at 375px and the comment's 904px width, in both themes.
- Twenty screenshots: 360/375/768/904/1440px × light/dark × closed/open.
  Reviewed all combinations. No document/panel overflow or console errors.
  Standard `shoot.sh` six-shot matrix also passed.
- Offline export refreshed and verified: seven routes, local font, JSON download;
  no HTTP requests or script errors. Skill validator passed.
- Taste source lint: 0 FAIL, 5 WARN (existing overlay shadow declarations and
  metadata selector). Inspector: 0 FAIL, 2 WARN (approved public title size and
  partial next navigation label inside its scrolling container).
- Protected results and PLAN unchanged. Staged secret and forbidden-name scans
  passed across 1,303 tracked files.

Hygiene review fixed the nested native dropdown, keyboard-inaccessible closed
contents, unavailable static-source action and mobile popover anchoring. Sun/moon
buttons have 44px targets and accessible names. The menu uses ordinary buttons
rather than incomplete ARIA menu semantics. It intentionally overlays the page;
only its real overlay has a shadow. No new font, asset, route or data-loading path
was introduced, so no new performance trace was needed. The previously reported
large application bundle remains an open performance limitation.

## Scope

Q6 frontend and browser tests, DESIGN.md and this lane report. The separately
installed skill changes are local files outside this branch. No remote, push or
publication changes. Preview: `http://127.0.0.1:8000/?mode=replay&review=controls#/`.

## orch-ui tool report

Generated with `tool-report.sh` and annotated for the React/plain-CSS web subproject.

| Tool | Status | Evidence or reason |
|---|---|---|
| Intake | Reused | Explicit annotated request resolves this small tweak |
| taste-start.sh + draw.mjs | Ran | Fresh utilities brief/receipt |
| Prototypes + proto-review.sh | Skipped | Existing-design short path; approved B retained |
| taste-pick.sh | Ran | `existing` with current request |
| taste-check.sh / lint / inspector | Ran | Before and after; counts above |
| shoot.sh / browser screenshots | Ran | Six standard and twenty utility captures |
| Hygiene review | Ran | Findings and fixes above |
| Original Claude hooks | Skipped | Not registered; manual checks used |
| DESIGN.md | Updated | Requested theme/menu behavior documented |
| shadcn / Kokonut / Bklit | Skipped | Existing components/plain CSS; no installation needed |
| Motion library | Skipped | Existing native-CSS design contract |
| scenes.mjs | Skipped | No scroll-linked scene |
| assets.mjs | Skipped | No photo/video needed for utility controls |
| DevTools speed trace | Skipped | No changed route, font, heavy asset or data-loading path |
| reference-image.md | Skipped | Annotation identifies an existing control; no image reconstruction |
| Lavish Editor | Skipped | Existing design; review in working browser |
| Project package installs | Skipped | None needed |
| Skill creator validator | Ran | Updated portfolio skill is valid |
