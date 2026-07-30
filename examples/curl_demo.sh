# AgentNet — Complete curl Examples
# Usage: bash examples/curl_demo.sh
# Run this script to demonstrate every major API endpoint.

API="${AGENTNET_API:-http://localhost:8000}"
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}━━━ AgentNet API Demo ━━━${NC}"
echo ""

# ── Setup: Register two users ──
echo -e "${BOLD}1. Register Users${NC}"
A=$(curl -s -X POST "$API/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo1@test.dev","password":"testpass123","display_name":"Demo Alice"}')
A_TOKEN=$(echo "$A" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
A_ID=$(echo "$A" | python3 -c "import sys,json; print(json.load(sys.stdin)['user_id'])")
echo "   Alice: $A_ID"

B=$(curl -s -X POST "$API/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo2@test.dev","password":"testpass123","display_name":"Demo Bob"}')
B_TOKEN=$(echo "$B" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
B_ID=$(echo "$B" | python3 -c "import sys,json; print(json.load(sys.stdin)['user_id'])")
echo "   Bob:   $B_ID"

# ── Auth ──
echo -e "\n${BOLD}2. Login & Profile${NC}"
curl -s -X POST "$API/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo1@test.dev","password":"testpass123"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('   Login token:', d['token'][:20],'...')"

curl -s "$API/api/auth/me" \
  -H "Authorization: Bearer $A_TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('   Me:', d['email'])"

# ── Agents ──
echo -e "\n${BOLD}3. Agent CRUD${NC}"
AGENT=$(curl -s -X POST "$API/api/agents" \
  -H "Authorization: Bearer $A_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"handle":"demo-alice-agent","display_name":"Alice Agent"}')
AGENT_ID=$(echo "$AGENT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "   Created: $AGENT_ID"

curl -s "$API/api/agents" -H "Authorization: Bearer $A_TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('   List:', len(d['agents']), 'agent(s)')"

# ── Credentials ──
echo -e "\n${BOLD}4. Credentials${NC}"
CRED=$(curl -s -X POST "$API/api/credentials" \
  -H "Authorization: Bearer $A_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\":\"$AGENT_ID\",\"name\":\"demo-key\",\"scopes\":\"profile:read,messages:read,messages:send\"}")
SECRET=$(echo "$CRED" | python3 -c "import sys,json; print(json.load(sys.stdin)['secret'])")
echo "   Secret (show once): ${SECRET:0:16}..."

# ── Agent Session ──
echo -e "\n${BOLD}5. Agent API${NC}"
curl -s -X POST "$API/v1/agent/session" \
  -H "Content-Type: application/json" \
  -d "{\"credential\":\"$SECRET\"}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('   Agent:', d['agent_handle'], 'Scopes:', d['scopes'])"

# ── Contacts ──
echo -e "\n${BOLD}6. Contacts${NC}"
CONTACT=$(curl -s -X POST "$API/api/contacts/request" \
  -H "Authorization: Bearer $B_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"addressee_user_id\":\"$A_ID\"}")
CID=$(echo "$CONTACT" | python3 -c "import sys,json; print(json.load(sys.stdin)['contact_id'])")
echo "   Request sent: $CID"
curl -s -X POST "$API/api/contacts/$CID/accept" \
  -H "Authorization: Bearer $A_TOKEN" > /dev/null
echo "   Accepted"

# ── Conversation + Messages ──
echo -e "\n${BOLD}7. Messages${NC}"
CONV=$(curl -s -X POST "$API/api/conversations" \
  -H "Authorization: Bearer $A_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"participant_user_id\":\"$B_ID\"}")
CVID=$(echo "$CONV" | python3 -c "import sys,json; print(json.load(sys.stdin)['conversation_id'])")
echo "   Conversation: $CVID"

curl -s -X POST "$API/api/messages" \
  -H "Authorization: Bearer $A_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"conversation_id\":\"$CVID\",\"body\":\"Hello Bob!\",\"client_message_id\":\"${CVID}-m1\"}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('   Sent:', d['status'])"

curl -s "$API/api/conversations/$CVID/messages" \
  -H "Authorization: Bearer $B_TOKEN" \
  | python3 -c "import sys,json; msgs=json.load(sys.stdin)['messages']; print('   Read:', len(msgs), 'message(s)')"

# ── Security ──
echo -e "\n${BOLD}8. Security${NC}"
echo "   Automation: $(curl -s "$API/api/security/agents/$AGENT_ID/automation" -H "Authorization: Bearer $A_TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['automation_level'])")"
curl -s -X PATCH "$API/api/security/agents/$AGENT_ID/automation" \
  -H "Authorization: Bearer $A_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"automation_level":"auto"}' > /dev/null
echo "   → Set to auto"

echo -e "\n${BOLD}9. Events${NC}"
curl -s "$API/v1/agent/events?limit=5" -H "Authorization: Bearer $SECRET" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('   Events:', len(d.get('events',[])))"

# ── Audit ──
echo -e "\n${BOLD}10. Audit${NC}"
curl -s "$API/api/audit" -H "Authorization: Bearer $A_TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('   Entries:', len(d))"

# ── System Status ──
echo -e "\n${BOLD}11. System Status${NC}"
curl -s "$API/api/admin/status" -H "Authorization: Bearer $A_TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); c=d['counts']; print(f'   Users: {c[\"users\"]} | Agents: {c[\"agents\"]} | Msgs: {c[\"messages\"]}')"

# ── Cleanup ──
echo -e "\n${BOLD}12. Teardown${NC}"
curl -s -X DELETE "$API/api/messages/" \
  -H "Authorization: Bearer $A_TOKEN" > /dev/null 2>&1 || true

echo -e "\n${BOLD}━━━ Demo Complete ━━━${NC}"
