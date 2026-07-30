"""Agent event queue: pull + ack delivery."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agentnet.common.agent_session import get_credential_dep
from agentnet.common.database import get_db
from agentnet.common.models import Agent, AgentCredential, AgentEvent

router = APIRouter(prefix="/v1/agent", tags=["agent-api"])


class EventResponse(BaseModel):
    id: str
    event_type: str
    payload: dict
    status: str
    available_at: str
    created_at: str


class EventsResponse(BaseModel):
    events: list[EventResponse]
    has_more: bool


async def push_event(
    db: AsyncSession,
    agent_id: str,
    event_type: str,
    payload: dict,
    max_attempts: int = 5,
) -> AgentEvent:
    """Create an event for the agent's event queue."""
    ev = AgentEvent(
        agent_id=agent_id,
        event_type=event_type,
        payload=json.dumps(payload),
        max_attempts=max_attempts,
    )
    db.add(ev)
    await db.flush()
    return ev


async def push_event_to_agent_owner(
    db: AsyncSession,
    owner_user_id: str,
    event_type: str,
    payload: dict,
):
    """Push event to all active agents owned by a user."""
    result = await db.execute(
        select(Agent).where(
            Agent.owner_user_id == owner_user_id,
            Agent.status == "active",
        )
    )
    agents = result.scalars().all()
    for agent in agents:
        await push_event(db, agent.id, event_type, payload)


@router.get("/events", response_model=EventsResponse)
async def get_events(
    limit: int = Query(20, le=100),
    cursor: str | None = None,
    wait_seconds: int = Query(0, le=30),
    cred_agent: tuple = Depends(get_credential_dep),
    db: AsyncSession = Depends(get_db),
):
    _cred, agent = cred_agent
    query = (
        select(AgentEvent)
        .where(
            AgentEvent.agent_id == agent.id,
            AgentEvent.status == "pending",
            AgentEvent.available_at <= datetime.now(timezone.utc),
            AgentEvent.attempts < AgentEvent.max_attempts,
        )
        .order_by(AgentEvent.created_at.asc())
        .limit(limit + 1)
    )
    if cursor:
        query = query.where(AgentEvent.id > cursor)

    result = await db.execute(query)
    events = result.scalars().all()
    has_more = len(events) > limit
    if has_more:
        events = events[:limit]

    # Mark as delivered
    for ev in events:
        ev.status = "delivered"
        ev.attempts = AgentEvent.attempts + 1
    await db.flush()

    return EventsResponse(
        events=[
            EventResponse(
                id=ev.id,
                event_type=ev.event_type,
                payload=json.loads(ev.payload),
                status=ev.status,
                available_at=ev.available_at.isoformat(),
                created_at=ev.created_at.isoformat(),
            )
            for ev in events
        ],
        has_more=has_more,
    )


@router.post("/events/{event_id}/ack")
async def ack_event(
    event_id: str,
    cred_agent: tuple = Depends(get_credential_dep),
    db: AsyncSession = Depends(get_db),
):
    _cred, agent = cred_agent
    result = await db.execute(
        select(AgentEvent).where(
            AgentEvent.id == event_id,
            AgentEvent.agent_id == agent.id,
        )
    )
    ev = result.scalar_one_or_none()
    if not ev:
        raise HTTPException(404, detail="Event not found")
    ev.status = "acked"
    ev.acked_at = datetime.now(timezone.utc)
    await db.flush()
    return {"status": "acked"}


@router.post("/events/{event_id}/nack")
async def nack_event(
    event_id: str,
    cred_agent: tuple = Depends(get_credential_dep),
    db: AsyncSession = Depends(get_db),
):
    """Negative ack: return event to queue for retry."""
    _cred, agent = cred_agent
    result = await db.execute(
        select(AgentEvent).where(
            AgentEvent.id == event_id,
            AgentEvent.agent_id == agent.id,
        )
    )
    ev = result.scalar_one_or_none()
    if not ev:
        raise HTTPException(404, detail="Event not found")
    ev.status = "pending"
    ev.available_at = datetime.now(timezone.utc)
    await db.flush()
    return {"status": "returned"}
