"""Generic tool interpreter - Phase 3.5 prototype.

Problem this solves: today every level's *recognized* commands are either an
exact literal string or a hand-authored regex (`command_patterns`). That's
fine for a level's *win condition* (it should stay exact - see rules.md's hard
rule and architecture.md §4), but it means generic recon commands like `nmap`
or `ps aux` only ever "work" if a level author happened to script that exact
command for that exact level. Anything else falls through to "command not
recognized" even though a real target would have answered.

This module adds a **read-only, generic interpretation layer** for common
recon/inspection commands. It never decides a win condition and never changes
`victim_pc_state` - it only *renders* the state that already exists (services,
files, logs) into realistic tool-shaped output, the same way a real `nmap` or
`ps aux` would just reflect whatever is actually running on a box.

Still pure string generation, still never `subprocess`/`eval`/a real shell -
same hard rule as command_engine.py, this is just a smarter formatter.

Wiring: command_engine.run_command tries this ONLY as a fallback, after the
literal `commands` dict and `command_patterns` have both already had a chance
to match and (potentially) win the level. So a level author's specific,
authored win-condition command always takes priority; this only fills the gap
for everything else a player might reasonably type.
"""

import re

# Best-effort service -> (port, banner) table for realistic nmap-style output.
# Deliberately small and hand-maintained (rules.md: no premature abstraction) -
# extend this table, not the matching logic, when a level introduces a new
# service name.
SERVICE_PROFILES: dict[str, tuple[int, str]] = {
    "apache2": (80, "Apache httpd 2.4.41 ((Ubuntu))"),
    "nginx": (80, "nginx 1.18.0 (Ubuntu)"),
    "mysql": (3306, "MySQL 5.7.31-0ubuntu0.18.04.1"),
    "tomcat": (8080, "Apache Tomcat/Coyote JSP engine 1.1"),
    "ssh": (22, "OpenSSH 7.6p1 Ubuntu 4ubuntu0.7"),
    "postgres": (5432, "PostgreSQL DB 11.5"),
    "redis": (6379, "Redis key-value store 5.0.7"),
    "mongo": (27017, "MongoDB 4.0.19"),
    "audit-logging": (None, "internal service - no listening port"),
    "ftp": (21, "vsftpd 3.0.3"),
}

_FALLBACK_PORT_START = 8100  # deterministic-but-plausible port for unknown services


def _profile(service: str) -> tuple[int | None, str]:
    if service in SERVICE_PROFILES:
        return SERVICE_PROFILES[service]
    # Unknown service name (a level author added something new): still render
    # *something* plausible rather than silently omitting it from the scan -
    # a real nmap wouldn't skip a port just because our table doesn't know it.
    port = _FALLBACK_PORT_START + (hash(service) % 50)
    return port, f"{service} (unrecognized service - generic banner)"


def _nmap(ip: str, state: dict) -> str:
    services = state.get("services", [])
    rows = []
    for svc in services:
        port, banner = _profile(svc)
        if port is None:
            continue  # not network-facing, a real nmap wouldn't list it either
        rows.append((port, svc, banner))
    rows.sort(key=lambda r: r[0])

    lines = [
        "Starting Nmap 7.94 ( https://nmap.org ) at 2026-07-22 10:00 UTC",
        f"Nmap scan report for {ip}",
        "Host is up (0.0021s latency).",
        "",
    ]
    if rows:
        lines.append("PORT     STATE SERVICE  VERSION")
        for port, svc, banner in rows:
            lines.append(f"{port}/tcp".ljust(9) + "open  " + svc.ljust(9) + banner)
    else:
        lines.append("All 1000 scanned ports on {ip} are in ignored state".format(ip=ip))
    lines += ["", "Nmap done: 1 IP address (1 host up) scanned in 1.38 seconds"]
    return "\n".join(lines)


def _ps(state: dict) -> str:
    services = state.get("services", [])
    header = f"{'USER':<8}{'PID':<8}{'%CPU':<6}{'%MEM':<6}COMMAND"
    lines = [header]
    for i, svc in enumerate(services):
        pid = 1000 + i * 37  # deterministic, not random - stable across repeated calls
        lines.append(f"{'root':<8}{pid:<8}{'0.1':<6}{'0.4':<6}/usr/sbin/{svc}")
    return "\n".join(lines)


def _service_status(state: dict) -> str:
    services = state.get("services", [])
    if not services:
        return "No services currently running."
    return "\n".join(f" [ + ]  {svc}" for svc in services)


def _ls(path: str, state: dict) -> str:
    files = state.get("files", [])
    matches = [f for f in files if f.startswith(path.rstrip("/"))]
    if not matches:
        return f"ls: cannot access '{path}': No such file or directory"
    return "\n".join(matches)


def _cat(path: str, state: dict) -> str | None:
    files = state.get("files", [])
    if path not in files:
        return f"cat: {path}: No such file or directory"
    # We model *existence*, not byte-for-byte contents - a real file's actual
    # content (creds, source code) stays part of a level's authored win
    # condition (curl/sqlmap/etc against it), not something generic `cat`
    # should be able to dump for free. This keeps the win path exact, per
    # rules.md, while still giving a truthful, non-spoiling response instead
    # of a flat 404.
    return f"cat: {path}: Permission denied (or binary file - use the application's own interface to read this)"


# Registry of generic command patterns this module understands, tried in
# order. Each handler returns the rendered string, or None to mean "shape
# matched but not enough to answer" (currently unused, kept for extension).
_GENERIC_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"nmap(?:\s+-\S+)*\s+(?P<ip>[\w.\-{}]+)$"), "nmap"),
    (re.compile(r"ps\s+aux$"), "ps"),
    (re.compile(r"service\s+--status-all$"), "service_status"),
    (re.compile(r"systemctl\s+list-units.*"), "service_status"),
    (re.compile(r"ls(?:\s+-\w+)?\s+(?P<path>\S+)$"), "ls"),
    (re.compile(r"cat\s+(?P<path>\S+)$"), "cat"),
]


def try_generic_tool(normalized_command: str, state: dict) -> str | None:
    """Entry point called by command_engine as the final fallback tier.

    Returns rendered output for a recognized *generic* command shape, or None
    if nothing here matches (caller then falls through to "command not
    recognized", same as today).
    """
    for pattern, kind in _GENERIC_PATTERNS:
        match = pattern.fullmatch(normalized_command)
        if match is None:
            continue
        groups = match.groupdict()
        if kind == "nmap":
            return _nmap(groups["ip"], state)
        if kind == "ps":
            return _ps(state)
        if kind == "service_status":
            return _service_status(state)
        if kind == "ls":
            return _ls(groups["path"], state)
        if kind == "cat":
            return _cat(groups["path"], state)
    return None
