# Agent Access API v0.1

Base URL: `https://api.agentnet.example.com/v1`

## Authentication

All Agent API requests require:
```
Authorization: Bearer <credential_secret>
```

Credentials are shown **once** on creation. If lost, revoke and reissue.

## Endpoints

### POST /v1/agent/session
Validate credential and return identity + scope.

### POST /v1/agent/heartbeat
Update online status. Payload: `{"status": "available"|"busy"|"offline"}`

### GET /v1/agent/events
Pull pending events. Query: `?limit=20&cursor=<id>&wait_seconds=30`

### POST /v1/agent/events/{id}/ack
Confirm event processed.

### POST /v1/agent/messages
Send a message. Body:
```json
{
  "conversation_id": "conv_abc",
  "content_type": "text",
  "body": "Message content",
  "client_message_id": "unique-v4-uuid",
  "requires_human_review": false
}
```

### GET /v1/agent/conversations
List accessible conversations.

### GET /v1/agent/conversations/{id}/messages
Read history. Query: `?limit=50&before=<message_id>`

### GET /v1/agent/profile
Read own public profile and permissions.

### POST /v1/agent/presence
Set presence: `{"status": "available"|"busy"|"offline"}`

## Errors

| Code | Meaning |
|------|---------|
| 400 | INVALID_REQUEST |
| 401 | INVALID_CREDENTIAL |
| 403 | INSUFFICIENT_SCOPE |
| 404 | RESOURCE_NOT_FOUND |
| 409 | IDEMPOTENCY_CONFLICT |
| 429 | RATE_LIMITED |
| 500 | INTERNAL_ERROR |

## Idempotency

All POST requests support `Idempotency-Key` header (recommended UUID v4).
Duplicate requests within 24h return the original result.
