import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from app.db import get_connection
from app.services import randomizer, tool_engine

LEVELS_DIR = Path(__file__).parent.parent / "levels"
INTROS_PATH = LEVELS_DIR / "vulnerability_intros.json"

REQUIRED_LEVEL_KEYS = [
    "id", "role", "order", "owasp_category", "title", "difficulty",
    "objective", "briefing", "hints", "debrief", "victim_pc_initial_state",
    "commands", "randomizable_fields",
]

_levels: dict[str, dict] | None = None
_intros: dict[str, str] | None = None
_session_state: dict[tuple[str, str], dict] = {}
_materialized_levels: dict[tuple[str, str], dict] = {}


def _load_levels() -> dict[str, dict]:
    levels = {}
    for pattern in ("red-*.json", "blue-*.json"):
        for path in LEVELS_DIR.glob(pattern):
            data = json.loads(path.read_text(encoding="utf-8"))
            missing = [key for key in REQUIRED_LEVEL_KEYS if key not in data]
            if missing:
                raise ValueError(f"{path.name}: missing required key(s): {missing}")
            levels[data["id"]] = data
    return levels


def get_levels() -> dict[str, dict]:
    global _levels
    if _levels is None:
        _levels = _load_levels()
    return _levels


def get_level(level_id: str) -> dict | None:
    return get_levels().get(level_id)


def get_intros() -> dict[str, str]:
    global _intros
    if _intros is None:
        _intros = json.loads(INTROS_PATH.read_text(encoding="utf-8"))
    return _intros


def _paired_level_id(level_id: str) -> str:
    """The other side's level for the same vulnerability - red/blue level ids share
    everything after the role prefix (e.g. red-01-x <-> blue-01-x)."""
    role, rest = level_id.split("-", 1)
    return f"{'blue' if role == 'red' else 'red'}-{rest}"


def get_vulnerabilities(session_id: str) -> list[dict]:
    by_category: dict[str, dict] = {}
    for level in get_levels().values():
        entry = by_category.setdefault(level["owasp_category"], {"order": level["order"]})
        entry[f"{level['role']}_level_id"] = level["id"]

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT level_id FROM progress WHERE session_id = ? AND completed_at IS NOT NULL",
            (session_id,),
        ).fetchall()
    completed = {row["level_id"] for row in rows}

    intros = get_intros()
    vulnerabilities = [
        {
            "owasp_category": category,
            "order": entry["order"],
            "intro": intros.get(category, ""),
            "red_level_id": entry["red_level_id"],
            "blue_level_id": entry["blue_level_id"],
            "exploited": entry["red_level_id"] in completed,
            "patched": entry["blue_level_id"] in completed,
        }
        for category, entry in by_category.items()
    ]
    vulnerabilities.sort(key=lambda v: v["order"])
    return vulnerabilities


def _is_patched(session_id: str, level: dict) -> bool:
    """A Red level's exploit is denied once its paired Blue level has been won in
    this session - see architecture.md #4a. Blue levels are never gated."""
    if level["role"] != "red":
        return False
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM progress WHERE session_id = ? AND level_id = ? AND completed_at IS NOT NULL",
            (session_id, _paired_level_id(level["id"])),
        ).fetchone()
    return row is not None


def get_level_for_session(session_id: str, level_id: str) -> dict | None:
    """The level a specific session sees - placeholders substituted once and cached,
    so a session's briefing/hints and its command matching always agree, even
    across multiple commands within the same level attempt."""
    level = get_level(level_id)
    if level is None:
        return None
    key = (session_id, level_id)
    if key not in _materialized_levels:
        _materialized_levels[key] = randomizer.randomize_level(level)
    return _materialized_levels[key]


def _normalize(command: str) -> str:
    return re.sub(r"\s+", " ", command.strip())


def _parse_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_version(text: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", text or "")
    return tuple(int(x) for x in match.groups()) if match else None


def _check_regex(captured: dict, field: str, pattern: str, flags: str = "") -> dict | None:
    """Does `field` look like <shape>? e.g. a JNDI lookup, a PHP-serialized object,
    a SQLi tautology - any named groups in `pattern` are merged in for templating."""
    value = captured.get(field) or ""
    match = re.search(pattern, value, re.IGNORECASE if "i" in flags else 0)
    if match is None:
        return None
    return {k: v for k, v in match.groupdict().items() if v is not None}


def _check_int_cmp(captured: dict, field: str, op: str, value: int) -> dict | None:
    n = _parse_int(captured.get(field))
    if n is None:
        return None
    ops = {"lt": n < value, "le": n <= value, "gt": n > value, "ge": n >= value, "eq": n == value, "ne": n != value}
    return {} if ops[op] else None


def _check_int_derive(captured: dict, field: str, factor: int, into: str) -> dict | None:
    """Always succeeds if `field` parses as an int - computes into = |field| * factor,
    e.g. the credited amount for whatever quantity the player actually sent."""
    n = _parse_int(captured.get(field))
    return None if n is None else {into: f"{abs(n) * factor:.2f}"}


def _check_md5_matches(captured: dict, field: str, target: str) -> dict | None:
    return {} if hashlib.md5((captured.get(field) or "").encode()).hexdigest() == target else None


def _check_version_ge(captured: dict, field: str, threshold: str) -> dict | None:
    version = _parse_version(captured.get(field))
    return {} if version is not None and version >= _parse_version(threshold) else None


CHECKS = {
    "regex": _check_regex,
    "int_cmp": _check_int_cmp,
    "int_derive": _check_int_derive,
    "md5_matches": _check_md5_matches,
    "version_ge": _check_version_ge,
}


def _case_matches(case: dict, captured: dict) -> dict | None:
    when = case.get("when")
    if when and any(captured.get(k) != v for k, v in when.items()):
        return None
    values = dict(captured)
    for spec in case.get("checks", []):
        extra = CHECKS[spec["name"]](values, **spec.get("args", {}))
        if extra is None:
            return None
        values.update(extra)
    return values


def _match_pattern(level: dict, normalized: str) -> dict | None:
    """Fallback for commands that are the right *shape* but not a literal in
    `commands` - e.g. any numeric invoice id, any password guess, any log4j version.
    Regexes and checks are plain data on the level (see architecture.md §4); cases
    are tried in order, the first whose `when`/`checks` all pass wins, and a case
    with neither is a catch-all default. Case fields may reference a captured group
    (or a value a check derived, like a computed charge) as `{name}`."""
    for pattern in level.get("command_patterns", []):
        match = re.fullmatch(pattern["regex"], normalized)
        if match is None:
            continue
        captured = {k: (v or "") for k, v in match.groupdict().items()}
        for case in pattern.get("cases", []):
            values = _case_matches(case, captured)
            if values is not None:
                return randomizer._substitute(case, values)
    return None


def _get_state(session_id: str, level_id: str, level: dict) -> dict:
    key = (session_id, level_id)
    if key not in _session_state:
        _session_state[key] = json.loads(json.dumps(level["victim_pc_initial_state"]))
    return _session_state[key]


def _apply_state_change(state: dict, change: dict) -> dict:
    new_state = {**state}
    for key, value in change.items():
        if key.endswith("_append"):
            field = key[: -len("_append")]
            new_state[field] = [*new_state.get(field, []), *value]
        else:
            new_state[key] = value
    return new_state


def _record_attempt(session_id: str, level_id: str, won: bool) -> None:
    completed_at = datetime.now(timezone.utc).isoformat() if won else None
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO progress (session_id, level_id, attempts, completed_at)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(session_id, level_id) DO UPDATE SET
                attempts = attempts + 1,
                completed_at = COALESCE(progress.completed_at, excluded.completed_at)
            """,
            (session_id, level_id, completed_at),
        )


def run_command(level_id: str, session_id: str, command: str) -> dict:
    level = get_level_for_session(session_id, level_id)
    if level is None:
        raise KeyError(level_id)

    state = _get_state(session_id, level_id, level)
    normalized = _normalize(command)

    match = next(
        (result for pattern, result in level["commands"].items() if _normalize(pattern) == normalized),
        None,
    )
    if match is None:
        match = _match_pattern(level, normalized)

    if match is None:
        # Final fallback: a generic, read-only tool interpreter (nmap/ps/ls/cat
        # style) rendered from the level's *actual current* victim_pc_state.
        # Never sets wins_level and never changes state - it only narrates
        # what's already there, so it can't interfere with a level's authored
        # win condition (see tool_engine.py's module docstring).
        generic_output = tool_engine.try_generic_tool(normalized, state)
        if generic_output is not None:
            return {
                "terminal_output": generic_output,
                "victim_pc_state": state,
                "wins_level": False,
            }
        return {
            "terminal_output": f"command not recognized: {command}",
            "victim_pc_state": state,
            "wins_level": False,
        }

    if match.get("wins_level") and _is_patched(session_id, level):
        _record_attempt(session_id, level_id, False)
        return {
            "terminal_output": "Access denied - this target was already patched earlier this session.",
            "victim_pc_state": state,
            "wins_level": False,
        }

    new_state = _apply_state_change(state, match.get("state_change", {}))
    _session_state[(session_id, level_id)] = new_state
    won = bool(match.get("wins_level", False))
    _record_attempt(session_id, level_id, won)

    return {
        "terminal_output": match["output"],
        "victim_pc_state": new_state,
        "wins_level": won,
        "debrief": level["debrief"] if won else None,
    }
