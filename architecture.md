# Architecture

## 1. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + Vite + TypeScript | Fast dev server, standard for interactive UI, first-class TS support |
| Terminal UI | xterm.js | Battle-tested terminal emulator, MIT licensed — don't hand-roll one |
| Styling | Tailwind CSS | Utility CSS, no hand-rolled design system, pairs natively with Vite |
| Backend | Python + FastAPI | Async, typed (pydantic), good fit for the command-engine logic and calling Ollama |
| Database | SQLite (stdlib `sqlite3`) | File-based, zero setup, free, plenty for level defs + per-user progress at this scale |
| AI agent runtime | Ollama (local) | Free, open-source, runs a real open model locally — no API cost, no rate limits |
| Frontend hosting | Vercel or Netlify (free tier) | Static React build, generous free tier |
| Backend hosting | Render/Fly.io free tier, or self-hosted alongside Ollama | See §5 for the Ollama hosting caveat |

No Docker, no CI, no ORM, no state-management library, no monorepo tool. Add each only
when a concrete need shows up — see `rules.md`.

## 2. Why a scripted simulation (not real containers)

Considered: spinning up a real, vulnerable Docker container per player session so
commands hit an actual target.

Rejected for this project because:
- Free hosting tiers don't reliably give persistent, isolated, per-session compute.
- Real exploitation surfaces real abuse risk (a public game that lets strangers run
  real attack tooling against containers you host is a liability, not a feature).
- It roughly triples the engineering surface (orchestration, isolation, cleanup) for a
  dissertation timeline that also needs 20 levels of content and an AI agent.

Instead: the backend holds, per level, a **scripted rule set** — a mapping from
recognized command patterns to a pre-modeled output and a resulting change in the
"victim PC" state. This is not a toy fallback; the technical depth lives in *how
accurately* each level models real tool output (real `nmap`/`sqlmap`/log-file syntax
and behavior), not in whether the exploit code is "real."

**Hard rule (see `rules.md`):** player input is **never** passed to a real shell, `eval`,
or subprocess. It is only ever pattern-matched as a string. This is non-negotiable —
it's what keeps a "hacking game" from becoming an actual RCE vector.

## 3. App flow

```
Landing page (intro only)
        ↓
Vulnerability Hub (10 OWASP categories, dual status: exploited / patched)
        ↓
Learn page (per vulnerability: what it is + why it matters, non-spoiler)
        ↓                                      ↓
  "Exploit it"                            "Patch it"
        ↓                                      ↓
Level view (Red level)                  Level view (Blue level)
  ┌─────────────┬─────────────────────────┐
  │ Objective    │ Terminal (xterm.js)     │
  │ sidebar      │  → player types command │
  │ + Hints      │  → POST /levels/:id/run │
  │              ├─────────────────────────┤
  │              │ Victim PC panel         │
  │              │  → renders updated state│
  └─────────────┴─────────────────────────┘
        ↓ (win condition met)                   ↓ (win condition met)
progress saved (session_id, red level_id)  progress saved (session_id, blue level_id)
        └──────────────── back to Learn page / Hub ────────────────┘
```

Once a category's Blue level is won, the command engine denies the paired Red level's
win command for the rest of that `session_id` — see §4a. A new session (new
`session_id`) starts unpatched again, so "until next session" falls out of the existing
session model for free, with no separate reset feature.

Backend request per command:

```
POST /api/levels/{level_id}/command
  body: { session_id, input: "nmap -sV 10.0.0.5" }
  →  command_engine matches input against level's rule set
  →  updates in-memory/SQLite session state for that level
  →  returns { terminal_output, victim_pc_state, hint_unlocked?, won? }
```

## 4. Level definition format

Each level is one JSON file under `backend/app/levels/`. This is the single source of
truth the command engine, the UI, and the randomizer agent all read.

```json
{
  "id": "red-03-injection",
  "role": "red",
  "order": 3,
  "owasp_category": "A03:2021 - Injection",
  "title": "SQL Injection: Login Bypass",
  "difficulty": 3,
  "objective": "Bypass the login form on the victim's internal admin panel.",
  "briefing": "Recon shows an admin panel at /admin/login...",
  "hints": [
    "Try submitting something unusual in the username field.",
    "SQL comments can end a query early: -- ",
    "' OR '1'='1' -- "
  ],
  "debrief": "Plain-language explanation of what the exploit/defense actually did. Like `commands`, this is withheld from `GET /levels/{id}/detail` (it would spoil the solution) — the command engine attaches it to the response only on the command that sets `wins_level: true`.",
  "victim_pc_initial_state": {
    "files": ["/var/www/admin/login.php"],
    "services": ["mysql", "apache2"],
    "logs": []
  },
  "commands": {
    "curl -X POST http://{ip}/login -d \"user=' OR '1'='1' -- \"": {
      "output": "HTTP/1.1 302 Found\nLocation: /admin/dashboard",
      "state_change": { "logs_append": ["[AUTH] admin login from {ip} - bypassed"] },
      "wins_level": true
    }
  },
  "randomizable_fields": ["ip"],
  "default_values": { "ip": "10.0.0.5" }
}
```

The command engine matches on normalized whitespace (not exact literal strings) so
incidental spacing differences still resolve — see
`backend/app/services/command_engine.py`.

**Optional `command_patterns`** (fallback tier, tried only when the literal `commands`
dict doesn't match): a level can declare regex-shaped commands instead of one exact
string, so any input of the *right shape* is accepted — e.g. any numeric invoice id,
not just the one hardcoded example — instead of falling through to "command not
recognized" for inputs a real target would still respond to. Still pure string/regex
matching, still never a real shell — see `rules.md`'s hard rule, unchanged by this.

```json
"command_patterns": [
  {
    "regex": "curl http://{ip}/api/invoices/(?P<id>\\d+)",
    "cases": [
      { "when": { "id": "1042" }, "output": "...", "state_change": {...}, "wins_level": false },
      { "output": "...{id}...", "state_change": {...}, "wins_level": true }
    ]
  }
]
```

Cases are tried in order; a case with a `when` dict only applies if every captured
group matches; a case with no `when`/`checks` is the catch-all default and should
come last. Case fields (`output`, `state_change` values, `wins_level`) may reference
a captured group — or a value a check derived — as `{name}`, filled in with
`randomizer._substitute` (the same generic substitution `{field}` tokens already
use).

**`checks`** — a case can gate on more than exact string equality via a small,
reusable, named-function library in `command_engine.py` (`CHECKS`), each returning
either `None` (case doesn't apply, try the next one) or a dict of derived values to
merge in for templating:

| check | does | used by |
|---|---|---|
| `regex` | does `field` match a shape? merges any named groups into the values (e.g. extracting the JNDI protocol) | SQLi tautology shape, JNDI lookup shape, PHP-serialized-object shape, algorithm-name allowlist, SSRF target-host check |
| `int_cmp` | numeric comparison (`lt`/`le`/`gt`/`ge`/`eq`/`ne`) | quantity sign, lockout attempt-count range |
| `int_derive` | always succeeds if `field` parses as an int; computes `into = \|field\| * factor` | the checkout level's credited/charged amount, computed from whatever quantity was actually sent, not one hardcoded pair of examples |
| `md5_matches` | real `hashlib.md5` computation, not a hardcoded plaintext | the hash-cracking level accepts any guess that actually hashes to the target, not one pre-approved word |
| `version_ge` | parses `x.y.z` and compares tuples | the log4j upgrade level accepts any version ≥ the real patched threshold, not one exact version string |

This is genuine per-command server-side logic (real hash computation, real numeric
comparison, real version comparison) — still never a real shell, never `subprocess`/
`eval` (`rules.md`'s hard rule is unchanged), but no longer limited to one hardcoded
example string per level. All 20 levels now use `command_patterns` for their win
condition; a level's `commands` dict is kept only where the real-world "correct
answer" genuinely is a single fixed string with no broader family (e.g. a specific
config-patch flag) — that's an honest reflection of the scenario, not laziness.
Every level also gets a generic `restart (?P<svc>\S+)` fallback pattern (Blue side)
so trying to restart *any* service, not just the one originally scripted, gets a
coherent "no effect" response instead of "command not recognized".

`{field}` tokens (matching a name in `randomizable_fields`) can appear anywhere in a
level's strings — `briefing`, `hints`, `commands` keys/output/`state_change` log
lines, `debrief` — and get substituted consistently everywhere by the randomizer
before a session ever sees the level. `default_values` is required for any field
that's actually templated; a level with `randomizable_fields` but no matching
`default_values` is treated as **not yet retrofitted** and skips randomization
entirely (see §5).

All 20 levels are now retrofitted — every level's `randomizable_fields` list matches
the `{field}` tokens actually present in its text (verified by a one-off consistency
script, not committed). Two fields ended up in use: `ip` (the victim's `10.0.0.5`,
wherever a level references it in a URL/log line) and `victim_username`
(`admin`/`guest`, wherever a level names the specific account being targeted/fixed —
`red-02`/`blue-02`, `red-07`/`blue-07`). `red-04`/`blue-04` also got `item_name`
(`widget`) — but only `red-04` actually mentions it in text, so `blue-04` keeps an
empty `randomizable_fields` list. **7 levels have no randomizable content and
correctly declare an empty `randomizable_fields: []`**: `blue-01`, `blue-04`,
`blue-05`, `blue-06`, `blue-08`, `blue-09`, `blue-10` — their content is entirely
file paths, service names, and patch commands with no cosmetic detail (ip/hostname/
username) actually referenced in the text, so there's nothing honest to tokenize.
This is a deliberate, checked outcome, not an oversight — inventing scenario details
that weren't in the original level design to force randomization variety was judged
out of scope for a retrofit pass.

## 4a. Vulnerability pairing & patch gate

A **vulnerability** is not a new content type — it's the existing `red-{NN}-{slug}` /
`blue-{NN}-{slug}` pair for a given `order`/`owasp_category`, derived by id convention
(strip the `red-`/`blue-` prefix, match on what's left). No new level schema, no merged
JSON file — the 20 existing, already-playtested level files are unchanged.

**New content — one small file, not per-level:** `backend/app/levels/vulnerability_intros.json`,
keyed by `owasp_category`, one short non-spoiler paragraph per category (what the
vulnerability class is, why it matters in the real world) — shown on the Learn page
*before* the player picks Exploit or Patch. This is distinct from each level's `debrief`,
which stays a spoiler (the specific scenario's answer) gated behind that level's own win.
Reusing `debrief` for this would leak the answer early; the two serve different moments.

**New read endpoint:** `GET /api/vulnerabilities?session_id=` — returns the 10 categories,
each with `{owasp_category, order, intro, red_level_id, blue_level_id, exploited, patched}`.
`exploited`/`patched` are read straight off the existing `progress` table (a completed row
for that session_id + red/blue level id) — no new table.

**Patch gate (the one real new mechanic):** in `command_engine`, before a Red level's
matched command is allowed to set `wins_level: true`, look up whether the paired Blue
level already has a completed `progress` row for the same `session_id`. If so, override
the response: `wins_level: false`, with output explaining the target has already been
patched — everything else about that command (it still "runs", still isn't a real shell)
is unchanged. Non-winning commands are never gated; only the win transition is. This
reuses the same `progress` table §6 already maintains — no schema change.

## 5. AI agent: Scenario Randomizer (built — `backend/app/services/randomizer.py`)

**Purpose:** the first time a session touches a level, regenerate its cosmetic/
parametric details — currently just `ip`, more fields as more levels get retrofitted
— so the underlying command set and win condition stay valid but the exact scenario
isn't memorizable from a previous playthrough or a walkthrough online.

**How it runs:**
1. `command_engine.get_level_for_session(session_id, level_id)` materializes a level
   once per session (cached), so a session's briefing/hints and its command matching
   always agree with each other even across multiple attempts.
2. `randomizer.randomize_level(level)` skips entirely (returns the level unchanged,
   no Ollama call) if the level has no `randomizable_fields` or no `default_values`
   — i.e. it hasn't been retrofitted with `{field}` tokens yet. This matters for
   performance: 19 of the 20 levels currently fall into this no-op path.
3. For a retrofitted level, it prompts a local Ollama model for strict JSON
   (field name → replacement value), one try + one retry.
4. **Sanitization**: every returned value must be a string, non-empty, ≤64 chars, and
   match `^[A-Za-z0-9.\-_]+$` (no quotes, braces, whitespace, newlines) — this blocks
   values that could break template substitution, JSON structure, or reintroduce a
   `{token}`-shaped string. Any field failing this check, a request timeout/connection
   failure, or a response that isn't valid JSON all fall back to the level's own
   `default_values` (its original, non-randomized content) — a level is never
   unplayable because the model/service is unavailable.
5. Substitutes the resolved values for every `{field}` token, recursively across the
   whole level dict (`briefing`, `hints`, `commands` keys/output/state-change log
   lines, `debrief`) — one substitution pass keeps every surface consistent.

Verified without a live Ollama install by mocking the Ollama-call function directly:
confirmed the unreachable-service fallback, confirmed a battery of malicious/malformed
simulated responses (prompt-injection-shaped strings, SQL-injection-shaped strings, a
re-injected `{token}`, embedded newlines, oversized strings, wrong types, missing
fields) all get rejected and fall back safely, and confirmed a well-formed safe value
does get applied consistently everywhere it appears.

**Live-verified with a real Ollama install (2026-07-17)**, `llama3.2:3b` pulled and
running locally — this closes the model choice, no need to also trial `phi3:mini`.
Three fresh sessions materializing the same level returned three different `ip`
values (confirmed genuine live generation, not the static `default_values` fallback).
Two real (not hypothetical) findings from this:
- **Cold-start latency exceeds the timeout budget.** A model with nothing loaded took
  ~19s to load plus ~20s for its first prompt eval - ~40s total, far past the 5s ×
  2-try budget in `_call_ollama`. So the very first request after Ollama starts (or
  after Ollama's default 5-minute idle timeout unloads the model) always times out
  both tries and silently falls back to `default_values` - by design that's still a
  safe, playable level, just not a randomized one. Once warm, a real generate call
  takes ~0.6-0.8s, comfortably inside the timeout, which is what the three sessions
  above actually hit. No code change made for this - documenting it here so a demo
  isn't confused by an unrandomized first level; sending one throwaway warm-up prompt
  before a demo session avoids it, if that ever matters enough to automate.
- **Generated values are shape-safe but not always semantically realistic** - e.g. an
  `ip` field came back as `1234567890` or `user_id` rather than an IP-shaped string.
  The sanitizer correctly accepts these (they're safe: alphanumeric, no
  quotes/braces/newlines) since its job is blocking unsafe characters, not judging
  realism. A prompt-engineering pass (few-shot examples of real IPs in the prompt)
  would improve output quality but wasn't in scope for verifying the mechanism works.

No agent framework, no multi-step planning loop — this is a single constrained
generation call. That's the whole "agent" for now; see `rules.md` for why nothing
heavier is justified yet.

**Model:** a small local model good enough for constrained JSON generation — e.g.
`llama3.2:3b` or `phi3:mini` via Ollama. Exact model choice is a Phase 3 decision once
real prompts are being tested against real level content.

**Hosting caveat:** Ollama needs a machine with real, persistent RAM/CPU — it will not
run on typical serverless free tiers. For development and for the dissertation demo,
run Ollama locally (or on whatever machine hosts the backend, if that machine has
enough headroom). If a fully public always-on deployment is needed later without a
persistent host, the randomizer call degrades to "use the level's original values" —
the game still works, just without per-play variation. Document actual deployment
choice in `handoff.md` once made.

## 6. Data & session model

- **Level content**: static JSON files in `backend/app/levels/`, loaded at startup.
- **Player progress**: one SQLite table (`progress`: session_id, level_id, completed_at,
  attempts) — drives both the Vulnerability Hub's exploited/patched status and the patch
  gate (§4a), by cross-referencing a session's red/blue rows for the same category.
- **In-session level state** (victim PC state while playing a level): kept in memory,
  keyed by session_id, for the lifetime of the backend process. Not durable across a
  backend restart — acceptable for a single-player learning tool at this scale. Move to
  SQLite/Redis only if that assumption ever breaks.
- **Identity**: a random session id issued to the browser (cookie or localStorage), no
  accounts, no passwords. Add real auth only if multi-device progress sync is actually
  requested.

## 7. Folder structure

```
F21MP/
├── README.md
├── prd.md
├── architecture.md
├── rules.md
├── design.md
├── handoff.md
├── frontend/
│   ├── src/
│   │   ├── pages/           # Landing, VulnerabilityHub (was Dashboard), Learn, LevelView
│   │   ├── components/      # ObjectivePanel, Terminal, VictimPC, Hints
│   │   ├── api/              # thin fetch wrapper to backend
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
└── backend/
    ├── app/
    │   ├── main.py           # FastAPI app + routes
    │   ├── models.py         # pydantic request/response schemas
    │   ├── db.py             # sqlite3 connection + progress table
    │   ├── levels/           # one .json per level (20 total) + vulnerability_intros.json
    │   └── services/
    │       ├── command_engine.py
    │       └── randomizer.py
    ├── requirements.txt
    └── run.py                # uvicorn entrypoint
```

Two distinct codebases as required: `frontend/` never imports backend code and vice
versa; they only talk over the HTTP API in §3.

## 8. Phases (see `handoff.md` for live status)

1. **Dashboard** — landing page, role selection, level-list dashboard, progress display
   (mock/empty level data is fine here).
2. **Game UI** — the four-pane level view components, wired to the backend API,
   still fine with placeholder level content.
3. **Game development** — real content: all 20 level JSON files, the command engine,
   win-condition logic, the randomizer agent wired in.
4. **Testing end-to-end** — playtest all 20 levels both ways, fix bugs, finalize docs.
