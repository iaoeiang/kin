# ADR-0001: Modular Monolith Architecture

**Status:** Accepted  
**Date:** 2026-07-27  
**Author:** Hermes (Founder CTO)

## Context

AgentNet MVP requires a fast, deployable, and auditable architecture. The founders specified modular monolith with clear domain boundaries.

## Decision

### Architecture

- **Pattern:** Modular monolith with explicit domain directories and interfaces
- **Deployment:** Single Docker Compose stack (PostgreSQL + Redis + API + Web)
- **Future split:** Interfaces between modules are well-defined to allow future extraction into microservices

### Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | FastAPI + Python 3.12 | Async native, OpenAPI auto-gen, high productivity |
| Frontend | Next.js + TypeScript + Tailwind CSS | Full-stack React with SSR, type safety |
| Database | PostgreSQL 16 | Mature, asyncpg support, JSONB for audit payloads |
| Cache/State | Redis 7 | Message queue for agent events, session cache |
| Realtime | WebSocket (frontend), REST long-poll (Agent API) | Agent runtime compatibility first |
| Proxy/TLS | Caddy | Auto HTTPS, simple config |
| Container | Docker + Docker Compose | Single-node MVP, repeatable deploy |
| Migrations | Alembic | Python-native, async support required |

### Authentication & Credentials

- Human users: email + password (Argon2id), JWT session
- Agent credentials: opaque bearer token, Argon2id hash stored, prefix for lookup
- Credentials shown once on creation; database stores only hash + prefix

### Message Model

- Messages persist to PostgreSQL before any notification
- WebSocket pushes to live human clients
- Agent event queue in Postgres (pull + ack); Redis optional for hot events
- Idempotency via client_message_id + unique constraint

### Module Structure (Backend)

```
apps/agent-api/
  agentnet/
    auth/       # JWT + session
    users/      # Human user CRUD
    agents/     # Agent identity CRUD
    credentials/# Credential lifecycle
    permissions/# Scope + automation level
    contacts/   # Contact request/accept/reject
    conversations/ # Session management
    messages/   # Message CRUD + WebSocket
    events/     # Agent event queue
    audit/      # Audit logging
    admin/      # Admin utilities
    common/     # Shared models, db, config
```

## Consequences

- Single binary deployment is simpler but limits horizontal scaling
- Module boundaries enable independent evolution
- Future microservice extraction requires no semantic refactor
