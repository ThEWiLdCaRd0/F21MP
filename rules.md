# Rules

Working conventions for this project. Read before starting a session; update when a
real decision is made that future-you or another dev would need to know.

## Use

- **Ponytail discipline on every change**: cheapest thing that works first — stdlib →
  native platform feature → already-installed dependency → one line → minimum new code.
  No new dependency for what a few lines already do.
- **Free/open-source infrastructure only** — hosting, models, APIs, libraries. No paid
  tier, ever, for any part of this project.
- **Two distinct codebases** (`frontend/`, `backend/`) that only talk over the HTTP API.
  Never import one from the other.
- **TypeScript strict mode** in `frontend/`; type hints + pydantic models in `backend/`.
- **xterm.js** for the terminal UI. **Tailwind CSS** for styling. **SQLite** for
  persistence. Don't replace these without a concrete reason written down here.
- **Ollama** for the randomizer agent, called directly over its local HTTP API
  (`httpx`/`requests`). No agent framework (LangChain etc.) for a single constrained
  generation call.
- Keep level content as **data** (JSON files), not code — adding a level should never
  require touching the command engine.
- One `handoff.md` update at the **start** (read it) and **end** (write it) of every
  session.

## Avoid

- **No real command execution.** Player terminal input is pattern-matched as a string,
  never passed to `subprocess`, `os.system`, `eval`, `exec`, or any real shell. This is
  the single most important rule in the project — breaking it turns a teaching game
  into a real RCE vector. Also breaking it: keep it that way when the AI agent gets involved -
  never let generated output be interpreted as code, only as data (strings/JSON values).
- **No real attacks on real infrastructure.** No live scanning, no real network calls to
  real external hosts, no real malware/payload storage, even for "authenticity."
  Everything the player attacks is a simulated `victim_pc_state` object.
- **No premature abstraction.** No interface for a single implementation, no plugin
  system for 20 levels that are just data files, no generic "game engine" layer until a
  second game actually needs one.
- **No infra you have to babysit before it's earned its place**: no Docker, no CI/CD
  pipeline, no ORM, no Redis, no message queue, no microservices split. Add each only
  when a real, current need (not a hypothetical future one) shows up — and note the
  reason here when you do.
- **No scope creep past 20 levels / OWASP Top 10 (2021)** without updating `prd.md`
  first.
- **No `git commit --no-verify` / force-push to shared branches** without explicit
  sign-off in the moment.
- **No committing secrets** (API keys, tokens) — there shouldn't be any paid-API keys in
  this project at all; if one shows up, that's a sign a "free-only" rule got broken.

## Assistant conventions

- Every AI-assistant response in this project starts with the literal word `MLEM`, per
  standing user instruction — not a code rule, just recorded here so it doesn't get
  dropped.

## Ethical/safety guardrails specific to this project

- Every "attack" and "defense" the player performs is against fabricated data
  (`victim_pc_state`), never a real endpoint, real file system, or real account.
- Hints and level content teach *mitigations*, not just exploitation — every Red level
  has a matching Blue level; don't ship one without the other.
- If a future contributor is tempted to add "real" execution for realism, point them at
  §Avoid above and `architecture.md` §2 first.
