#!/usr/bin/env python3
"""AgentNet ClickOps — interactive demo script.
Run:  python3 examples/clickops_demo.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import urllib.error

BASE = os.environ.get("AGENTNET_API", "http://localhost:8000")
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
NC = "\033[0m"


def api(method: str, path: str, data: dict | None = None, token: str | None = None) -> dict:
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def step(n: str, title: str):
    print(f"\n{BOLD}{CYAN}[{n}] {title}{NC}")
    if "--headless" not in sys.argv:
        input(f"  {DIM}Press Enter →{NC} ")
    else:
        print(f"  {DIM}(auto){NC}")


def ok(msg: str):
    print(f"  {GREEN}✓{NC} {msg}")


def main():
    print(f"\n{BOLD}{'='*50}")
    print(f"  AgentNet ClickOps Demo")
    print(f"{'='*50}{NC}")
    print(f"  {DIM}API: {BASE}{NC}")

    step("01", "Register Alice")
    a = api("POST", "/api/auth/register", {"email": "clickops_a@test.dev", "password": "testpass123", "display_name": "ClickOps Alice"})
    a_t, a_i = a["token"], a["user_id"]
    ok(f"Alice: {a_i[:16]}...")

    step("02", "Register Bob")
    b = api("POST", "/api/auth/register", {"email": "clickops_b@test.dev", "password": "testpass123", "display_name": "ClickOps Bob"})
    b_t, b_i = b["token"], b["user_id"]
    ok(f"Bob: {b_i[:16]}...")

    step("03", "Alice creates an Agent")
    ag = api("POST", "/api/agents", {"handle": "clickops-agent", "display_name": "ClickOps Agent"}, token=a_t)
    ok(f"Agent: {ag['handle']} ({ag['id'][:16]}...)")

    step("04", "Issue credential for the Agent")
    cr = api("POST", "/api/credentials", {"agent_id": ag["id"], "name": "clickops-key"}, token=a_t)
    secret = cr["secret"]
    ok(f"Secret (show once): {secret[:20]}...")

    step("05", "Agent authenticates via session")
    sess = api("POST", "/v1/agent/session", {"credential": secret})
    ok(f"Session: {sess['agent_handle']} with {len(sess['scopes'])} scope(s)")

    step("06", "Bob sends Alice a contact request")
    c = api("POST", "/api/contacts/request", {"addressee_user_id": a_i}, token=b_t)
    cid = c["contact_id"]
    ok(f"Contact ID: {cid}")

    step("07", "Alice accepts")
    api("POST", f"/api/contacts/{cid}/accept", {}, token=a_t)
    ok("Accepted")

    step("08", "Alice creates a conversation")
    cv = api("POST", "/api/conversations", {"participant_user_id": b_i}, token=a_t)
    cvid = cv["conversation_id"]
    ok(f"Conversation: {cvid[:16]}...")

    step("09", "Alice sends a message")
    api("POST", "/api/messages", {"conversation_id": cvid, "body": "Hey Bob, Alice here!", "client_message_id": f"{cvid}-cm1"}, token=a_t)
    ok("Message sent")

    step("10", "Agent reads the conversation")
    msgs = api("GET", f"/v1/agent/conversations/{cvid}/messages", token=secret)
    ok(f"Agent reads {len(msgs['messages'])} message(s)")
    for m in msgs["messages"]:
        print(f"    {DIM}{m['actor_type']}: {m['body'][:60]}{NC}")

    step("11", "Agent replies")
    api("POST", "/v1/agent/messages", {"conversation_id": cvid, "body": "Hello from the agent! 🤖", "client_message_id": f"{cvid}-cm2"}, token=secret)
    ok("Agent replied")

    step("12", "Bob reads all messages")
    msgs2 = api("GET", f"/api/conversations/{cvid}/messages", token=b_t)
    ok(f"Bob sees {len(msgs2['messages'])} messages")

    step("13", "Check pending events for the agent")
    evts = api("GET", "/v1/agent/events?limit=5", token=secret)
    ok(f"{len(evts.get('events',[]))} pending event(s)")
    for e in evts.get("events", []):
        api("POST", f"/v1/agent/events/{e['id']}/ack", {}, token=secret)
        ok(f"Acked {e['id'][:16]}")

    step("14", "Security: set automation to auto")
    api("PATCH", f"/api/security/agents/{ag['id']}/automation", {"automation_level": "auto"}, token=a_t)
    ok("Automation = auto")

    step("15", "System status")
    st = api("GET", "/api/admin/status", token=a_t)
    c = st["counts"]
    ok(f"Users: {c['users']} | Agents: {c['agents']} | Messages: {c['messages']} | Audit: {c['audit_logs']}")

    step("16", "Grand finale: Audit trail")
    au = api("GET", "/api/audit", token=a_t)
    ok(f"{len(au)} audit entries recorded")

    print(f"\n{BOLD}{GREEN}{'='*50}")
    print(f"  ✅ All 16 demo steps completed!")
    print(f"{'='*50}{NC}")
    print(f"\n  Web UI: {BASE.replace(':8000', ':3000')}")
    print(f"  API:    {BASE}/docs")


if __name__ == "__main__":
    main()
