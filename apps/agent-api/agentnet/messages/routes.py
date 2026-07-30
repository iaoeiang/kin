"""Message edit, delete, and recall endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentnet.auth.routes import get_current_user_dep
from agentnet.common.database import get_db
from agentnet.common.crypto import encrypt_body
from agentnet.common.config import settings
from agentnet.common.models import ConversationMember, Message, User

router = APIRouter(prefix="/api/messages", tags=["messages"])


class EditMessageRequest(BaseModel):
    body: str
    content_type: str = "text"


@router.patch("/{message_id}")
async def edit_message(
    message_id: str,
    req: EditMessageRequest,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message).where(Message.id == message_id, Message.sender_user_id == user.id, Message.deleted_at.is_(None))
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, detail="Message not found or not yours")
    msg.body = ""
    msg.body_encrypted = encrypt_body(req.body, settings.message_encryption_key)
    msg.content_type = req.content_type
    await db.flush()
    return {"status": "edited", "message_id": msg.id, "updated_at": datetime.now(timezone.utc).isoformat()}


@router.delete("/{message_id}")
async def delete_message(
    message_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message).where(Message.id == message_id, Message.sender_user_id == user.id, Message.deleted_at.is_(None))
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, detail="Message not found or not yours")
    msg.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return {"status": "deleted", "message_id": msg.id}


@router.post("/{message_id}/recall")
async def recall_message(
    message_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Recall: only within 5 minutes of sending."""
    result = await db.execute(
        select(Message).where(Message.id == message_id, Message.sender_user_id == user.id, Message.deleted_at.is_(None))
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, detail="Message not found or not yours")
    age = (datetime.now(timezone.utc) - msg.created_at).total_seconds()
    if age > 300:
        raise HTTPException(400, detail="Recall window expired (5 minutes)")
    msg.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return {"status": "recalled", "message_id": msg.id, "recall_window_seconds": 300}
