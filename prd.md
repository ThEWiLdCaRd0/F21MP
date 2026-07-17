# Project Requirements Document (PRD)

## 1. Project

**Working title:** Red/Blue — a browser-based cybersecurity training game
**Context:** MSc Applied Cybersecurity dissertation project

## 2. Problem

Cybersecurity enthusiasts and students learn OWASP Top 10-class threats mostly through
static writeups or expensive/complex lab setups (real VMs, Metasploitable, paid ranges).
There's a gap for something that is: browser-based, free to run, teaches both the attack
and the defense side of the same vulnerability class, and doesn't get stale after one
playthrough.

## 3. Target users

- Cybersecurity/CS students (undergrad/postgrad) learning offensive & defensive basics.
- Self-learners preparing for certs (Security+, CEH, eJPT) who want hands-on drilling of
  OWASP Top 10 concepts without standing up their own lab.
- CTF beginners/intermediates who want structured, increasingly-difficult scenarios.
- Dissertation evaluators assessing the educational and technical merit of the system.

## 4. Aim

Teach players how to **attack** and **defend** against real-world classes of cyberattacks
(OWASP Top 10) through a game that is technically credible but never touches a real
network, real exploit code, or a real shell.

## 5. Core concept

- Landing page is a plain intro — **no upfront Red/Blue commitment**. Which side the
  player acts as is chosen per vulnerability, not once for the whole session.
- **Vulnerability Hub**: a list of the **10 OWASP Top 10 (2021) categories**. Each entry
  shows a dual status indicator — exploited (Red accent) / patched (Blue accent) — so
  progress is visible per vulnerability, not per side. The player can tackle categories
  in any order.
- Picking a category opens a **Learn page** first: a short, non-spoiler explainer of what
  the vulnerability class is and why it matters in the real world, followed by two
  choices — **Exploit it** or **Patch it**. Either can be done first; the player can come
  back and do the other later in the same session.
- **20 levels** total: 10 Red (exploit), 10 Blue (patch), one pair per OWASP category —
  reached through the Learn page rather than a pre-committed role track. Each level still
  climbs its own internal difficulty curve.
- **Persistent patch gate**: once a category's Blue (patch) level is won, that
  vulnerability is "fixed" for the rest of the session — replaying the matching Red
  (exploit) level's win command afterward is denied in-character ("target already
  patched") instead of winning again. Reinforces that a real fix sticks. Resets naturally
  with a new session (see `architecture.md` §4a) — no separate reset feature needed.
- Every level (exploit or patch) is played through the same three-pane layout:
  1. **Objective sidebar** — what this level is, what "win" means, current OWASP category.
  2. **Terminal pane** — where the player types commands.
  3. **Victim PC pane** — a simulated target machine whose visible state (files, logs,
     running services, alerts) changes in response to the player's commands.
  4. **Hints** — optional, escalating (nudge → stronger nudge → near-answer).
- Attacks and defenses are **simulated, not executed**: the backend matches player input
  against a level's scripted rule set and returns a realistic, pre-modeled outcome. No
  real exploit code runs, no real network is touched, nothing capable of harming a real
  system ever executes. Realism comes from how well each level's simulated
  environment/output is modeled, not from live exploitation.
- To keep replays fresh, an **AI agent (local, via Ollama)** rewrites the cosmetic and
  parametric details of a level's scenario (hostnames, file paths, IPs, log lines,
  usernames, story framing) within the fixed rules of that level, so the underlying
  lesson stays intact but the exact scenario isn't memorizable.

## 6. Features (must-have)

- [ ] Landing page: game intro only (no upfront role pick).
- [ ] Vulnerability Hub: list of 10 OWASP categories, dual exploited/patched status per
      category, clickable in any order.
- [ ] Learn page: per-vulnerability non-spoiler explainer + Exploit/Patch choice.
- [ ] Level view: objective sidebar, terminal, victim PC panel, hints — all four always
      present for every level.
- [ ] Command engine: parses player terminal input, matches against the current level's
      scripted command set, returns output + updates victim PC state + evaluates win
      condition — plus a **patch gate**: deny a Red level's win condition once its paired
      Blue level is already completed in the same session.
- [ ] 20 level definitions (10 Red / 10 Blue) mapped to OWASP Top 10 (2021), ordered by
      increasing difficulty within each track.
- [ ] Scenario Randomizer Agent: Ollama-backed, regenerates a level's variable details
      per playthrough within a schema the command engine still understands.
- [ ] Progress persistence across sessions (local, free storage — see architecture.md).

## 7. Non-goals (out of scope)

- Real exploitation of real hosts/services, real payload execution, real shell access.
- Multiplayer / real-time PvP.
- Native mobile apps.
- Paid infrastructure of any kind (hosting, APIs, models, storage).
- User accounts with full auth/identity system — a lightweight local/session identity is
  enough for a single-player learning tool.
- General-purpose sandboxed VM/container-per-user infrastructure (explicitly rejected in
  favor of the scripted simulation approach — see architecture.md §2 for the reasoning).

## 8. Success criteria

**Educational:** a player who completes a Red/Blue pair of levels for a given OWASP
category can explain, in their own words, how the attack works and how the defense
mitigates it.

**Dissertation/technical:** a working, deployed, free-to-run system covering all 20
levels, with an AI-driven randomization layer, built on a documented, reproducible
architecture that another developer could pick up from `handoff.md` +
`architecture.md` alone.

## 9. Content coverage — OWASP Top 10 (2021) → level pairing

Each category gets one Red (attack) level and one matching Blue (defend) level.
Exact level ordering/difficulty curve is decided in Phase 3 (see `handoff.md`).

1. A01:2021 – Broken Access Control
2. A02:2021 – Cryptographic Failures
3. A03:2021 – Injection
4. A04:2021 – Insecure Design
5. A05:2021 – Security Misconfiguration
6. A06:2021 – Vulnerable and Outdated Components
7. A07:2021 – Identification and Authentication Failures
8. A08:2021 – Software and Data Integrity Failures
9. A09:2021 – Security Logging and Monitoring Failures
10. A10:2021 – Server-Side Request Forgery (SSRF)
