#!/usr/bin/env python3
"""AgentNet Sprint 1 verification: full register→agent→credential→session→revoke→rotate chain."""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = "http://localhost:8000"
passed = 0
failed = 0


def api(method: str, path: str, data: dict | None = None, token: str | None = None) -> dict:
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def check(label: str, ok: bool):
    global passed, failed
    if ok:
        print(f"  ✅ {label}")
        passed += 1
    else:
        print(f"  ❌ {label}")
        failed += 1


def main():
    global passed, failed
    print("AgentNet Sprint 1 Verification")

    # 1. Health
    h = api("GET", "/health")
    check("Health endpoint", h.get("status") == "ok")

    # 2. Register
    reg = api("POST", "/api/auth/register", {
        "email": "verify@agentnet.dev",
        "password": "testpass123",
        "display_name": "Verify User",
    })
    token = reg.get("token", "")
    check("Register returns token", bool(token))
    user_id = reg.get("user_id", "")
    check("Register returns user_id", bool(user_id))

    # 3. Me
    me = api("GET", "/api/auth/me", token=token)
    check("GET /me returns email", me.get("email") == "verify@agentnet.dev")

    # 4. Create Agent
    agent = api("POST", "/api/agents", {"handle": "verify-agent", "display_name": "Verify Agent"}, token=token)
    agent_id = agent.get("id", "")
    check("Create Agent returns id", bool(agent_id))
    check("Agent handle correct", agent.get("handle") == "verify-agent")

    # 5. List Agents
    agents = api("GET", "/api/agents", token=token)
    check("List Agents non-empty", len(agents.get("agents", [])) > 0)

    # 6. Create Credential
    cred = api("POST", "/api/credentials", {
        "agent_id": agent_id,
        "name": "verify-key",
        "scopes": "profile:read,messages:read,messages:send",
    }, token=token)
    secret = cred.get("secret", "")
    cred_id = cred.get("id", "")
    check("Credential shows secret once", bool(secret))
    check("Credential has prefix", bool(cred.get("prefix", "")))

    # 7. Agent Session
    sess = api("POST", "/v1/agent/session", {"credential": secret})
    check("Agent session returns agent_id", bool(sess.get("agent_id")))
    check("Agent session scopes non-empty", len(sess.get("scopes", [])) > 0)

    # 8. Agent Profile
    prof = api("GET", "/v1/agent/profile", token=secret)
    check("Agent profile returns handle", prof.get("handle") == "verify-agent")

    # 9. Revoke
    rev = api("POST", f"/api/credentials/{cred_id}/revoke", {}, token=token)
    check("Revoke returns status revoked", rev.get("status") == "revoked")

    # 10. Session after revoke fails
    fail = api("POST", "/v1/agent/session", {"credential": secret})
    check("Revoked session returns 401", "INVALID_CREDENTIAL" in str(fail.get("detail", "")))

    # 11. Rotate
    rot = api("POST", f"/api/credentials/{cred_id}/rotate", {}, token=token)
    new_secret = rot.get("secret", "")
    check("Rotate returns new secret", bool(new_secret) and new_secret != secret)

    # 12. Session with rotated
    rot_sess = api("POST", "/v1/agent/session", {"credential": new_secret})
    check("Rotated session works", bool(rot_sess.get("agent_id")))

    # Summary
    total = passed + failed
    print(f"\n{'='*40}")
    print(f"Result: {passed}/{total} passed")
    if failed:
        print(f"WARNING: {failed} failed")
        sys.exit(1)
    else:
        print("Sprint 1: ALL PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
