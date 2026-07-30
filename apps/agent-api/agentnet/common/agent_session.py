"""Agent session — POST /v1/agent/session and related endpoints.

NOTE: Uses lazy imports inside functions to avoid circular imports
with events/routes.py and audit/service.py.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from passlib.hash import argon2
from pydantic import BaseModel
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentnet.common.crypto import encrypt_body, decrypt_body
from agentnet.common.config import settings

from agentnet.common.database import get_db

router = APIRouter(prefix="/v1/agent", tags=["agent-api"])


class SessionRequest(BaseModel):
    credential: str


class SessionResponse(BaseModel):
    agent_id: str
    agent_handle: str
    agent_name: str
    owner_user_id: str
    scopes: list[str]
    server_time: str


class ProfileResponse(BaseModel):
    agent_id: str
    handle: str
    display_name: str
    status: str
    scopes: list[str]


async def authenticate_credential(
    credential: str,
    db: AsyncSession,
) -> tuple:
    """Validate credential secret and return (cred, agent)."""
    from agentnet.common.models import Agent, AgentCredential

    prefix = credential[:12]
    result = await db.execute(
        select(AgentCredential).where(
            AgentCredential.prefix == prefix,
            AgentCredential.status == "active",
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=401, detail="INVALID_CREDENTIAL")

    if cred.revoked_at:
        raise HTTPException(status_code=401, detail="INVALID_CREDENTIAL")

    if cred.expires_at and cred.expires_at < datetime.now(timezone.utc):
        cred.status = "expired"
        raise HTTPException(status_code=401, detail="CREDENTIAL_EXPIRED")

    if not argon2.verify(credential, cred.secret_hash):
        raise HTTPException(status_code=401, detail="INVALID_CREDENTIAL")

    result = await db.execute(select(Agent).where(Agent.id == cred.agent_id))
    agent = result.scalar_one_or_none()
    if not agent or agent.status != "active":
        raise HTTPException(status_code=403, detail="AGENT_INACTIVE")

    return cred, agent


async def get_credential_dep(
    authorization: str = Header(""),
) -> tuple:
    """Dependency: async generator that yields (cred, agent)."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_CREDENTIAL")

    from agentnet.common.database import get_db as _get_db

    async for session in _get_db():
        try:
            return await authenticate_credential(authorization[7:], session)
        finally:
            pass  # session managed by get_db context


@router.post("/session", response_model=SessionResponse)
async def agent_session(req: SessionRequest, db: AsyncSession = Depends(get_db)):
    cred, agent = await authenticate_credential(req.credential, db)
    cred.last_used_at = datetime.now(timezone.utc)
    await db.flush()
    scopes = [s.strip() for s in cred.scopes.split(",") if s.strip()]
    return SessionResponse(
        agent_id=agent.id,
        agent_handle=agent.handle,
        agent_name=agent.display_name,
        owner_user_id=agent.owner_user_id,
        scopes=scopes,
        server_time=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/profile", response_model=ProfileResponse)
async def agent_profile(
    cred_agent: tuple = Depends(get_credential_dep),
    db: AsyncSession = Depends(get_db),
):
    _cred, agent = cred_agent
    result = await db.execute(
        select().__select__(
            from_obj=None  # placeholder — will be replaced
        )
    )
    # Get all active credentials for this agent's scopes
    from agentnet.common.models import AgentCredential

    result = await db.execute(
        select(AgentCredential).where(
            AgentCredential.agent_id == agent.id, AgentCredential.status == "active"
        )
    )
    creds = result.scalars().all()
    all_scopes = set()
    for c in creds:
        for s in c.scopes.split(","):
            all_scopes.add(s.strip())
    return ProfileResponse(
        agent_id=agent.id,
        handle=agent.handle,
        display_name=agent.display_name,
        status=agent.status,
        scopes=list(all_scopes),
    )


@router.post("/heartbeat")
async def agent_heartbeat(
    cred_agent: tuple = Depends(get_credential_dep),
):
    _cred, _agent = cred_agent
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


class AgentSendMessageRequest(BaseModel):
    conversation_id: str
    body: str
    content_type: str = "text"
    client_message_id: str | None = None
    requires_human_review: bool = False


@router.post("/messages")
async def agent_send_message(
    req: AgentSendMessageRequest,
    cred_agent: tuple = Depends(get_credential_dep),
    db: AsyncSession = Depends(get_db),
):
    from agentnet.common.models import (
        Agent,
        AgentCredential,
        Conversation,
        ConversationMember,
        Message,
    )
    from agentnet.events.routes import push_event_to_agent_owner
    from agentnet.audit.service import log_audit

    _cred, agent = cred_agent
    # Verify conversation membership
    result = await db.execute(
        select(ConversationMember).join(Conversation).where(
            ConversationMember.conversation_id == req.conversation_id,
            ConversationMember.user_id == agent.owner_user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(403, detail="INSUFFICIENT_SCOPE")

    if req.client_message_id:
        result = await db.execute(
            select(Message).where(Message.client_message_id == req.client_message_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return {"status": "duplicate", "message_id": existing.id, "actor_type": existing.actor_type}

    msg = Message(
        conversation_id=req.conversation_id,
        sender_user_id=agent.owner_user_id,
        sender_agent_id=agent.id,
        actor_type="agent",
        content_type=req.content_type,
        body="",
        body_encrypted=encrypt_body(req.body, settings.message_encryption_key),
        client_message_id=req.client_message_id,
    )
    db.add(msg)
    await db.flush()

    # Push event to all participants
    result = await db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == req.conversation_id,
            ConversationMember.user_id != agent.owner_user_id,
        )
    )
    for member in result.scalars().all():
        await push_event_to_agent_owner(
            db,
            owner_user_id=member.user_id,
            event_type="message.received",
            payload={
                "message_id": msg.id,
                "conversation_id": req.conversation_id,
                "sender_agent_id": agent.id,
                "sender_handle": agent.handle,
                "body": req.body[:500],
                "actor_type": "agent",
            },
        )

    await log_audit(
        db, owner_user_id=agent.owner_user_id, agent_id=agent.id,
        action="agent.message.send", target_type="message", target_id=msg.id,
        metadata={"conversation_id": req.conversation_id, "preview": req.body[:100]},
    )
    return {"status": "sent", "message_id": msg.id, "actor_type": "agent", "created_at": msg.created_at.isoformat()}


@router.get("/conversations")
async def agent_list_conversations(
    cred_agent: tuple = Depends(get_credential_dep),
    db: AsyncSession = Depends(get_db),
):
    from agentnet.common.models import Agent, Conversation, ConversationMember

    _cred, agent = cred_agent
    result = await db.execute(
        select(ConversationMember.conversation_id).where(
            ConversationMember.user_id == agent.owner_user_id
        )
    )
    conv_ids = [r[0] for r in result.all()]
    if not conv_ids:
        return {"conversations": []}
    convs = await db.execute(
        select(Conversation).where(Conversation.id.in_(conv_ids)).order_by(desc(Conversation.created_at))
    )
    out = []
    for c in convs.scalars().all():
        members = await db.execute(
            select(ConversationMember, Agent)
            .outerjoin(Agent, Agent.owner_user_id == ConversationMember.user_id)
            .where(ConversationMember.conversation_id == c.id)
        )
        others = [
            {"user_id": m.ConversationMember.user_id, "agent_handle": m.Agent.handle if m.Agent else None}
            for m in members.all() if m.ConversationMember.user_id != agent.owner_user_id
        ]
        out.append({"id": c.id, "type": c.type, "participants": others, "created_at": c.created_at.isoformat()})
    return {"conversations": out}


@router.get("/conversations/{conv_id}/messages")
async def agent_get_messages(
    conv_id: str,
    limit: int = Query(50, le=100),
    before: str | None = None,
    cred_agent: tuple = Depends(get_credential_dep),
    db: AsyncSession = Depends(get_db),
):
    from agentnet.common.models import ConversationMember, Message

    _cred, agent = cred_agent
    result = await db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conv_id,
            ConversationMember.user_id == agent.owner_user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(403, detail="INSUFFICIENT_SCOPE")
    query = (
        select(Message)
        .where(Message.conversation_id == conv_id, Message.deleted_at.is_(None))
        .order_by(desc(Message.created_at)).limit(limit)
    )
    if before:
        query = query.where(Message.id < before)
    result = await db.execute(query)
    msgs = result.scalars().all()
    return {
        "messages": [
            {"id": m.id, "sender_user_id": m.sender_user_id, "sender_agent_id": m.sender_agent_id,
             "actor_type": m.actor_type, "body": _agent_decrypt_body(m), "content_type": m.content_type,
             "created_at": m.created_at.isoformat()}
            for m in reversed(msgs)
        ]
    }


def _agent_decrypt_body(m: Message) -> str:
    """Decrypt message body for agent API. Falls back to legacy plaintext."""
    if m.body_encrypted:
        try:
            return decrypt_body(m.body_encrypted, settings.message_encryption_key)
        except Exception:
            return "[decryption error]"
    return m.body


# ── Agent: search users ──────────────────────────────────────


@router.get("/users/search")
async def agent_search_users(
    q: str = Query("", min_length=1, max_length=50),
    limit: int = Query(10, le=50),
    cred_agent: tuple = Depends(get_credential_dep),
    db: AsyncSession = Depends(get_db),
):
    """Agent searches for users by handle or display_name."""
    from agentnet.common.models import User

    _cred, agent = cred_agent
    pattern = f"%{q.strip()}%"
    result = await db.execute(
        select(User)
        .where(
            User.handle.ilike(pattern),
            User.status == "active",
            User.handle.isnot(None),
        )
        .limit(limit)
    )
    users = result.scalars().all()
    return {
        "users": [
            {"user_id": u.id, "handle": u.handle or "", "display_name": u.display_name or u.email}
            for u in users
        ]
    }


# ── Agent: add contact ───────────────────────────────────────


@router.post("/contacts")
async def agent_request_contact(
    addressee_user_id: str,
    cred_agent: tuple = Depends(get_credential_dep),
    db: AsyncSession = Depends(get_db),
):
    """Agent sends a contact request on behalf of its owner."""
    from agentnet.common.models import Contact, User

    _cred, agent = cred_agent

    if addressee_user_id == agent.owner_user_id:
        raise HTTPException(400, detail="Cannot add yourself")

    # Check target exists
    result = await db.execute(select(User).where(User.id == addressee_user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, detail="User not found")

    # Check existing request
    result = await db.execute(
        select(Contact).where(
            or_(
                (Contact.requester_user_id == agent.owner_user_id) & (Contact.addressee_user_id == addressee_user_id),
                (Contact.requester_user_id == addressee_user_id) & (Contact.addressee_user_id == agent.owner_user_id),
            ),
            Contact.status.in_(["pending", "accepted"]),
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(409, detail="Contact request already exists or you are already connected")

    contact = Contact(
        requester_user_id=agent.owner_user_id,
        addressee_user_id=addressee_user_id,
    )
    db.add(contact)
    await db.flush()

    # Notify the other user's agents
    from agentnet.events.routes import push_event_to_agent_owner

    await push_event_to_agent_owner(
        db,
        owner_user_id=addressee_user_id,
        event_type="contact.requested",
        payload={
            "contact_id": contact.id,
            "requester_user_id": agent.owner_user_id,
            "requester_agent_handle": agent.handle,
        },
    )

    return {"status": "pending", "contact_id": contact.id}


# ── Agent: accept contact ────────────────────────────────────


@router.post("/contacts/{contact_id}/accept")
async def agent_accept_contact(
    contact_id: str,
    cred_agent: tuple = Depends(get_credential_dep),
    db: AsyncSession = Depends(get_db),
):
    """Agent accepts a contact request on behalf of its owner."""
    from agentnet.common.models import Contact

    _cred, agent = cred_agent
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    c = result.scalar_one_or_none()
    if not c or c.addressee_user_id != agent.owner_user_id or c.status != "pending":
        raise HTTPException(404, detail="Contact request not found")

    c.status = "accepted"
    c.responded_at = datetime.now(timezone.utc)
    await db.flush()

    # Notify requester's agents
    from agentnet.events.routes import push_event_to_agent_owner

    await push_event_to_agent_owner(
        db,
        owner_user_id=c.requester_user_id,
        event_type="contact.accepted",
        payload={
            "contact_id": c.id,
            "accepted_by_user_id": agent.owner_user_id,
        },
    )

    return {"status": "accepted"}


# ── Agent: create conversation ───────────────────────────────


@router.post("/conversations")
async def agent_create_conversation(
    participant_user_id: str,
    cred_agent: tuple = Depends(get_credential_dep),
    db: AsyncSession = Depends(get_db),
):
    """Agent creates a conversation with another connected user."""
    from agentnet.common.models import Contact, Conversation, ConversationMember

    _cred, agent = cred_agent

    # Check contact exists
    result = await db.execute(
        select(Contact).where(
            or_(
                (Contact.requester_user_id == agent.owner_user_id) & (Contact.addressee_user_id == participant_user_id),
                (Contact.requester_user_id == participant_user_id) & (Contact.addressee_user_id == agent.owner_user_id),
            ),
            Contact.status == "accepted",
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(403, detail="Not connected")

    # Check existing direct conversation
    result = await db.execute(
        select(ConversationMember).where(
            ConversationMember.user_id.in_([agent.owner_user_id, participant_user_id])
        )
    )
    member_ids = set(r.conversation_id for r in result.scalars().all())
    result = await db.execute(
        select(ConversationMember.conversation_id)
        .where(ConversationMember.user_id == agent.owner_user_id)
        .where(ConversationMember.conversation_id.in_(member_ids))
    )
    owner_conv_ids = set(r[0] for r in result.all())
    result = await db.execute(
        select(ConversationMember.conversation_id)
        .where(ConversationMember.user_id == participant_user_id)
        .where(ConversationMember.conversation_id.in_(owner_conv_ids))
    )
    existing = result.first()
    if existing:
        return {"conversation_id": existing[0], "existing": True}

    conv = Conversation(created_by=agent.owner_user_id)
    db.add(conv)
    await db.flush()
    db.add(ConversationMember(conversation_id=conv.id, user_id=agent.owner_user_id))
    db.add(ConversationMember(conversation_id=conv.id, user_id=participant_user_id))
    await db.flush()

    return {"conversation_id": conv.id, "existing": False}
