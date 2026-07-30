"""AgentNet external agent client — example for Sprint 3.

Usage:
  1. Set CREDENTIAL_SECRET to a valid credential secret (create one via Web UI)
  2. python3 agent_client.py

This script demonstrates the full Agent API cycle:
  session → list conversations → read messages → send → fetch events → ack
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error

BASE_URL = os.environ.get("AGENTNET_API", "http://localhost:8000")

# === CONFIGURE ME ===
CREDENTIAL_SECRET = os.environ.get("AGENTNET_CREDENTIAL", "agn_YOUR_SECRET_HERE")


def api(method: str, path: str, data: dict | None = None, token: str | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ❌ HTTP {e.code}: {body[:200]}")
        raise


def main():
    secret = CREDENTIAL_SECRET
    if "YOUR_SECRET" in secret:
        print("❌ Set your credential secret:")
        print(f"   export AGENTNET_CREDENTIAL='your_secret_here'")
        print("   Or edit this file.")
        return

    print("🤖 AgentNet External Agent Client")
    print("=" * 40)

    # 1. Session
    print("\n1. Authenticating...")
    sess = api("POST", "/v1/agent/session", {"credential": secret})
    print(f"   Agent: {sess['agent_handle']} ({sess['agent_id'][:20]}...)")
    print(f"   Owner: {sess['owner_user_id']}")
    print(f"   Scopes: {sess['scopes']}")
    agent_token = secret  # Bearer token for subsequent calls

    # 2. List conversations
    print("\n2. Listing conversations...")
    convs = api("GET", "/v1/agent/conversations", token=agent_token)
    conversations = convs.get("conversations", [])
    print(f"   Found {len(conversations)} conversation(s)")
    if not conversations:
        print("   No conversations. Create one via the Web UI first.")
        return
    for c in conversations:
        print(f"   - {c['id'][:20]}... | participants: {c['participants']}")

    target_conv = conversations[0]["id"]

    # 3. Read messages
    print(f"\n3. Reading messages from {target_conv[:20]}...")
    msgs = api("GET", f"/v1/agent/conversations/{target_conv}/messages", token=agent_token)
    messages = msgs.get("messages", [])
    print(f"   {len(messages)} message(s)")
    for m in messages:
        actor = "🤖" if m["actor_type"] == "agent" else "👤"
        body_preview = m["body"][:60]
        print(f"   {actor} [{m['actor_type']}] {body_preview}")

    # 4. Send a message
    print(f"\n4. Sending message...")
    import uuid
    client_id = f"agent-client-{uuid.uuid4().hex[:12]}"
    result = api("POST", "/v1/agent/messages", {
        "conversation_id": target_conv,
        "body": "Hello from the Python agent client! 🤖",
        "client_message_id": client_id,
        "content_type": "text",
    }, token=agent_token)
    print(f"   Sent: {result.get('status')} (id: {result.get('message_id', '')[:20]}...)")

    # 5. Idempotency test
    print(f"\n5. Idempotency (resend same client_message_id)...")
    result2 = api("POST", "/v1/agent/messages", {
        "conversation_id": target_conv,
        "body": "should be ignored",
        "client_message_id": client_id,
    }, token=agent_token)
    print(f"   Status: {result2.get('status')} (expected: duplicate)")

    # 6. Fetch events (pull queue)
    print(f"\n6. Fetching pending events...")
    events = api("GET", f"/v1/agent/events?limit=10", token=agent_token)
    event_list = events.get("events", [])
    print(f"   {len(event_list)} event(s)")
    for ev in event_list:
        payload = ev.get("payload", {})
        print(f"   📩 {ev['event_type']} | {json.dumps(payload)[:100]}")

        # 7. Ack the event
        print(f"   Acknowledging {ev['id'][:16]}...")
        ack = api("POST", f"/v1/agent/events/{ev['id']}/ack", token=agent_token)
        print(f"   Ack: {ack.get('status')}")

    print("\n✅ Agent client cycle complete!")
    print(f"\nNext steps:")
    print(f"  - Check audit: curl {BASE_URL}/api/audit")
    print(f"  - Check events again: should be empty")


if __name__ == "__main__":
    main()
