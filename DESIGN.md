# Field quality agents — portfolio and evidence desk

## Intent and audience

UI INIT decision, 2026-11-02: make the project understandable to portfolio visitors
and hiring reviewers, then let them inspect the working evidence desk. Calm and
clear, with comfortable spacing. English, desktop and phone, light and dark.
Apple HIG level: principles-only.

The opening answers: what problem is being solved, what was built, and what can
I inspect next? It explains a returned part passing a standard test while an
intermittent fault remains unexplained. No measured savings or production-readiness
claim is implied. Public NHTSA complaint reports stand in for returned-part reports.

## Chosen direction

Owner chose prototype B: **framed-sheet**, seed 954241747.
Owner notes, verbatim: “B — framed layout with a prominent real case (recommended)”.
Use the sheet's single tonal frame and shared edges. The portfolio references
(current LIVECell Audit and AI Privacy Filter source) supply the palette, header,
font and rounded surfaces; those deliberate portfolio choices override the generic
Taste defaults. No gradients, glass or ornamental animation.

Reference screen: overview. Information priority: problem and solution → actual
case with verified evidence → measured results and visible limitations.
Signature: a complaint-to-evidence-to-test trail using the real recorded case.

## Structure and disclosure

- Overview, `#/`: problem, real example, results with caveats, what was built.
- Cases, `#/cases`: browse reports, search and filter; open a case sheet.
- Case sheet, `#/cases/:id`: report, proposal, recorded human decision first;
  agent trace, extraction and related sources in accessible disclosures.
- Issues, `#/issues`: recurring-problem clusters, evidence and draft reports.
- Results, `#/compare`: comparison, evaluation caveats, examples and full metrics.
- Dashboard, `#/dashboard`: operational metrics, short recent activity and links.
- Replay, `#/replay`: working playback with play/pause, speed and scrubber.
- Weekly report, `#/report`: report narrative, counts and detailed measurements.

Existing routes remain. `#/command` aliases the dashboard. Unknown routes open
the overview. Modes and the recorded/bundled data contracts remain unchanged.
HTTP defaults to recorded replay; an offline export uses its bundled results.
No invented fixtures ship as project evidence.

## Portfolio identity and shell

Header: author link in portfolio blue, four ordinary route links (Overview,
Cases, Issues, Results), project badge and Back-to-portfolio. Active route has a
thin blue underline. No tab ARIA for ordinary navigation. Utilities offer theme
and recorded/static/live data controls. A detached desktop tool rail links to
Dashboard, Replay and Weekly report. On smaller screens all destinations become
one horizontally scrollable navigation row; the document itself never scrolls
sideways. No duplicate mobile bottom bar. Header stays sticky without obscuring
focus or content. Sheet maximum width 1320px; outer gutter 24px desktop, 16px phone.

## Design tokens

`web/src/styles/tokens.css` is the implementation authority. Portfolio tokens:

| Role | Light | Dark |
|---|---|---|
| Canvas | #f9fafb | #030712 |
| Surface | #ffffff | #111827 |
| Subtle inset | #f3f4f6 | #1a2232 |
| Raised | #ffffff | #1a2232 |
| Border | #e5e7eb | #374151 |
| Strong border | #9ca3af | #6b7280 |
| Primary ink | #111827 | #f9fafb |
| Secondary ink | #374151 | #d1d5db |
| Muted ink | #626b78 | #a6afbd |
| Accent / focus | #2563eb | #60a5fa |
| Accent hover | #1d4ed8 | #93c5fd |
| Accent soft | #eff6ff | #172b49 |
| On primary | #ffffff | #111827 |

Retain existing semantic status foreground/background/border tokens. Status is
always accompanied by a label or icon. Quote highlight: #fff3c4 / #3a3216.
Overlay scrim: rgb(3 7 18 / 0.48). No coloured decoration on zero deltas.

Font: locally hosted Inter variable, licensed under SIL OFL, `font-display: swap`.
System fallback; monospace only for opaque IDs and actual tool/code payloads.
Body 15px / 1.6; explanatory lead 18px / 1.65; metadata 12–13px, no text under
11px; operational page title 28px / 1.2; public overview title 40px desktop,
30px phone / 1.15. Section titles 22px, subsection titles 16px, key values 30px.
Headings 500–600, tracking -0.03em; sentence case. Tabular numeric columns.

Spacing: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64px. Component spacing 12/16/24;
public section gap 48px. Radii: small 8px (controls), medium 16px (insets), large
24px (panels), shell 32px, pill 999px. Overlay shadow only:
0 12px 40px rgb(3 7 18 / 0.16). Resting surfaces use tone steps, no shadows.
Duration 140ms ease-out for hover feedback; reduced motion disables transitions.
No new motion library or dependencies are needed.

Polish request, 2026-11-02: retain the selected layout and add the portfolio's
skill chips, GitHub and Hire Me actions. Skill labels describe implemented work;
GitHub links to the verified public profile until a project repository exists.
Hire Me links to `https://sabersojudi.com/#contact`.

Motion stays native CSS, matching the inspected reference sources: 140ms feedback,
420ms ease-out for one page group or a sheet opening, and 1200ms ease-in-out for
loading opacity. Loading repeats four times, then settles; no endless decorative
motion. Only opacity and transform animate. No staggered entrance per card or
counting-up evidence values. Reduced motion removes all motion. A lightweight
opening state appears before the application bundle; shape placeholders reserve
space for cases, lists and metrics while data loads. The workflow is a connected
HTML trail so its text stays readable at phone widths and browser zoom.

## Components and responsive behavior

All actions use anchors or buttons. Keyboard focus visible, labelled form fields,
44px touch targets. Dialogs retain focus management, Escape, and focus restoration.
Case summaries are readable rows by default, with a board view available for
workflow inspection. Empty/loading/error states preserve headings and explain
recovery. Very long reports and IDs wrap without widening the document.

Results always retain denominators and confidence intervals. Introductory values
are rendered from the existing result-backed data source. Essential failures
(original truth-field leakage, later classification failure, simulated engineer,
and proposed rather than performed tests) stay visible, never buried in details.
Full raw payloads may be disclosed. Replay must never trigger real model calls.

## Verification and boundaries

Review at 375, 768 and 1440px in both themes, and verify 360px for the existing
contract. Exercise navigation, browser history, theme control, filters, case-sheet
keyboard flow, playback and downloads. Run Taste lint/inspector, screenshot loop,
hygiene review, strict build, existing unit tests and scoped recorded-browser tests.
Protected: PLAN.md, all committed results and recordings, backend method and data.
This task ends at a local preview; no push, remote creation or publication.
