"""Contacts API — request/accept/reject/delete state machine."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentnet.auth.routes import get_current_user_dep
from agentnet.common.database import get_db
from agentnet.common.models import Contact, User

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


class ContactResponse(BaseModel):
    id: str
    user_id: str
    handle: str
    display_name: str
    status: str
    requested_at: str
    responded_at: str | None = None


class ContactRequest(BaseModel):
    addressee_user_id: str


@router.post("/request")
async def request_contact(
    req: ContactRequest,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    if req.addressee_user_id == user.id:
        raise HTTPException(400, detail="Cannot add yourself")
    # Check target exists
    result = await db.execute(select(User).where(User.id == req.addressee_user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, detail="User not found")
    # Check existing
    result = await db.execute(
        select(Contact).where(
            or_(
                (Contact.requester_user_id == user.id) & (Contact.addressee_user_id == req.addressee_user_id),
                (Contact.requester_user_id == req.addressee_user_id) & (Contact.addressee_user_id == user.id),
            ),
            Contact.status.in_(["pending", "accepted"]),
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(409, detail="Contact request already exists")
    contact = Contact(requester_user_id=user.id, addressee_user_id=req.addressee_user_id)
    db.add(contact)
    await db.flush()
    return {"status": "pending", "contact_id": contact.id}


@router.post("/{contact_id}/accept")
async def accept_contact(
    contact_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    c = result.scalar_one_or_none()
    if not c or c.addressee_user_id != user.id or c.status != "pending":
        raise HTTPException(404, detail="Contact request not found")
    c.status = "accepted"
    c.responded_at = datetime.now(timezone.utc)
    await db.flush()
    return {"status": "accepted"}


@router.post("/{contact_id}/reject")
async def reject_contact(
    contact_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    c = result.scalar_one_or_none()
    if not c or c.addressee_user_id != user.id or c.status != "pending":
        raise HTTPException(404, detail="Contact request not found")
    c.status = "rejected"
    c.responded_at = datetime.now(timezone.utc)
    await db.flush()
    return {"status": "rejected"}


@router.get("", response_model=list[dict])
async def list_contacts(
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Return accepted contacts for current user."""
    result = await db.execute(
        select(Contact).where(
            or_(
                (Contact.requester_user_id == user.id) | (Contact.addressee_user_id == user.id),
            ),
            Contact.status == "accepted",
        )
    )
    contacts = result.scalars().all()
    out = []
    for c in contacts:
        other_id = c.addressee_user_id if c.requester_user_id == user.id else c.requester_user_id
        r = await db.execute(select(User).where(User.id == other_id))
        u = r.scalar_one()
        out.append({
            "contact_id": c.id,
            "user_id": u.id,
            "handle": getattr(u, "handle", u.email.split("@")[0]),
            "display_name": u.display_name or u.email,
            "status": c.status,
            "since": c.updated_at.isoformat() if c.updated_at else "",
        })
    return out
