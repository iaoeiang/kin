"""Sprint 4: Security & Access Control — automation level, emergency stop, rate limits."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from agentnet.auth.routes import get_current_user_dep
from agentnet.common.database import get_db
from agentnet.common.models import Agent, AgentConversationACL, User

router = APIRouter(prefix="/api/security", tags=["security"])


# ── Agent Automation Level ──

class AutomationUpdate(BaseModel):
    automation_level: str


VALID_LEVELS = {"auto", "human_review", "disabled"}


@router.get("/agents/{agent_id}/automation")
async def get_automation(
    agent_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.owner_user_id == user.id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, detail="Agent not found")
    return {"agent_id": agent.id, "automation_level": agent.automation_level, "status": agent.status}


@router.patch("/agents/{agent_id}/automation")
async def set_automation(
    agent_id: str,
    req: AutomationUpdate,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    if req.automation_level not in VALID_LEVELS:
        raise HTTPException(400, detail=f"Must be one of: {', '.join(VALID_LEVELS)}")
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.owner_user_id == user.id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, detail="Agent not found")
    agent.automation_level = req.automation_level
    await db.flush()
    return {"agent_id": agent.id, "automation_level": agent.automation_level}


# ── Emergency Stop ──

@router.post("/agents/{agent_id}/emergency-stop")
async def emergency_stop(
    agent_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Immediately suspend all credentials and set agent to disabled."""
    from agentnet.common.models import Agent, AgentCredential

    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.owner_user_id == user.id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, detail="Agent not found")
    agent.status = "suspended"
    agent.automation_level = "disabled"
    # Revoke all active credentials
    result = await db.execute(
        select(AgentCredential).where(AgentCredential.agent_id == agent_id, AgentCredential.status == "active")
    )
    for cred in result.scalars().all():
        from datetime import datetime, timezone
        cred.status = "revoked"
        cred.revoked_at = datetime.now(timezone.utc)
    await db.flush()
    return {"status": "emergency_stopped", "agent_id": agent.id}


@router.post("/agents/{agent_id}/emergency-release")
async def emergency_release(
    agent_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Release emergency stop — requires manual re-enable."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.owner_user_id == user.id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, detail="Agent not found")
    if agent.status != "suspended":
        raise HTTPException(400, detail="Agent is not emergency stopped")
    agent.status = "paused"  # user must manually set to active + issue new credentials
    await db.flush()
    return {"status": "released_to_paused", "agent_id": agent.id, "next": "Issue new credentials and set status=active"}


# ── Agent Conversation ACL ──

class ACLCreate(BaseModel):
    agent_id: str
    permission: str = "allow"


class ACLResponse(BaseModel):
    id: str
    conversation_id: str
    agent_id: str
    agent_handle: str
    permission: str
    created_at: str


@router.post("/conversations/{conv_id}/acl")
async def create_acl(
    conv_id: str,
    req: ACLCreate,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Grant or deny an agent access to a conversation."""
    from agentnet.common.models import ConversationMember, Agent

    # Verify user is a member
    result = await db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conv_id, ConversationMember.user_id == user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(403, detail="Not a member of this conversation")
    if req.permission not in ("allow", "deny"):
        raise HTTPException(400, detail="Permission must be 'allow' or 'deny'")
    # Check agent exists
    result = await db.execute(select(Agent).where(Agent.id == req.agent_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, detail="Agent not found")
    # Upsert
    result = await db.execute(
        select(AgentConversationACL).where(
            AgentConversationACL.conversation_id == conv_id,
            AgentConversationACL.agent_id == req.agent_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.permission = req.permission
    else:
        acl = AgentConversationACL(conversation_id=conv_id, agent_id=req.agent_id, permission=req.permission, granted_by=user.id)
        db.add(acl)
    await db.flush()
    return {"status": "set", "conversation_id": conv_id, "agent_id": req.agent_id, "permission": req.permission}


@router.get("/conversations/{conv_id}/acl", response_model=list[ACLResponse])
async def list_acl(
    conv_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    from agentnet.common.models import ConversationMember, Agent

    result = await db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conv_id, ConversationMember.user_id == user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(403, detail="Not a member")
    result = await db.execute(
        select(AgentConversationACL, Agent)
        .join(Agent, AgentConversationACL.agent_id == Agent.id)
        .where(AgentConversationACL.conversation_id == conv_id)
    )
    return [
        ACLResponse(id=row.AgentConversationACL.id, conversation_id=conv_id, agent_id=row.Agent.id,
                     agent_handle=row.Agent.handle, permission=row.AgentConversationACL.permission,
                     created_at=row.AgentConversationACL.created_at.isoformat())
        for row in result.all()
    ]


@router.delete("/conversations/{conv_id}/acl/{acl_id}")
async def delete_acl(
    conv_id: str, acl_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    from agentnet.common.models import ConversationMember

    result = await db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conv_id, ConversationMember.user_id == user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(403, detail="Not a member")
    result = await db.execute(
        select(AgentConversationACL).where(AgentConversationACL.id == acl_id, AgentConversationACL.conversation_id == conv_id)
    )
    acl = result.scalar_one_or_none()
    if not acl:
        raise HTTPException(404, detail="ACL entry not found")
    await db.delete(acl)
    await db.flush()
    return {"status": "deleted"}


# ── Rate Limit Status ──

@router.get("/rate-limits")
async def get_rate_limits(
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Return current rate limit state for the user's credentials."""
    from agentnet.common.models import Agent, AgentCredential
    from datetime import datetime, timezone

    result = await db.execute(
        select(AgentCredential, Agent)
        .join(Agent, AgentCredential.agent_id == Agent.id)
        .where(Agent.owner_user_id == user.id)
        .order_by(AgentCredential.created_at.desc())
    )
    creds = []
    for cred, agent in result.all():
        creds.append({
            "credential_id": cred.id,
            "agent_id": cred.agent_id,
            "agent_handle": agent.handle,
            "prefix": cred.prefix,
            "status": cred.status,
            "scopes": cred.scopes,
            "last_used_at": cred.last_used_at.isoformat() if cred.last_used_at else None,
        })
    return {"credentials": creds, "default_rate_limit": "60/minute per credential", "user_id": user.id}
