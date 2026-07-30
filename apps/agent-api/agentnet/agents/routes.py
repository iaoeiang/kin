"""Agents CRUD."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentnet.auth.routes import get_current_user_dep
from agentnet.common.database import get_db
from agentnet.common.models import Agent, User

router = APIRouter(prefix="/agents", tags=["agents"])


class CreateAgentRequest(BaseModel):
    handle: str
    display_name: str


class AgentResponse(BaseModel):
    id: str
    handle: str
    display_name: str
    status: str
    created_at: str


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    req: CreateAgentRequest,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    if not req.handle or len(req.handle) < 2:
        raise HTTPException(status_code=400, detail="Handle must be at least 2 characters")
    # Check unique handle
    result = await db.execute(select(Agent).where(Agent.handle == req.handle))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Handle already taken")
    agent = Agent(
        owner_user_id=user.id,
        handle=req.handle,
        display_name=req.display_name or req.handle,
    )
    db.add(agent)
    await db.flush()
    return AgentResponse(
        id=agent.id,
        handle=agent.handle,
        display_name=agent.display_name,
        status=agent.status,
        created_at=agent.created_at.isoformat(),
    )


@router.get("", response_model=AgentListResponse)
async def list_agents(
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.owner_user_id == user.id))
    agents = result.scalars().all()
    return AgentListResponse(
        agents=[
            AgentResponse(
                id=a.id,
                handle=a.handle,
                display_name=a.display_name,
                status=a.status,
                created_at=a.created_at.isoformat(),
            )
            for a in agents
        ]
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent or agent.owner_user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse(
        id=agent.id,
        handle=agent.handle,
        display_name=agent.display_name,
        status=agent.status,
        created_at=agent.created_at.isoformat(),
    )


@router.patch("/{agent_id}/status")
async def update_agent_status(
    agent_id: str,
    new_status: str = "paused",
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent or agent.owner_user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent not found")
    if new_status not in ("active", "paused", "suspended"):
        raise HTTPException(status_code=400, detail="Invalid status")
    agent.status = new_status
    await db.flush()
    return {"status": new_status}
