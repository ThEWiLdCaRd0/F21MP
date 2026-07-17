import json
import re
import urllib.error
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"  # exact model choice still open, see architecture.md §5

MAX_FIELD_LENGTH = 64
# Deliberately restrictive: only what an ip/hostname/username placeholder needs.
# Rejects anything with quotes, braces, whitespace, or other characters that could
# break template substitution, JSON structure, or the command engine's string match.
SAFE_FIELD_RE = re.compile(r"^[A-Za-z0-9.\-_]+$")


def _substitute(node, values: dict):
    if isinstance(node, str):
        result = node
        for key, val in values.items():
            result = result.replace("{" + key + "}", val)
        return result
    if isinstance(node, dict):
        return {_substitute(k, values): _substitute(v, values) for k, v in node.items()}
    if isinstance(node, list):
        return [_substitute(item, values) for item in node]
    return node


def _sanitize_field(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > MAX_FIELD_LENGTH:
        return None
    if not SAFE_FIELD_RE.match(value):
        return None
    return value


def _call_ollama(fields: list[str], context: str) -> dict | None:
    schema_example = ", ".join(f'"{f}": "..."' for f in fields)
    prompt = (
        "Return ONLY a JSON object (no prose, no markdown fences) mapping each of "
        f"these field names to a short replacement value in the same style as a real "
        f"example: {fields}. Context: {context}. "
        f"Respond with exactly this shape: {{{schema_example}}}"
    )
    body = json.dumps(
        {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json"}
    ).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read())
        return json.loads(payload["response"])
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, OSError):
        return None


def randomize_level(level: dict) -> dict:
    """Substitute a level's {field} placeholders with AI-generated values.

    Falls back to the level's own `default_values` (i.e. its original, non-randomized
    content) if the randomizer service isn't reachable or returns anything that
    fails sanitization - the level must always stay playable.
    """
    fields = level.get("randomizable_fields", [])
    defaults = level.get("default_values", {})
    if not fields or not defaults:
        return level

    values = dict(defaults)
    context = level.get("title", level.get("id", ""))

    for _ in range(2):  # one try, one retry, then fall back
        raw = _call_ollama(fields, context)
        if raw is None:
            continue
        candidate = {}
        for field in fields:
            cleaned = _sanitize_field(raw.get(field))
            if cleaned is None:
                candidate = None
                break
            candidate[field] = cleaned
        if candidate is not None:
            values.update(candidate)
            break

    return _substitute(level, values)
