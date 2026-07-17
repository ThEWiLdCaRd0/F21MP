# Handoff

Read this file at the start of every session. Update it at the end of every session —
what got done, what's next, what's currently open. This is the single source of truth
for "where did we leave off."

## Aim / end goal (stable — copy from `prd.md`, don't rewrite each session)

Build a browser-based cybersecurity training game (MSc Applied Cybersecurity
dissertation) where players choose Red Team (attack) or Blue Team (defend) and play
through 10 levels per side, covering the OWASP Top 10 (2021), via a scripted (non-live)
simulation: an objective sidebar, a terminal, a "victim PC" panel, and hints. Scenario
details are randomized per playthrough by a local Ollama-backed agent. Everything must
run on free/open-source infrastructure. See `prd.md`, `architecture.md`, `rules.md`,
`design.md` for the full detail behind each of those points.

**Phases:** 1) Dashboard → 2) Game UI → 3) Game development (levels + engine + agent) →
4) Testing end-to-end.

## Current phase

**Architecture change (2026-07-17)**: the app is no longer role-first (pick Red or Blue
for the whole session). It's now vulnerability-first: Landing → Vulnerability Hub (10
OWASP categories, grid view) → Learn page (non-spoiler intro + Exploit/Patch choice) →
Level view. See `prd.md` §5/§6 and `architecture.md` §3/§4a for the recorded decision —
this has been fully implemented (backend + frontend), not just designed.

**Phase 1 (Dashboard)**: superseded by the Vulnerability Hub above — functionally
complete under the new design. **Phase 3 (Game development)**: all 20 levels
written/validated/playtested, randomizer agent built and wired in, all 20 levels
retrofitted with real `{field}` tokens + `default_values` (see `architecture.md` §4 for
which fields landed where and why 7 blue levels correctly have none), and the
**persistent patch gate** (§4a) is built and verified. **Phase 2 (Game UI)**: LevelView
polished to match `design.md` (JetBrains Mono heading, ~25% sidebar, accent-glow hover
on nav buttons); Landing/Hub/Learn are new pages built for the vulnerability-first flow,
not yet browser-verified (see Next steps).

## Completed this session (2026-07-15)

- Decided: scripted simulation (not real containers), React+Vite+TS / Python+FastAPI,
  Ollama for the randomizer agent, SQLite for persistence, Tailwind for styling,
  xterm.js for the terminal (all recorded with reasoning in `architecture.md`).
- Wrote `prd.md`, `architecture.md`, `rules.md`, `design.md` — read these before
  building anything; they contain the actual decisions, not just this summary.
- Scaffolded `frontend/`: Vite + React + TS, Tailwind v4 (via `@tailwindcss/vite`),
  Google Fonts (Inter + JetBrains Mono) wired into `index.html`, dark theme CSS
  variables from `design.md` in `src/index.css`, dev-server proxy to `/api` →
  `localhost:8000` in `vite.config.ts`, boilerplate marketing content stripped out of
  `App.tsx`. Verified `npm run build` succeeds.
- Scaffolded `backend/`: FastAPI app (`app/main.py`) with CORS for the Vite dev
  origin and a `/api/health` route, SQLite `progress` table bootstrap (`app/db.py`),
  `run.py` uvicorn entrypoint, `.venv` created, `requirements.txt` installed. Verified
  `GET /api/health` returns `{"status": "ok"}`.
- `app/services/` and `app/levels/` (command engine, randomizer agent, level JSON
  files) deliberately **not** stubbed out yet — that's real Phase 3 work; empty
  placeholder files would just be scaffolding-for-later, which `rules.md` says to
  avoid.
- **Landing page** (`frontend/src/pages/Landing.tsx`): intro copy + Red/Blue role
  selection cards, styled from `design.md` tokens. Session identity
  (`frontend/src/lib/session.ts`): `crypto.randomUUID()` issued and cached in
  localStorage on first role pick, no backend call needed to mint it. `App.tsx` wires
  role selection with plain `useState` — no router added yet (only two screens exist
  so far; add one when the dashboard/level-view screens actually need real routes/URLs).
  Verified with a headless Playwright drive: landing renders, clicking Red Team
  transitions and persists the session id, zero console errors.

- **`/api/levels` + `/api/progress`** (`backend/app/main.py`, `backend/app/models.py`):
  `/api/levels?role=red|blue` returns 20 generated stubs (10 red + 10 blue, one pair
  per OWASP Top 10 (2021) category, `difficulty` = order 1-10) — generated from a
  small `OWASP_CATEGORIES` list rather than hand-written, so it can't drift out of
  sync with `prd.md` §9. `/api/progress?session_id=` reads the existing `progress`
  SQLite table (empty until Phase 3's command engine can actually complete a level).
  Verified both routes directly with curl (20 levels, correct role split, empty
  progress list for a fresh session).
- **Dashboard page** (`frontend/src/pages/Dashboard.tsx`, `frontend/src/api/client.ts`):
  fetches levels for the chosen role + progress for the session id, renders an
  ordered list with title, OWASP badge, a 10-dot difficulty indicator, and a ✓ for
  completed levels. `App.tsx` now goes Landing → Dashboard on role selection.
  Verified with a headless Playwright drive against the real backend (not mocked):
  picked Blue Team, saw all 10 Blue levels render correctly, "0 / 10 completed",
  zero console errors. Screenshot confirmed the dot/badge/accent styling matches
  `design.md`.

- **Back navigation + cyber visual pass**: `Dashboard` takes an `onBack` prop
  (`App.tsx` resets `role` to `null`), rendered as a `← back` button. Brightened the
  whole palette for more contrast (`design.md` updated with new hex values + two new
  `--red-glow`/`--blue-glow` tokens), added a CSS-only 32px grid background on `body`,
  and gave interactive surfaces (role cards, level rows, back button) a glow +
  accent-border hover state instead of a flat border. Headings/role labels switched
  to JetBrains Mono. No new dependencies — all done with existing Tailwind arbitrary
  values + CSS vars. Verified with a Playwright drive: hover glow renders, back
  button returns from Dashboard to Landing correctly, zero console errors.

- **Phase 3, first slice — command engine + one real level**
  (`backend/app/services/command_engine.py`, `backend/app/levels/red-03-injection.json`):
  loads level JSON from `app/levels/` at startup, matches player input as a
  whitespace-normalized **string** (never `subprocess`/`eval` — the hard rule in
  `rules.md`), applies `state_change` (`*_append` keys append to a list field,
  everything else overwrites), tracks per-`(session_id, level_id)` victim-PC state
  in memory, and on a win writes to the same `progress` SQLite table the Dashboard
  already reads — so completing a level now actually shows up on the Dashboard.
  New endpoints: `GET /api/levels/{id}/detail` (public level data — deliberately
  excludes the `commands` dict, which is the answer key) and
  `POST /api/levels/{id}/command`. `red-03-injection` has two commands: a wrong
  login (401, logged, doesn't win) and the SQLi bypass payload (302, wins).
  Verified the whole loop with curl end-to-end: detail hides the answer key, 404 on
  unknown level, wrong command doesn't win, an unrecognized command hits the
  fallback path without corrupting state or counting as an attempt, the winning
  payload sets `wins_level: true` and `/api/progress` shows `completed_at` set with
  `attempts: 2` (the two recognized commands only — noise doesn't inflate it).

- **Minimal level view** (`frontend/src/pages/LevelView.tsx`): objective sidebar
  (OWASP badge, title, objective, briefing, escalating hints) + terminal (command
  input, scrollback of `$ input` / output pairs, wired to `POST
  /api/levels/{id}/command`) + victim-PC panel (files/services/logs, re-rendered
  from each response). Dashboard level rows are now clickable
  (`Dashboard.tsx`'s `onSelectLevel`); `App.tsx` gained a third state slot
  (`levelId`) alongside `role` — still plain `useState`, no router yet, three
  screens still doesn't force the issue.
  Verified by actually playing it end-to-end through the browser (Playwright,
  not curl this time): Landing → Red Team → clicked "Attack: Injection" → typed
  the wrong login (saw the 401 and the log line appear in the victim-PC panel) →
  typed the SQLi payload → saw the 302, the log update, and "✓ Level complete" in
  the sidebar. Zero console errors both screenshots.
  Not yet matching `design.md`'s exact three-pane layout (objective sidebar + hints
  section stacked, not separate) or its precise spacing — functional MVP, visual
  polish deferred.

- **Post-win debrief**: added a `debrief` field to the level schema (plain-language
  explanation of what the exploit actually did and why, plus the OWASP mitigation) —
  see `red-03-injection.json` and `architecture.md` §4. Labeled the sidebar's
  objective/briefing text so the "what am I supposed to do" description reads clearly
  before the player starts. **Security fix caught before shipping**: the debrief
  text effectively states the solution, so — like the `commands` answer key — it's
  now withheld from `GET /levels/{id}/detail` entirely and only attached to the
  `POST .../command` response on the specific command that sets `wins_level: true`
  (`command_engine.run_command`, `CommandResult.debrief`). Verified with curl: absent
  from detail, `null` on non-winning commands, present only on the win. Also fixed a
  real bug hit along the way: `Path.read_text()` on Windows defaults to the system
  codepage, not UTF-8, so the debrief's em dash was rendering as mojibake
  (`â€"`) — fixed with `encoding="utf-8"` in `command_engine._load_levels`; worth
  remembering for any future level content with non-ASCII characters.

- **All 19 remaining levels written** (`backend/app/levels/*.json`): one Red +
  one Blue level per OWASP Top 10 (2021) category, following the proven
  `red-03-injection` pattern — objective/briefing/3 escalating hints, a wrong-attempt
  command + a winning command, victim-PC state changes, and a post-win `debrief`.
  Validated all 20 files programmatically (schema completeness, exactly 3 hints,
  at least one winning + one non-winning command, filename matches `id`, id set
  matches the `role-NN-slug` pattern) before touching the API — all passed.
  Spot-checked one new level (`blue-02-cryptographic-failures`) end-to-end via curl:
  detail hides `commands`/`debrief`, wrong action doesn't win, correct fix
  (`rehash-password admin --algorithm bcrypt`) wins and records progress.
- **Bug found and fixed while wiring this in**: `GET /api/levels` was still backed
  by `main.py`'s old Phase-1 mock title generator (`"Attack: <category>"` /
  `"Defend: <category>"`), which no longer matched the real, specific titles now in
  the level JSON files (e.g. real title "Steal Cloud Credentials via the Preview
  Fetcher" vs. generated "Attack: Server-Side Request Forgery (SSRF)"). Replaced the
  generator entirely — `list_levels` now builds `LevelStub`s straight from
  `command_engine.get_levels()`, the same data `GET /detail` and the command engine
  already use, so there's exactly one source of truth for level content going
  forward. Verified via curl (`GET /api/levels?role=blue` returns the real titles,
  correctly ordered 1-10) and a Playwright screenshot of the full Blue dashboard.

- **Full playtest pass, all 20 levels**: wrote an automated playtest script (reads
  each level's real JSON, drives the actual running API — not mocked) that for every
  level checks: `GET /detail` never leaks `commands`/`debrief`, an unrecognized
  command doesn't crash or win, the documented non-winning command doesn't win and
  matches its expected output, the documented winning command wins/matches output/
  returns the exact `debrief`, and `/api/progress` shows `completed_at` set
  afterward. **20/20 passed** on the first run. Also browser-spot-checked the two
  levels whose `state_change` overwrites `files`/`services` directly instead of just
  appending to `logs` (`blue-06-vulnerable-components`'s jar-version bump,
  `blue-09-logging-failures`'s service-list addition) — both rendered correctly in
  the Victim PC panel, confirming the generic `LevelView` component handles
  non-append state changes too, not just the log-append case already covered by
  `red-03-injection`.

## Completed this session (2026-07-16)

- **Randomizer agent built** (`backend/app/services/randomizer.py`) — see
  `architecture.md` §5 for the full design writeup. Calls a local Ollama model for
  strict-JSON field replacements, one try + one retry, then falls back to the
  level's own `default_values` on any failure (unreachable service, invalid JSON,
  a field that fails sanitization) — a level is never unplayable because the model
  is down. **Sanitization**: generated values must be a string, non-empty, ≤64
  chars, matching `^[A-Za-z0-9.\-_]+$` — rejects quotes/braces/newlines/oversized
  values/wrong types, so a compromised or misbehaving model can't inject something
  that breaks template substitution, JSON structure, or reintroduces a `{token}`.
  Ollama isn't installed in this dev environment, so the live-generation path is
  unverified by nature, but the code path that matters most (everything failing
  safely) is fully tested: mocked the Ollama-call function directly and confirmed
  (a) unreachable service falls back to defaults, (b) a battery of malicious/
  malformed simulated responses (prompt-injection-shaped text, SQL-injection-shaped
  text, a re-injected `{token}`, embedded newlines, 200-char string, wrong type,
  missing field) all get rejected and fall back safely, (c) a well-formed value
  actually gets applied, consistently, everywhere it appears, and (d) a level with
  no `default_values` skips the Ollama call entirely (so the other 19 levels, not
  yet retrofitted, have zero added latency or behavior change).
- **`command_engine.get_level_for_session`**: materializes a level once per
  `(session_id, level_id)` and caches it, so a session's briefing/hints/victim-PC
  state and its command matching always agree, even across multiple attempts.
  `GET /api/levels/{id}/detail` now requires `session_id` (was previously
  session-independent) so it returns the same materialized content the command
  engine will match against — this is a breaking API change, frontend updated to
  match (`client.ts`, `LevelView.tsx`).
- **`red-03-injection.json` retrofitted** as the proof-of-concept: `10.0.0.5`
  replaced with `{ip}` in the briefing, both command patterns, and both log lines;
  added `"default_values": {"ip": "10.0.0.5"}`; trimmed `randomizable_fields` down
  to `["ip"]` (the other three — hostname/victim_username/log_timestamps — were
  aspirational placeholders from before the randomizer existed and aren't actually
  templated anywhere, so left declaring them would have been misleading).
- **Broader input sanitization pass** (the user's second, wider request):
  - `CommandRequest.session_id`/`.input` now have `Field(min_length=..., max_length=...)`
    constraints (128 / 2000 chars) — empty or oversized values now get a clean 422
    instead of being accepted silently. Same constraint added to the `session_id`
    query param on `/api/progress` and `/api/levels/{id}/detail`.
  - `command_engine._load_levels` now checks every level file has all required
    schema keys and raises a clear `ValueError` naming the file + missing keys if
    not, **and** `main.py`'s startup hook now calls `get_levels()` eagerly — found
    and fixed a real gap here: level loading was lazy (first request only), so a
    malformed level file would previously pass a clean startup and only blow up
    confusingly on some future player's first request. Verified by dropping a
    deliberately broken level file in `app/levels/` and confirming the server now
    refuses to start, naming the exact file and missing keys, instead of starting
    clean and failing later.
  - All fixes verified with curl: empty/oversized `session_id`, empty/oversized
    command `input` all now 422; a normal valid request still works fine (200).
- Re-ran the full 20-level automated playtest suite (updated for the new
  `session_id`-on-detail requirement) after every change in this session —
  **20/20 passed** each time, no regressions. Also replayed `red-03-injection`
  through the actual browser: materialized briefing correctly shows the fallback
  `10.0.0.5`, full win flow still works, zero console errors.

## Completed this session (2026-07-16, continued)

- **All 19 remaining levels retrofitted** with real `{field}` tokens + `default_values`
  (`red-01`, `red-02`, `red-04` through `red-10`, `blue-02` through `blue-10` — `red-03`
  was already done as the proof-of-concept). Two fields ended up genuinely in use across
  the set: `ip` (`10.0.0.5`, wherever a level's text references the victim host) and
  `victim_username` (`admin` in the `red-02`/`blue-02` MD5-crack pair, `guest` in the
  `red-07`/`blue-07` brute-force pair). `red-04` also got `item_name` (`widget`) since
  it's genuinely referenced in its commands; `blue-04` does not mention it, so it stays
  untokenized there. **7 levels** (`blue-01`, `blue-04`, `blue-05`, `blue-06`, `blue-08`,
  `blue-09`, `blue-10`) legitimately have zero randomizable content — their text is only
  file paths, service names, and patch commands, no ip/username/item ever appears — so
  they correctly declare `"randomizable_fields": []` and take the documented no-op path
  rather than having fabricated scenario detail invented for them. Full reasoning and the
  per-level field table lives in `architecture.md` §4.
- Wrote a one-off consistency check (not committed — lived in the scratchpad) that
  parses every level file and asserts `randomizable_fields` exactly matches both the
  keys in `default_values` and the actual `{field}` tokens found anywhere in the level's
  text — **20/20 passed**. Then started the real backend and curl-verified end-to-end on
  a representative sample: `red-01` (`ip` only), `red-07` (`ip` + `victim_username`,
  two tokens in one level), `blue-02` (`victim_username`, five occurrences across
  briefing/hint/commands/output/logs), and `blue-01` (empty `randomizable_fields`,
  confirming the no-op path still plays normally) — all four materialized correctly
  (fallback default values substituted, no live Ollama needed) and won correctly.
  `GET /api/levels?role=...` still returns the correct 10/10 split — no regressions.

## Completed this session (2026-07-17)

- **Regex-based `command_patterns` fallback tier** in the command engine
  (`backend/app/services/command_engine.py`, `_match_pattern`) — the user hit a real
  gap: `red-01`'s IDOR level only recognized the one hardcoded neighboring invoice id
  (1043), so trying a different valid-looking id (1047, 2043) returned "command not
  recognized" instead of a plausible in-character response, breaking immersion. Rather
  than the much bigger step of real per-session command execution (assessed and
  explicitly declined — see the reasoning below), added a second matching tier: after
  the literal `commands` dict misses, an optional per-level `command_patterns` list is
  tried — a regex captures named groups (e.g. `(?P<id>\d+)`), and an ordered list of
  `cases` (each with an optional `when` dict on the captured values, first match wins,
  no-`when` case is the catch-all default) produces the response, with `{captured}`
  placeholders filled in via `randomizer._substitute` (reused as-is, no changes to
  randomizer.py needed). Still pure string/regex matching — no real shell, no
  `rules.md` rule crossed.
  Piloted on `red-01-broken-access-control`: its two hardcoded invoice-id commands
  were replaced by one pattern (own id 1042 → no-win response, any other numeric id →
  a generated "user_{id}" IDOR win). Full schema/design writeup in `architecture.md`
  §4. Verified end-to-end via curl: 1042 still doesn't win, 1043 still wins (same as
  before), 1047 and 2043 (previously "not recognized") now both win with an id-specific
  response, and a non-numeric id (`abc`) still correctly falls through to "not
  recognized" since it doesn't match the pattern's shape. Re-ran the 20-file
  consistency script — no regressions on the other 19 levels, which don't use this
  tier at all yet.
- **Assessed and explicitly declined a full real-execution architecture** (container/
  VM-per-session, real vulnerable stacks, sandboxing/orchestration) when the user
  first raised wanting non-scripted command handling — this is exactly what
  `architecture.md` §2 already rejected (triples engineering surface, breaks the
  free-tier rule, real abuse/liability surface for a public app). Landed on the
  `command_patterns` approach above instead, which solves the actual complaint
  (valid-shaped-but-unmodeled input) without any architecture change.

## Completed this session (2026-07-17, continued)

- **`command_patterns` rolled out to all 20 levels**, per explicit user direction
  ("hardcoding must never be the answer"). `command_engine.py` gained a small,
  reusable, named-check library (`regex`, `int_cmp`, `int_derive`, `md5_matches`,
  `version_ge` — see `architecture.md` §4 for the full table and reasoning) so a
  case can gate on real computed logic, not just exact-string equality. Every
  level's win condition now goes through this instead of a hardcoded example
  string:
  - **Real computation, not hardcoded literals**: `red-02` now computes an actual
    `hashlib.md5` and accepts any guess that truly hashes to the target (not one
    pre-approved word); `blue-06` parses the log4j version the player upgrades to
    and accepts anything ≥ 2.17.0 (not one exact version string); `red-04`
    computes the credited/charged amount from whatever quantity was actually sent.
  - **Shape validation replacing one exact payload**: `red-03` accepts any of
    several classic SQLi tautology/comment-bypass shapes (not one exact string);
    `red-06` accepts any JNDI protocol (`ldap`/`rmi`/`dns`/...), not just the one
    hint example; `red-08` accepts any well-formed PHP-serialized-object payload,
    not just the one class name; `red-10` accepts any path under the metadata IP,
    not one exact IAM sub-path; `blue-02` accepts bcrypt/argon2/scrypt (the real
    OWASP-approved family), not only bcrypt.
  - **Range/threshold checks**: `blue-07`'s lockout fix only wins for a genuinely
    small `--max-attempts` (1-10) — setting it to something absurdly high "enables
    lockout" in name only and correctly doesn't win, with a message explaining why.
  - **Generic wrong-action fallback**: every Blue level now accepts `restart
    <any-service>` (not just the one originally scripted service name) as a
    coherent no-op instead of "command not recognized"; `blue-09` also
    distinguishes "started the service" from "started it *and* turned alerting
    on" — a half-fix now gets a distinct, correct, non-winning response instead of
    either winning wrongly or being unrecognized.
  - Where a level's real answer genuinely is one fixed string with no broader
    family (e.g. a specific config-patch flag name), it's still a single literal
    match — that's honest modeling, not a hardcoding shortcut.
- **Assessed and explicitly declined a full real-execution architecture**
  (container/VM-per-session) earlier in this same conversation when the user first
  asked about non-scripted commands — see the previous session block above for the
  full reasoning. `command_patterns` is the (correctly-scoped) alternative that
  was built instead.
- **Verified end-to-end against the live server**: wrote a scripted playtest
  (51 commands across all 20 levels, both winning and non-winning inputs per
  level) hitting the real running backend — **51/51 passed**. Also extended the
  static consistency script to `re.compile()` every `command_patterns` regex and
  every check's `regex` arg across all 20 files (catches typos/escaping mistakes
  that a startup pass alone wouldn't, since patterns only compile lazily at
  match-time) — all clean. Note: a handful of individual test requests took ~8s
  each (2 timed-out attempts to reach Ollama, which isn't installed in this dev
  environment) - this is pre-existing randomizer fallback behavior, not something
  introduced this session, just newly visible because the playtest hits many fresh
  sessions in a tight loop.

## Completed this session (2026-07-17, vulnerability-first redesign)

- **`prd.md`/`architecture.md` updated first**, before any code, to record the
  decision: Landing drops the upfront Red/Blue pick; a Vulnerability Hub + Learn page
  replace the role-scoped Dashboard; a persistent patch gate denies replaying an
  exploit after its patch has been won, resetting only on a new session. Recorded as
  `architecture.md` §4a (not renumbered, since this doc's existing §4/§5 citations
  elsewhere in this file needed to stay valid).
- **Backend**: `command_engine._paired_level_id` derives the red/blue pair by id
  convention (no merged level files, all 20 existing JSON files untouched);
  `_is_patched` checks the existing `progress` table for the paired Blue level's
  completion — no new schema. `run_command` now intercepts a would-be win with an
  in-character denial once patched. New `vulnerability_intros.json` (10 short
  non-spoiler paragraphs, one per OWASP category — deliberately separate from each
  level's spoiler `debrief`). New `GET /api/vulnerabilities?session_id=` endpoint
  returns all 10 categories with `intro`/`red_level_id`/`blue_level_id`/`exploited`/
  `patched`. Loaded eagerly at startup (fail-fast, same convention as `get_levels()`).
  Verified end-to-end via curl: fresh session exploits normally, patch wins, hub shows
  both flags true, replaying the exploit in the *same* session is denied with
  `wins_level: false` and unchanged victim-PC state, a *new* session_id exploits
  normally again, and patching one category left an unrelated category's flags
  untouched (gate is per-category, not global).
- **Incidental fix**: found and killed a stale orphaned backend process (a leftover
  `python.exe` from outside this session's own process tree) that was still bound to
  port 8000 serving old code and making the new route 404 — not a bug in the app,
  just dev-environment cleanup.
- **Frontend rewire**: `Landing.tsx` now just intro + `START` (no role cards).
  New `VulnerabilityHub.tsx` (replaces `Dashboard.tsx`, which was deleted along with
  the now-dead `LevelStub`/`getLevels` in `client.ts`) lists all 10 categories in a
  **grid** (1/2/3 cols responsive, per explicit follow-up request) with two
  independent status pills (exploited/patched) instead of one combined checkmark.
  New `Learn.tsx` shows the category's non-spoiler intro + Exploit/Patch cards (styled
  like Landing's old role cards), fetching fresh status on every visit so it's never
  stale after playing. `App.tsx` rewired to `started → category → levelId` state
  instead of `role → levelId`. `LevelView.tsx` unchanged — already generic enough to
  serve either side, reached via Learn now instead of a role-locked dashboard.
  Verified: `tsc --noEmit` clean, `npm run build` succeeds, `/api/health` and
  `/api/vulnerabilities` both resolve through the Vite dev proxy. **Not yet
  browser-verified** — no browser tool was available this session (Claude in Chrome
  was declined), so the actual click-through flow hasn't been watched end-to-end by
  Claude, only by static checks + curl against the API layer it calls.

## Currently working on

Nothing in progress. Phase 3 (game development) and Phase 4 (testing end-to-end) are
both now substantively done: all 20 levels, the command engine, the patch gate, and
the randomizer are built and verified (including a real, non-mocked Ollama run), and
a committed test (`test_patch_gate.py`) covers the patch-gate cycle across all 10
categories. The `GET /api/levels?role=` cleanup is the only loose end.

## Next steps

- [x] **Browser-test the new flow end-to-end** — user confirmed 2026-07-17: played it
      live, the exploit-denial message rendered correctly in the terminal after
      patching. Core patch-gate mechanic confirmed working through the actual UI, not
      just curl.
- [x] **`backend/test_patch_gate.py` committed** — a real winning command for all 20
      levels (read from each level's own JSON, not guessed), driving the full
      exploit → patch → denied → fresh-session-works cycle for all 10 categories
      against the live server. **10/10 passed.** Caught and fixed one wrong command
      in the process (`red-03`'s actual endpoint is `/admin/login` with a
      `username=`/`password=` body, not the older `/login`+`user=` shape from an
      earlier illustrative example in `architecture.md`).
- [x] **Ollama installed and the live-generation path verified end-to-end**
      (2026-07-17) — see `architecture.md` §5 for the full writeup. `llama3.2:3b`
      pulled and confirmed working: three fresh sessions materializing the same
      level came back with three different `ip` values, proving genuine live
      generation rather than the static fallback. Found and documented two real
      operational facts: cold-start (~40s) blows past the 5s×2-try timeout and
      always falls back on the very first request after Ollama starts/idles out;
      once warm, real calls take ~0.6-0.8s and comfortably fit the timeout.
      Generated values are shape-safe but not always realistic (e.g. `1234567890`
      for an `ip` field) — a prompt-quality issue, not a bug, and out of scope for
      this pass.
- [x] **Model choice decided**: `llama3.2:3b`, confirmed working live — no need to
      also trial `phi3:mini`.
- [ ] `GET /api/levels?role=` is now unused by the frontend (Hub/Learn use
      `/api/vulnerabilities` instead) — left in place since it's harmless and wasn't
      asked to be removed, but it's a candidate for deletion if it stays unused.

## Open questions / decisions deferred on purpose

- Whether the backend + Ollama get deployed anywhere public, or the dissertation demo
  runs locally — deferred until it's actually time to demo; `architecture.md` §5
  documents the fallback behavior either way, and now also the cold-start caveat to
  account for if a public deployment ever happens.
- Precise difficulty curve / exact level-to-OWASP-category assignment ordering — never
  ended up mattering enough to revisit; each track is already ordered 1-10 by its own
  `difficulty` field and that's held up through every playtest so far.
- Optional prompt-quality pass for the randomizer (real IP-shaped examples in the
  prompt) — generated values are safe but not always realistic; not blocking anything.
