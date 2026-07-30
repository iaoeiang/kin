"""Agent credentials lifecycle: create, show once, list, revoke, rotate."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.hash import argon2
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agentnet.auth.routes import get_current_user_dep
from agentnet.common.database import get_db
from agentnet.common.models import Agent, AgentCredential, User

router = APIRouter(prefix="/credentials", tags=["credentials"])


class CreateCredentialRequest(BaseModel):
    agent_id: str
    name: str = ""
    scopes: str = "profile:read,messages:read,messages:send"
    expires_in_days: int | None = None


class CredentialShowResponse(BaseModel):
    id: str
    name: str
    secret: str  # showed once
    prefix: str
    scopes: str
    expires_at: str | None
    created_at: str


class CredentialResponse(BaseModel):
    id: str
    agent_id: str
    name: str
    prefix: str
    scopes: str
    status: str
    last_used_at: str | None
    expires_at: str | None
    created_at: str


DEFAULT_SCOPES = ["profile:read", "messages:read", "messages:send", "conversations:read", "presence:write"]


def generate_secret() -> tuple[str, str, str]:
    """Generate (full_secret, prefix, hash)."""
    secret = "agn_" + secrets.token_urlsafe(32)
    prefix = secret[:12]
    h = argon2.hash(secret)
    return secret, prefix, h


@router.post("", response_model=CredentialShowResponse, status_code=201)
async def create_credential(
    req: CreateCredentialRequest,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    # Verify agent ownership
    result = await db.execute(select(Agent).where(Agent.id == req.agent_id))
    agent = result.scalar_one_or_none()
    if not agent or agent.owner_user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent not found")

    secret, prefix, secret_hash = generate_secret()
    cred = AgentCredential(
        agent_id=req.agent_id,
        name=req.name or f"cred-{secrets.token_hex(3)}",
        secret_hash=secret_hash,
        prefix=prefix,
        scopes=req.scopes or ",".join(DEFAULT_SCOPES),
    )
    if req.expires_in_days:
        from datetime import datetime, timedelta, timezone
        cred.expires_at = datetime.now(timezone.utc) + timedelta(days=req.expires_in_days)
    db.add(cred)
    await db.flush()

    return CredentialShowResponse(
        id=cred.id,
        name=cred.name,
        secret=secret,  # SHOW ONCE
        prefix=prefix,
        scopes=cred.scopes,
        expires_at=cred.expires_at.isoformat() if cred.expires_at else None,
        created_at=cred.created_at.isoformat(),
    )


@router.get("", response_model=list[CredentialResponse])
async def list_credentials(
    agent_id: str | None = None,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    query = select(AgentCredential).join(Agent).where(Agent.owner_user_id == user.id)
    if agent_id:
        query = query.where(AgentCredential.agent_id == agent_id)
    result = await db.execute(query.order_by(AgentCredential.created_at.desc()))
    creds = result.scalars().all()
    return [
        CredentialResponse(
            id=c.id,
            agent_id=c.agent_id,
            name=c.name,
            prefix=c.prefix,
            scopes=c.scopes,
            status=c.status,
            last_used_at=c.last_used_at.isoformat() if c.last_used_at else None,
            expires_at=c.expires_at.isoformat() if c.expires_at else None,
            created_at=c.created_at.isoformat(),
        )
        for c in creds
    ]


@router.post("/{credential_id}/revoke")
async def revoke_credential(
    credential_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AgentCredential).join(Agent).where(
            AgentCredential.id == credential_id,
            Agent.owner_user_id == user.id,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    from datetime import datetime, timezone
    cred.revoked_at = datetime.now(timezone.utc)
    cred.status = "revoked"
    await db.flush()
    return {"status": "revoked"}


@router.post("/{credential_id}/rotate", response_model=CredentialShowResponse)
async def rotate_credential(
    credential_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    # First revoke old
    result = await db.execute(
        select(AgentCredential).join(Agent).where(
            AgentCredential.id == credential_id,
            Agent.owner_user_id == user.id,
        )
    )
    old = result.scalar_one_or_none()
    if not old:
        raise HTTPException(status_code=404, detail="Credential not found")
    from datetime import datetime, timezone
    old.revoked_at = datetime.now(timezone.utc)
    old.status = "revoked"

    # Create new
    agent_id = old.agent_id
    secret, prefix, secret_hash = generate_secret()
    cred = AgentCredential(
        agent_id=agent_id,
        name=old.name + "-rotated",
        secret_hash=secret_hash,
        prefix=prefix,
        scopes=old.scopes,
        expires_at=old.expires_at,
    )
    db.add(cred)
    await db.flush()
    return CredentialShowResponse(
        id=cred.id,
        name=cred.name,
        secret=secret,
        prefix=prefix,
        scopes=cred.scopes,
        expires_at=cred.expires_at.isoformat() if cred.expires_at else None,
        created_at=cred.created_at.isoformat(),
    )
