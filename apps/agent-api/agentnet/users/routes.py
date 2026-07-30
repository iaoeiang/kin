"""User search and profile endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentnet.auth.routes import get_current_user_dep
from agentnet.common.database import get_db
from agentnet.common.models import User

router = APIRouter(prefix="/api/users", tags=["users"])


class UserProfile(BaseModel):
    user_id: str
    handle: str
    display_name: str


class UpdateProfileRequest(BaseModel):
    handle: str = ""
    display_name: str = ""


@router.get("/search")
async def search_users(
    q: str = Query("", min_length=1, max_length=50),
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Search users by handle or display_name (public info only)."""
    if not q.strip():
        return {"users": []}

    pattern = f"%{q.strip()}%"
    result = await db.execute(
        select(User)
        .where(
            or_(
                User.handle.ilike(pattern),
                User.display_name.ilike(pattern),
            ),
            User.status == "active",
            User.handle.isnot(None),
        )
        .limit(limit)
    )
    users = result.scalars().all()
    return {
        "users": [
            UserProfile(
                user_id=u.id,
                handle=u.handle or "",
                display_name=u.display_name or u.email,
            )
            for u in users
        ]
    }


@router.get("/me", response_model=UserProfile)
async def get_my_profile(
    user: User = Depends(get_current_user_dep),
):
    """Get own public profile."""
    return UserProfile(
        user_id=user.id,
        handle=user.handle or "",
        display_name=user.display_name or user.email,
    )


@router.patch("/me")
async def update_profile(
    req: UpdateProfileRequest,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
):
    """Update handle and/or display_name."""
    if req.handle:
        handle = req.handle.strip().lower()
        if not all(c.isalnum() or c in "_-" for c in handle):
            raise HTTPException(400, detail="Handle can only contain letters, numbers, underscores and hyphens.")
        if handle != user.handle:
            result = await db.execute(select(User).where(User.handle == handle))
            if result.scalar_one_or_none():
                raise HTTPException(409, detail="Handle already taken.")
        user.handle = handle

    if req.display_name:
        user.display_name = req.display_name.strip()

    await db.flush()
    return {"status": "updated", "handle": user.handle or "", "display_name": user.display_name}
