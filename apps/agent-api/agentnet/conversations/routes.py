"""Conversations + Messages API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentnet.auth.routes import get_current_user_dep
from agentnet.common.database import get_db
from agentnet.common.crypto import encrypt_body, decrypt_body
from agentnet.common.config import settings
from agentnet.common.models import (
    Contact,
    Conversation,
    ConversationMember,
    Message,
    User,
)
from agentnet.events.routes import push_event_to_agent_owner
from agentnet.audit.service import log_audit
import structlog

logger = structlog.get_logger("messages")


router = APIRouter(prefix="/api", tags=["conversations"])


class SendMessageRequest(BaseModel):
    conversation_id: str
    body: str
    content_type: str = "text"
    client_message_id: str | None = None


class CreateConversationRequest(BaseModel):
    participant_user_id: str


@router.post("/conversations")
async def create_conversation(
    req: CreateConversationRequest,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    # Check contact exists
    result = await db.execute(
        select(Contact).where(
            or_(
                (Contact.requester_user_id == user.id) & (Contact.addressee_user_id == req.participant_user_id),
                (Contact.requester_user_id == req.participant_user_id) & (Contact.addressee_user_id == user.id),
            ),
            Contact.status == "accepted",
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(403, detail="Not connected")

    # Check existing direct conversation
    result = await db.execute(
        select(ConversationMember).where(
            ConversationMember.user_id.in_([user.id, req.participant_user_id])
        )
    )
    member_ids = set(r.conversation_id for r in result.scalars().all())
    # Find conv where both are members
    result = await db.execute(
        select(ConversationMember.conversation_id)
        .where(ConversationMember.user_id == user.id)
        .where(ConversationMember.conversation_id.in_(member_ids))
    )
    user_conv_ids = set(r[0] for r in result.all())
    result = await db.execute(
        select(ConversationMember.conversation_id)
        .where(ConversationMember.user_id == req.participant_user_id)
        .where(ConversationMember.conversation_id.in_(user_conv_ids))
    )
    existing = result.first()
    if existing:
        return {"conversation_id": existing[0], "existing": True}

    conv = Conversation(created_by=user.id)
    db.add(conv)
    await db.flush()
    db.add(ConversationMember(conversation_id=conv.id, user_id=user.id))
    db.add(ConversationMember(conversation_id=conv.id, user_id=req.participant_user_id))
    await db.flush()
    return {"conversation_id": conv.id, "existing": False}


@router.get("/conversations")
async def list_conversations(
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ConversationMember.conversation_id).where(ConversationMember.user_id == user.id)
    )
    conv_ids = [r[0] for r in result.all()]
    if not conv_ids:
        return {"conversations": []}
    convs = await db.execute(select(Conversation).where(Conversation.id.in_(conv_ids)))
    out = []
    for c in convs.scalars().all():
        # get other participant name
        members = await db.execute(
            select(ConversationMember, User)
            .join(User, ConversationMember.user_id == User.id)
            .where(ConversationMember.conversation_id == c.id)
        )
        others = [
            {"user_id": m.User.id, "name": m.User.display_name or m.User.email}
            for m in members.all()
            if m.User.id != user.id
        ]
        out.append({
            "id": c.id,
            "type": c.type,
            "title": c.title or (others[0]["name"] if others else "Chat"),
            "others": others,
            "created_at": c.created_at.isoformat(),
        })
    return {"conversations": out}


@router.post("/messages")
async def send_message(
    req: SendMessageRequest,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    # Verify membership
    result = await db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == req.conversation_id,
            ConversationMember.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(403, detail="Not a member")

    if req.client_message_id:
        result = await db.execute(
            select(Message).where(Message.client_message_id == req.client_message_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return {"status": "duplicate", "message_id": existing.id}

    msg = Message(
        conversation_id=req.conversation_id,
        sender_user_id=user.id,
        actor_type="human",
        content_type=req.content_type,
        body="",
        body_encrypted=encrypt_body(req.body, settings.message_encryption_key),
        client_message_id=req.client_message_id,
    )
    db.add(msg)
    await db.flush()

    # Push event to participants
    result = await db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == req.conversation_id,
            ConversationMember.user_id != user.id,
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
                "sender_user_id": user.id,
                "body": req.body[:500],
                "actor_type": "human",
            },
        )

    # Real-time WS broadcast
    from agentnet.websocket.handler import broadcast_to_conversation
    try:
        other_user = await db.execute(
            select(User).where(User.id == (
                select(ConversationMember.user_id)
                .where(
                    ConversationMember.conversation_id == req.conversation_id,
                    ConversationMember.user_id != user.id,
                )
            ).scalar_subquery())
        )
        other_name = other_user.scalar_one_or_none()
        sender_name = user.display_name or user.email

        await broadcast_to_conversation(req.conversation_id, {
            "type": "new_message",
            "message_id": msg.id,
            "conversation_id": req.conversation_id,
            "sender_user_id": user.id,
            "sender_name": sender_name,
            "body": req.body[:200],
            "content_type": req.content_type,
            "created_at": msg.created_at.isoformat(),
            "conv_title": other_name.display_name if other_name else "Chat",
        })
    except Exception as e:
        logger.warning("ws_broadcast_failed", error=str(e))

    # Audit
    await log_audit(
        db,
        owner_user_id=user.id,
        action="human.message.send",
        target_type="message",
        target_id=msg.id,
        metadata={"conversation_id": req.conversation_id, "preview": req.body[:100]},
    )

    return {"status": "sent", "message_id": msg.id, "created_at": msg.created_at.isoformat()}


@router.get("/conversations/{conv_id}/messages")
async def get_messages(
    conv_id: str,
    limit: int = Query(50, le=100),
    before: str | None = None,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    # Verify membership
    result = await db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conv_id,
            ConversationMember.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(403, detail="Not a member")

    query = select(Message).where(
        Message.conversation_id == conv_id,
        Message.deleted_at.is_(None),
    ).order_by(desc(Message.created_at)).limit(limit)

    if before:
        query = query.where(Message.id < before)

    result = await db.execute(query)
    msgs = result.scalars().all()
    return {
        "messages": [
            {
                "id": m.id,
                "sender_user_id": m.sender_user_id,
                "sender_agent_id": m.sender_agent_id,
                "actor_type": m.actor_type,
                "body": _decrypt_message_body(m),
                "content_type": m.content_type,
                "created_at": m.created_at.isoformat(),
            }
            for m in reversed(msgs)  # oldest first
        ]
    }


def _decrypt_message_body(m: Message) -> str:
    """Decrypt message body. Falls back to legacy plaintext body for old messages."""
    if m.body_encrypted:
        try:
            return decrypt_body(m.body_encrypted, settings.message_encryption_key)
        except Exception:
            return "[decryption error]"
    return m.body
