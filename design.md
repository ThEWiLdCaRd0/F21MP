# Design

Visual language: dark, terminal/hacker-toolkit aesthetic. Readable and calm at rest,
with color reserved for role identity and status (not decoration).

## Theme

Single dark background theme for the whole app. Role choice (Red/Blue) only changes an
accent color, not the whole theme — keeps the four-pane level view legible and
consistent regardless of which side you're playing.

| Token | Value | Use |
|---|---|---|
| `--bg` | `#0a0e14` | App background |
| `--surface` | `#10151d` | Panel backgrounds (sidebar, terminal, victim PC, hints) |
| `--surface-border` | `#263042` | Panel borders/dividers (neutral, non-hover state) |
| `--text` | `#e6edf3` | Body text |
| `--text-muted` | `#8b949e` | Secondary text, labels |
| `--red-accent` | `#ff2d55` | Red Team role, attack actions, danger states |
| `--red-accent-dim` | `#3d0d18` | Red team subtle backgrounds/badges |
| `--red-glow` | `rgba(255,45,85,0.45)` | Box-shadow glow on hover for red-team elements |
| `--blue-accent` | `#2ee6ff` | Blue Team role, defense actions, info states |
| `--blue-accent-dim` | `#062b36` | Blue team subtle badges |
| `--blue-glow` | `rgba(46,230,255,0.45)` | Box-shadow glow on hover for blue-team elements |
| `--success` | `#39ff88` | Win condition met, correct defense |
| `--warning` | `#ffcc33` | Hint unlocked, partial progress |

Rule: exactly one accent color is "live" at a time — whichever role the player is
currently in. Don't mix red and blue accents on screen simultaneously outside the
landing page's role-selection moment.

**Cyber styling pass:** background carries a faint 32px cyan grid (`background-image`
linear-gradient lines at 5% opacity — pure CSS, no image asset). Interactive
surfaces (role cards, level rows, nav buttons) sit flat at rest and gain a colored
`box-shadow` glow (`--red-glow` / `--blue-glow`) plus an accent border on hover —
contrast is a hover/interaction cue, not a constant background effect. Headings and
role labels use JetBrains Mono (not Inter) for a terminal feel; body copy stays Inter.

## Typography

- **UI text**: Inter (Google Fonts, OFL license, free) — clean, highly legible sans for
  objectives, hints, dashboard, buttons.
- **Terminal & code/log text**: JetBrains Mono (OFL license, free) — used in the
  terminal pane, victim PC file/log views, and any inline command references in the UI.
- Scale: 14px base for terminal/code, 15px base for UI body text, 1.25 modular step for
  headings (h1 24px / h2 19px / h3 16px). No more than 3 heading levels needed anywhere
  in the app.

## Layout (level view)

Four panes, always present, no modal-only content for objective/hints:

```
┌───────────────┬───────────────────────────┐
│ Objective      │                           │
│ (sidebar,      │      Terminal             │
│  ~25% width)   │      (xterm.js)           │
│                │                           │
│ Hints          ├───────────────────────────┤
│ (collapsible,  │                           │
│  below         │      Victim PC panel      │
│  objective)    │      (file tree / logs /  │
│                │       service status)     │
└───────────────┴───────────────────────────┘
```

- Objective sidebar: fixed width, scrolls independently, shows OWASP category badge +
  difficulty (1-10 dots) + objective text.
- Hints: hidden by default, revealed one at a time on click ("Show hint 1 of 3") to
  keep it a genuine escalation rather than a spoiler dump.
- Terminal: monospace, dark surface, blinking cursor, scrollback — standard xterm.js
  defaults, no custom chrome beyond a thin border and a small "connected to
  victim-pc-01" label.
- Victim PC panel: simple representation (a small file tree + a log tail + a services
  list) that visibly changes after a command resolves — this is the panel that makes
  the effect of an attack/defense legible, so favor clarity over decoration.

## Component styling notes

- Use Tailwind utility classes directly; no separate component-library theme file
  until repeated inline class lists actually get unwieldy (extract a `Panel` component
  at that point, not a whole design-system package).
- Buttons/links use the active role's accent color; everything else stays on the
  neutral `--text`/`--surface` palette.
