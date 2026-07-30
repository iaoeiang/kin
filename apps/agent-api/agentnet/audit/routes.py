"""Audit log API endpoint."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentnet.auth.routes import get_current_user_dep
from agentnet.common.database import get_db
from agentnet.common.models import AuditLog, User

router = APIRouter(prefix="/api/audit", tags=["audit"])


class AuditEntryResponse(BaseModel):
    id: str
    agent_id: str | None
    action: str
    target_type: str
    target_id: str
    result: str
    audit_metadata: dict
    created_at: str


@router.get("", response_model=list[AuditEntryResponse])
async def list_audit(
    agent_id: str | None = Query(None),
    action: str | None = Query(None),
    limit: int = Query(50, le=200),
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AuditLog)
        .where(AuditLog.owner_user_id == user.id)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )
    if agent_id:
        query = query.where(AuditLog.agent_id == agent_id)
    if action:
        query = query.where(AuditLog.action == action)
    result = await db.execute(query)
    entries = result.scalars().all()
    return [
        AuditEntryResponse(
            id=e.id,
            agent_id=e.agent_id,
            action=e.action,
            target_type=e.target_type,
            target_id=e.target_id,
            result=e.result,
            audit_metadata=json.loads(e.audit_metadata or "{}"),
            created_at=e.created_at.isoformat(),
        )
        for e in entries
    ]
