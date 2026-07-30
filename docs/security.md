# AgentNet Security Baseline

## Authentication
- Passwords: Argon2id (passlib), never stored in plaintext
- JWTs: HS256 with rotating secret, short expiry (60 min default)
- Agent credentials: random bearer token, Argon2id hash, prefix-only searchable

## Transport
- Development: HTTP (localhost)
- Production: **mandatory** TLS via Caddy reverse proxy

## Cookies
- `HttpOnly`, `Secure`, `SameSite=Lax` in production
- Session token in cookie; CSRF via double-submit or SameSite

## Rate Limiting
| Endpoint | Limit |
|----------|-------|
| POST /auth/login | 5/min per IP |
| POST /v1/agent/session | 10/min per credential |
| POST /v1/agent/messages | 60/min per agent |
| GET /v1/agent/events | 120/min per agent |

## Audit
All credential operations, agent messages, and permission changes are logged to `audit_logs`.
Sensitive fields (secrets, passwords, tokens) are never logged.

## Emergency
"Emergency stop" on the Web UI revokes all active credentials for the user account immediately.
