"""Admin / system status endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentnet.auth.routes import get_current_user_dep
from agentnet.common.database import get_db
from agentnet.common.models import (
    Agent,
    AgentCredential,
    AuditLog,
    Contact,
    Conversation,
    Message,
    User,
)
from agentnet.common.cache import stats_cache

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/status")
async def system_status(
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """System overview — counts of all entity types."""
    # Check cache first
    cached = await stats_cache.get("status")
    if cached:
        return cached

    counts = {}
    for table, model in [
        ("users", User),
        ("agents", Agent),
        ("credentials", AgentCredential),
        ("contacts", Contact),
        ("conversations", Conversation),
        ("messages", Message),
        ("audit_logs", AuditLog),
    ]:
        result = await db.execute(select(func.count(model.id)))
        counts[table] = result.scalar()

    # Active agents
    result = await db.execute(select(func.count(Agent.id)).where(Agent.status == "active"))
    counts["agents_active"] = result.scalar()

    # Messages today
    from datetime import datetime, timezone, timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await db.execute(select(func.count(Message.id)).where(Message.created_at >= since))
    counts["messages_24h"] = result.scalar()

    resp = {
        "status": "ok",
        "app": "AgentNet",
        "version": "0.1.0",
        "counts": counts,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }

    stats_cache.set("status", resp)
    return resp


@router.get("/audit-summary")
async def audit_summary(
    limit: int = 20,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Recent audit entries across all users (for admin panel)."""
    from sqlalchemy import desc

    result = await db.execute(
        select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
    )
    entries = result.scalars().all()
    return {
        "entries": [
            {
                "id": e.id,
                "owner_user_id": e.owner_user_id,
                "agent_id": e.agent_id,
                "action": e.action,
                "target_type": e.target_type,
                "target_id": e.target_id,
                "result": e.result,
                "created_at": e.created_at.isoformat(),
            }
            for e in entries
        ]
    }
