# Design — antijudolinator

A locked design system for this app. Every page redesign reads this file before
emitting code. Extend or amend it when the system needs to grow; don't override per page.

## Genre
Editorial: the "Newsprint ledger". The app reads donations before they air, so the pages
are a newspaper front page and its ledgers.

## Macrostructure family
- App pages (queue, history, settings, admin): **Ledger**. Masthead, then a serif page head with a one-line dek,
  then content under a double rule. Lists of records are ruled tables (`.ledger`) that collapse to stacked rows
  under 40rem. Decisions (queue items) are `article.story` blocks, not cards.
- Login: **Split front page**. Centred nameplate, edition line, lead story + example donations on the left,
  sign-in column on the right (form first on phones).

## Theme
Tokens live in `app/static/tokens.css`. Light mode is the default; dark follows the OS
preference unless the user picks one with the masthead toggle (stored in `localStorage.theme`).

| token | light | dark |
| --- | --- | --- |
| `--color-paper` | oklch(96.5% 0.012 85) cream | oklch(18.5% 0.008 60) warm black |
| `--color-ink` | oklch(22% 0.012 60) | oklch(91% 0.014 85) |
| `--color-ink-2` | oklch(43% 0.014 60) | oklch(71% 0.014 80) |
| `--color-rule` | oklch(78% 0.018 75) | oklch(35% 0.012 60) |
| `--color-accent` | oklch(50% 0.175 27) red ink | oklch(68% 0.16 28) |
| `--color-ok` | oklch(45% 0.1 150) | oklch(74% 0.11 150) |

The accent means "blocked / gambling / destructive" and is used for nothing else.

## Typography
- Display: Newsreader 700–800, roman only (no italic headings)
- Body: Public Sans 400/600
- Mono: IBM Plex Mono for amounts, dates, patterns, URLs (`tabular-nums`)

## Rules and shape
Hairline rules separate items, a double heavy rule opens a section. Corners are 2px. No shadows, no cards.

## Motion
Hover tint (120ms, `--ease-out`) and a 1px press nudge. Nothing else. Reduced motion removes both.

## Microinteractions
- Silent success: copy buttons swap their label to "Copied" for 2s; no toasts.
- Verdicts are `.stamp` labels (Gambling / Clean / Active / Disabled).
- Focus ring: 2px `--color-focus`, offset 2px, never animated.

## CTA voice
- Primary: ink fill (`.btn-primary`). Destructive / confirm-gambling: red-ink fill (`.btn-danger`).
- Secondary: 1px ink outline (`.btn`). Tertiary: text-only (`.btn-quiet`).

## Out of scope
`overlay.html` + `overlay.css` are the user's stream graphic, styled by their own template. They don't use this system.
