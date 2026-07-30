# AgentNet BACKLOG — Sprint 0 → 5

## Sprint 0: Engineering Bootstrap

**Goal:** Launch project — one command starts everything; /health returns 200.

- [x] S0-01 Create directory structure
- [x] S0-02 Write ADR-0001 (modular monolith)
- [x] S0-03 Core files: .gitignore, README, LICENSE, CHANGELOG, .env.example, Makefile
- [ ] S0-04 Docker Compose: PostgreSQL 16 + Redis 7 + API + Web
- [ ] S0-05 FastAPI project: module skeleton, /health, pytest
- [ ] S0-06 Next.js project: Tailwind, empty page, health check to API
- [ ] S0-07 Scripts: dev-up, dev-down, backup.sh, env verification
- [ ] S0-08 CI: GitHub Actions template, linting baseline
- [ ] S0-09 infra: Caddy reverse proxy config template
- [ ] S0-10 docs: security.md, api/agent-api-v0.1.md
- [ ] S0-11 Validation: local `make dev-up` → curl /health returns ok

## Sprint 1: Identity & Credentials

**Goal:** Register user → create Agent → issue credential → curl API auth.

- [ ] US-01 Register/login/logout (email + password, Argon2id, JWT)
- [ ] US-02 Agent CRUD (handle, display_name, unique handle validation)
- [ ] US-03 Credential create/show-once/list/revoke/rotate
- [ ] US-04 Scope model + scope assignment to credentials
- [ ] US-05 POST /v1/agent/session (validate credential → return identity + scope)
- [ ] US-06 Web: registration page + login + dashboard shell
- [ ] US-07 Web: Agent management page + credential management page
- [ ] US-08 Web: developer page (API URL, curl examples)
- [ ] US-09 Test: credential auth flow end-to-end
- [ ] US-10 Audit log: credential operations

## Sprint 2: Contacts & Messaging

**Goal:** Two accounts can chat in real-time with history.

- [ ] US-05 Contact request/accept/reject/delete state machine
- [ ] US-06 Conversation creation + member management
- [ ] US-07 Message persistence (client_message_id unique, idempotency)
- [ ] US-08 WebSocket: live message push to frontend
- [ ] US-09 History pagination (cursor-based)
- [ ] US-10 Web: contacts list + add/search
- [ ] US-11 Web: conversation list + chat UI
- [ ] US-12 Test: two-browser chat e2e, persistence verification

## Sprint 3: Agent Closed Loop

**Goal:** External agent can read events and send messages.

- [ ] US-07 Agent event queue (agent_events table, pull + ack)
- [ ] US-08 GET /v1/agent/events (limit, cursor, wait_seconds)
- [ ] US-09 POST /v1/agent/events/{id}/ack
- [ ] US-10 POST /v1/agent/messages (with actor=agent, idempotency)
- [ ] US-11 GET /v1/agent/conversations and /conversations/{id}/messages
- [ ] US-12 Agent heartbeat / presence
- [ ] Example client: Python script that authenticates and sends a message
- [ ] Audit: agent message origin tracing
- [ ] Test: external agent completes send-receive loop

## Sprint 4: Permissions & Security

**Goal:** Granular control, rate limiting, emergency stop.

- [ ] US-04 Automation levels (L0-L2, MVP)
- [ ] US-04 Permission enforcement middleware (scope checks on every API call)
- [ ] US-09 Emergency stop (revoke all credentials)
- [ ] Rate limiting per endpoint (login, credential, message, event)
- [ ] Security middleware: XSS, SQL injection, CORS, helmet
- [ ] Web: permissions center + automation level selector
- [ ] Web: audit log page with filters
- [ ] Backup: auto daily + restore verification script
- [ ] Web: emergency stop button

## Sprint 5: Public Test Release

**Goal:** Founder can invite first 20-100 testers.

- [ ] Developer docs: API v0.1 spec, curl/SDK examples
- [ ] Example agent client: full Python SDK
- [ ] Admin endpoints: user management, system metrics
- [ ] Deployment playbook: fresh deploy from zero
- [ ] Demo accounts: pre-seeded test users with example agents
- [ ] OpenAPI docs auto-published
- [ ] Changelog + migration guide for Sprint 0→5
