"""Auth service: register (3-step email verification), login, JWT session."""
from __future__ import annotations

import asyncio
import json
import random
import string
from datetime import datetime, timedelta, timezone

from fastapi import Request, APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from passlib.hash import argon2
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentnet.common.config import settings
from agentnet.common.database import get_db
from agentnet.common.models import User
from agentnet.common.redis_client import get_redis

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Redis key helpers ────────────────────────────────────────

CODE_KEY = "verify:code:{email}"
TOKEN_KEY = "verify:token:{token}"


def _code_key(email: str) -> str:
    return CODE_KEY.format(email=email.lower())


def _token_key(token: str) -> str:
    return TOKEN_KEY.format(token=token)


# ── Request / Response models ────────────────────────────────


class SendCodeRequest(BaseModel):
    email: EmailStr


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str


class CompleteRegistrationRequest(BaseModel):
    verification_token: str
    password: str
    confirm_password: str
    display_name: str = ""
    handle: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    handle: str = ""
    token: str
    expires_at: str


class CurrentUserResponse(BaseModel):
    user_id: str
    email: str
    handle: str = ""
    display_name: str
    status: str
    created_at: str


class SimpleMessage(BaseModel):
    message: str


# ── Email sending ────────────────────────────────────────────


async def send_verification_email(to_email: str, code: str) -> None:
    """Send verification code via Agent Mail (agently-cli)."""
    subject = f"Your Kin verification code: {code}"
    body = f"""Hello,

Your Kin account verification code is:

    {code}

This code expires in {settings.verification_code_ttl_minutes} minutes.

If you did not request this, please ignore this email.

— Kin Team
"""

    loop = asyncio.get_event_loop()

    def _send():
        import subprocess

        # Step 1: get confirmation token
        proc1 = subprocess.run(
            ["agently-cli", "message", "+send",
             "--to", to_email,
             "--subject", subject,
             "--body", body],
            capture_output=True, text=True, timeout=30,
        )
        output = proc1.stdout
        # Extract JSON from output (ignore trailing tips)
        start = output.index("{")
        depth = 0
        end = start
        for i in range(start, len(output)):
            if output[i] == "{":
                depth += 1
            elif output[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        data = json.loads(output[start:end])
        if not data.get("ok"):
            raise RuntimeError(f"agently-cli error: {data.get('error', {}).get('message', 'unknown')}")
        ctk = data["data"]["confirmation_token"]

        # Step 2: confirm with same params
        proc2 = subprocess.run(
            ["agently-cli", "message", "+send",
             "--to", to_email,
             "--subject", subject,
             "--body", body,
             "--confirmation-token", ctk],
            capture_output=True, text=True, timeout=30,
        )
        out2 = proc2.stdout
        start2 = out2.index("{")
        depth2 = 0
        end2 = start2
        for i in range(start2, len(out2)):
            if out2[i] == "{":
                depth2 += 1
            elif out2[i] == "}":
                depth2 -= 1
                if depth2 == 0:
                    end2 = i + 1
                    break
        result = json.loads(out2[start2:end2])
        if not result.get("ok"):
            raise RuntimeError(f"agently-cli confirm error: {result.get('error', {}).get('message', 'unknown')}")

    await loop.run_in_executor(None, _send)


def _generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


# ── Token helpers ────────────────────────────────────────────


def create_token(user_id: str) -> tuple[str, datetime]:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": user_id, "exp": expires, "iat": datetime.now(timezone.utc)}
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, expires


async def get_current_user_dep(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: extract current user from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = auth[7:]
    return await _verify_token(token, db)


async def _verify_token(token: str, db: AsyncSession) -> User:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


# ── Step 1: Send verification code ───────────────────────────


@router.post("/send-code", response_model=SimpleMessage)
async def send_code(req: SendCodeRequest):
    """Send a 6-digit verification code to the given email."""
    email_lower = req.email.lower()

    # Check duplicate
    from agentnet.common.database import async_session

    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == email_lower))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already registered — try logging in.",
            )

    code = _generate_code()
    r = await get_redis()
    await r.setex(
        _code_key(email_lower),
        settings.verification_code_ttl_minutes * 60,
        code,
    )
    await send_verification_email(email_lower, code)
    return SimpleMessage(message=f"Verification code sent to {email_lower}")


# ── Step 2: Verify code → get verification token ─────────────


@router.post("/verify-code", response_model=SimpleMessage)
async def verify_code(req: VerifyCodeRequest):
    """Verify the code. If correct, return a verification token for completing registration."""
    email_lower = req.email.lower()
    r = await get_redis()

    stored = await r.get(_code_key(email_lower))
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code expired or not sent — request a new one.",
        )
    if stored != req.code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect verification code.",
        )

    # Delete used code
    await r.delete(_code_key(email_lower))

    # Generate a verification token tied to this email
    vtoken_raw = "".join(random.choices(string.ascii_letters + string.digits, k=48))
    vtoken_key = _token_key(vtoken_raw)
    await r.setex(vtoken_key, 30 * 60, email_lower)  # 30 min to complete registration

    return SimpleMessage(message=vtoken_raw)


# ── Step 3: Complete registration (set password) ─────────────


@router.post("/complete-registration", response_model=AuthResponse)
async def complete_registration(req: CompleteRegistrationRequest, db: AsyncSession = Depends(get_db)):
    """Complete registration: validate verification token, set password (with confirm), create user."""
    # Validate verification token
    r = await get_redis()
    cached_email = await r.get(_token_key(req.verification_token.strip()))
    if cached_email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token expired or invalid — start over.",
        )

    email_lower = cached_email

    # Validate passwords
    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters.",
        )
    if req.password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    # Final duplicate check (race condition guard)
    result = await db.execute(select(User).where(User.email == email_lower))
    if result.scalar_one_or_none():
        await r.delete(_token_key(req.verification_token.strip()))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered during this session.",
        )

    # Validate handle
    handle = req.handle.strip().lower() if req.handle else ""
    if handle:
        if not all(c.isalnum() or c in "_-" for c in handle):
            raise HTTPException(status_code=400, detail="Handle can only contain letters, numbers, underscores and hyphens.")
        result = await db.execute(select(User).where(User.handle == handle))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Handle already taken.")

    user = User(
        email=email_lower,
        password_hash=argon2.hash(req.password),
        handle=handle or None,
        display_name=req.display_name or email_lower.split("@")[0],
    )
    db.add(user)
    await db.flush()

    # Consume verification token
    await r.delete(_token_key(req.verification_token.strip()))

    token, expires = create_token(user.id)
    return AuthResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        handle=user.handle or "",
        token=token,
        expires_at=expires.isoformat(),
    )


# ── Login ────────────────────────────────────────────────────


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not argon2.verify(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended")
    token, expires = create_token(user.id)
    return AuthResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        handle=user.handle or "",
        token=token,
        expires_at=expires.isoformat(),
    )


# ── Me ───────────────────────────────────────────────────────


@router.get("/me", response_model=CurrentUserResponse)
async def me(user: User = Depends(get_current_user_dep)):
    return CurrentUserResponse(
        user_id=user.id,
        email=user.email,
        handle=user.handle or "",
        display_name=user.display_name,
        status=user.status,
        created_at=user.created_at.isoformat(),
    )
