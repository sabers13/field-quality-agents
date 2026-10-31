# Design system: field-quality-agents

A calm, data-dense operations surface. The dashboard is read for long stretches
by engineers and reviewers: prefer legible numbers, quiet surfaces and clear
status over decoration. No gradients, glass effects, oversized headings or
animated backgrounds. Colour carries status, not brand.

The implementation lives in `web/src/styles/tokens.css` and
`web/src/theme/echartsTheme.ts`; Q6 must use these tokens rather than inventing
local colours.

## Principles

1. **Numbers first.** Tabular figures, right-aligned numeric columns, units in
   the label or a quiet suffix.
2. **One accent.** Blue is the interaction accent. Status colours are reserved
   for status.
3. **Dense, not cramped.** 8 px spacing grid; 13 px body text; compact rows.
4. **Explain in place.** A trace step, quote or chart annotation carries its
   own reason; no tooltip-only meaning.
5. **Accessible by default.** WCAG AA text contrast in both themes, visible
   focus rings, status never conveyed by colour alone (label or icon too).

## Tokens

Use CSS custom properties on `:root` (light) and `[data-theme="dark"]`.
`prefers-color-scheme: dark` sets the same dark values when no explicit theme
is chosen.

### Light

| Token | Value | Use |
|---|---|---|
| `--bg-canvas` | `#f6f7f9` | app background |
| `--bg-surface` | `#ffffff` | cards, panels |
| `--bg-subtle` | `#eef1f4` | table headers, wells |
| `--bg-raised` | `#ffffff` | menus, dialogs |
| `--border` | `#d8dee5` | default border |
| `--border-strong` | `#b6c0cb` | focus/hover border |
| `--text-primary` | `#1b2430` | headings, values |
| `--text-secondary` | `#4d5a68` | body |
| `--text-muted` | `#6f7c8a` | labels, metadata |
| `--accent` | `#1f5fbf` | links, primary action |
| `--accent-hover` | `#184c99` | hover |
| `--accent-soft` | `#e8f0fb` | selected rows, active nav |
| `--focus-ring` | `#1f5fbf` | 2 px outline, 2 px offset |

### Dark

| Token | Value | Use |
|---|---|---|
| `--bg-canvas` | `#0f141a` | app background |
| `--bg-surface` | `#161d25` | cards, panels |
| `--bg-subtle` | `#1d2630` | table headers, wells |
| `--bg-raised` | `#202a35` | menus, dialogs |
| `--border` | `#2c3742` | default border |
| `--border-strong` | `#43505d` | focus/hover border |
| `--text-primary` | `#e8edf2` | headings, values |
| `--text-secondary` | `#b3bec9` | body |
| `--text-muted` | `#8794a1` | labels, metadata |
| `--accent` | `#6ea8ff` | links, primary action |
| `--accent-hover` | `#8bbaff` | hover |
| `--accent-soft` | `#1b2a3d` | selected rows, active nav |
| `--focus-ring` | `#6ea8ff` | 2 px outline, 2 px offset |

### Status colours

Each status has a foreground, a soft background and a border. Never rely on the
dot alone: render the status label beside it, and use the same label text in
exports and screen readers.

| Status | Light fg | Light bg | Light border | Dark fg | Dark bg | Dark border |
|---|---|---|---|---|---|---|
| new | `#44515f` | `#eef1f4` | `#d8dee5` | `#b3bec9` | `#1d2630` | `#2c3742` |
| in agent | `#1f5fbf` | `#e8f0fb` | `#bcd2f2` | `#8bbaff` | `#1b2a3d` | `#2b4770` |
| needs engineer | `#8a4b00` | `#fdf1df` | `#f0d3a4` | `#f0b45e` | `#2d2415` | `#5a4627` |
| decided | `#17663a` | `#e7f5ec` | `#b7ddc6` | `#6fd39a` | `#15281e` | `#2a4a36` |
| issue | `#a32020` | `#fcecec` | `#efc2c2` | `#ff8d8d` | `#2e1919` | `#5a2b2b` |

CSS names: `--status-new-fg/bg/border`, `--status-in-agent-*`,
`--status-needs-engineer-*`, `--status-decided-*`, `--status-issue-*`.

## Type

System UI stack for text; a monospace stack for ids, code, tool arguments and
tabular figures where alignment matters:

```css
--font-sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
  "Helvetica Neue", Arial, sans-serif;
--font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas,
  "Liberation Mono", monospace;
```

Scale (rem at 16 px root):

| Token | Size / line-height | Weight | Use |
|---|---|---|---|
| `--text-2xs` | 11 / 14 px | 500 | dense table metadata |
| `--text-xs` | 12 / 16 px | 500 | labels, badges |
| `--text-sm` | 13 / 18 px | 400 | body, table cells |
| `--text-md` | 14 / 20 px | 400 | default body |
| `--text-lg` | 16 / 24 px | 600 | card title |
| `--text-xl` | 20 / 28 px | 600 | page section title |
| `--text-2xl` | 24 / 32 px | 650 | page title |
| `--text-kpi` | 28 / 32 px | 650 | KPI value |

Rules: page title at most `--text-2xl`; KPI values use `font-variant-numeric:
tabular-nums`; no text below 11 px; uppercase labels only at 11-12 px with
`letter-spacing: 0.04em`.

## Spacing, radius, elevation

Spacing scale: `4, 8, 12, 16, 24, 32, 48` px. Component padding uses 8/12/16;
page gutters 24 px desktop, 16 px tablet, 12 px phone.

Radii: `--radius-sm: 4px` (badges, inputs), `--radius-md: 6px` (cards,
buttons), `--radius-lg: 10px` (dialogs). No pill-shaped cards.

Elevation: one subtle shadow only for raised surfaces:
`0 1px 2px rgb(16 24 40 / 0.06), 0 1px 3px rgb(16 24 40 / 0.10)`. Dark theme
uses borders instead of stronger shadows.

Motion: 120-160 ms ease-out for hover/expand; no looping animation except a
2 px live pulse that stops under `prefers-reduced-motion: reduce`.

## Layout

### Desktop (>= 1024 px)

- Left navigation rail: 232 px fixed, `--bg-surface`, 1 px right border.
  Product name at top (16 px semibold), then nav items:
  Command centre, Case board, Issue room, Before vs after, Replay, Weekly
  report. Each item is a 36 px row with icon + label; active uses
  `--accent-soft` and a 2 px left accent bar.
- Top bar: 56 px, breadcrumb/page title left; mode switch (Live / Replay /
  Static), theme toggle and a live-status dot right.
- Content: fluid, 24 px gutters, max-width 1600 px. Dense grids use
  `repeat(auto-fit, minmax(220px, 1fr))` for KPI tiles; the case board is a
  horizontal 6-column kanban that scrolls inside its own region, never the
  page.
- Secondary detail (case trace, issue evidence) opens as a 480-640 px right
  sheet on desktop; keyboard focus moves into it and returns on close.

### Tablet (640-1023 px)

Nav rail collapses to a 64 px icon rail with accessible labels; KPI grid is
2 columns; kanban becomes 2 visible columns with horizontal scroll and a
column jump control.

### Phone (<= 639 px, tested at 360 px)

- Bottom navigation, fixed, 56 px + `env(safe-area-inset-bottom)`, five items:
  Command, Cases, Issues, Compare, Report. Replay is reachable from Command or
  the page menu. Icons 20 px, labels 11 px; active item uses accent text and a
  3 px top indicator.
- Top bar 52 px with page title and overflow menu. No left rail.
- Content gutters 12 px. KPI tiles stack 1 per row. Kanban becomes a single
  column with a sticky status filter (segmented control). Trace and case detail
  use full-screen sheets. Tables become definition lists; never require
  horizontal page scroll.
- Touch targets at least 44 x 44 px; approve/override/ask buttons stack full
  width in a sticky action bar.

## Components

### KPI tile

Quiet card: label (12 px, muted, optional info tooltip), value (`--text-kpi`,
tabular), unit or comparison beneath (12 px). Optional sparkline 32 px high
with no axes. Status accent only when the KPI itself is a status (e.g. open
issues). Delta uses decided/issue colours plus an arrow and sign, never colour
alone. Padding 16 px; min-height 96 px; no icons larger than 16 px.

### Kanban card

`--bg-surface`, 1 px border, radius 6 px, padding 12 px, 8 px gap. Top row:
case id in mono (12 px muted) and status dot+label. Title: 2-line clamp of the
component/symptom summary. Meta row: make, model, year, group as 12 px muted
text. Bottom row: safety flag (icon + "Safety"), evidence count, human touches,
relative received time. A 3 px left stripe in the status colour. Hover raises
the border to `--border-strong`; focus-visible gets the focus ring. Dragging is
not required in Q6 (actions are explicit buttons), but a card must expose its
status to assistive tech.

### Trace step

A vertical timeline: 24 px rail with a 7 px dot per step, 1 px connector. Each
row: step number and agent badge (supervisor/intake/analysis/issue/report/
human/tool) on the first line; action text (13 px); optional tool call in a
mono chip (`similar_cases({"text": "..."})`); result summary; reason in
`--text-secondary`; duration and tokens right-aligned in 11 px muted. Expand for
raw JSON in a `<pre>` with a copy button. A human checkpoint row uses the
needs-engineer colour and shows the decision when resolved. Never truncate the
reason without an expand control.

### Evidence highlight

Inline quote: `<mark>` with a soft yellow that works in both themes
(`#fff3c4` light / `#3a3216` dark), 1 px underline offset, no rounded bubble.
Verified quotes carry a small check and a source link; unverified quotes are
struck through and labelled "not verified" and must not be counted as evidence.
A quote card shows the verbatim quote (13 px, max 6 lines then expand), source
type + id in mono, and the case/recall/investigation link. Citation validity is
always visible; a broken citation uses the issue colour and an explanatory
label.

### Chart (ECharts theme)

`echartsTheme.ts` exports `fqaTheme` and `fqaDarkTheme`:

- palette: blue `#1f5fbf`, teal `#0f766e`, amber `#b45309`, violet `#6d4aff`,
  green `#17663a`, red `#a32020` (dark equivalents: `#6ea8ff`, `#4fd1c5`,
  `#f0b45e`, `#a78bfa`, `#6fd39a`, `#ff8d8d`);
- background transparent (the card supplies `--bg-surface`);
- axis lines `--border`, split lines 1 px dashed at 50% opacity, axis labels
  11 px `--text-muted`, no axis name unless needed;
- line width 2 px, symbol size 5, no area fill except a 10% opacity band for
  confidence intervals;
- tooltip: surface background, 1 px border, 12 px text, tabular numbers;
- legend: 12 px, top-right, inactive uses muted text;
- the spike-rule threshold is a 1 px dashed annotation in the issue colour with
  a label "Poisson 99.9% threshold"; counts are integers;
- dark theme swaps text/axis colours only, never the status palette meaning;
- respect `prefers-reduced-motion`; no chart animation longer than 200 ms and
  none in static export screenshots.

### Buttons, badges, tables

Primary button: accent fill, white text, 32 px height, 6 px radius. Secondary:
surface, 1 px border. Destructive is not offered (no close/scrap/charge action
exists in the product). Badges: 11 px uppercase, 4 px radius, status soft
background + foreground. Tables: 40 px rows, sticky header in `--bg-subtle`,
right-align numbers, mono ids, zebra striping off, 1 px row borders.

## Content and tone

- Labels are plain nouns: "Cases in", "Human touches / case", "Cost / case",
  "NTF without evidence".
- Show the time window beside every KPI and the source file in the drill-down.
- A simulated engineer is labelled "Simulated engineer" everywhere, including
  tooltips, exports and screenshots.
- Empty states say what will appear and which pipeline produces it; no jokes,
  no mascots.
- Number formatting: integers with thousands separators; money in USD with 2
  decimals for spend, 4 decimals for per-case cost when below USD 0.01;
  percentages to 1 decimal; dates as `YYYY-MM-DD`; relative times only in
  feeds, with an absolute timestamp on hover or in the accessible label.

## Acceptance checks for Q6/Q10

- 360 px: no horizontal page scroll; bottom nav reachable; action bar visible.
- Light and dark: all text meets AA; status labels readable without colour.
- Keyboard: tab order follows the page; approve/override/ask reachable; sheets
  trap focus and restore it.
- Screenshots at 360 and 1280 px, light and dark, stored under
  `results/screenshots/` by Q10.
