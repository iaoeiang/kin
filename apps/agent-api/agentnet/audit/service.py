"""Audit log service."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentnet.common.models import AuditLog


async def log_audit(
    db: AsyncSession,
    owner_user_id: str,
    action: str,
    agent_id: str | None = None,
    target_type: str = "",
    target_id: str = "",
    result: str = "success",
    metadata: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        owner_user_id=owner_user_id,
        agent_id=agent_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        result=result,
        audit_metadata=json.dumps(metadata or {}),
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_audit_logs(
    db: AsyncSession,
    owner_user_id: str,
    agent_id: str | None = None,
    action: str | None = None,
    limit: int = 50,
) -> list[AuditLog]:
    from sqlalchemy import desc, select as _select

    query = (
        _select(AuditLog)
        .where(AuditLog.owner_user_id == owner_user_id)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )
    if agent_id:
        query = query.where(AuditLog.agent_id == agent_id)
    if action:
        query = query.where(AuditLog.action == action)
    result = await db.execute(query)
    return list(result.scalars().all())
