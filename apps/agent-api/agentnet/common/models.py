"""AgentNet domain models — Sprint 1: Users, Agents, Credentials, Permissions"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentnet.common.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


def new_id() -> str:
    return f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:12]}"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    handle: Mapped[str | None] = mapped_column(String(30), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | suspended

    agents = relationship("Agent", back_populates="owner")


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    owner_user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    handle: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | paused | suspended
    automation_level: Mapped[str] = mapped_column(String(20), default="human_review")  # auto | human_review | disabled

    owner = relationship("User", back_populates="agents")
    credentials = relationship("AgentCredential", back_populates="agent")


class AgentCredential(Base, TimestampMixin):
    __tablename__ = "agent_credentials"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    scopes: Mapped[str] = mapped_column(Text, default="profile:read,messages:read,messages:send")  # comma-sep
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | revoked | expired

    agent = relationship("Agent", back_populates="credentials")


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.id"), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    effect: Mapped[str] = mapped_column(String(10), default="allow")  # allow | deny
    resource_type: Mapped[str] = mapped_column(String(50), default="*")
    resource_id: Mapped[str] = mapped_column(String(64), default="*")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Contact(Base, TimestampMixin):
    """Contact request state machine."""
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    requester_user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    addressee_user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    type: Mapped[str] = mapped_column(String(20), default="direct")
    created_by: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="")


class ConversationMember(Base, TimestampMixin):
    __tablename__ = "conversation_members"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(String(64), ForeignKey("conversations.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), default="member")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(String(64), ForeignKey("conversations.id"), nullable=False, index=True)
    sender_user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False)
    sender_agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(10), default="human")
    content_type: Mapped[str] = mapped_column(String(20), default="text")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)   # AES-256-GCM ciphertext
    encryption_nonce: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Fernet token (self-contained)
    client_message_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentEvent(Base, TimestampMixin):
    """Event queue for agents — pull + ack delivery."""
    __tablename__ = "agent_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # message.received, message.sent, etc.
    payload: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | delivered | acked | failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)


class AuditLog(Base, TimestampMixin):
    """Audit trail for agent actions and high-value operations."""
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    owner_user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), default="")
    target_id: Mapped[str] = mapped_column(String(64), default="")
    result: Mapped[str] = mapped_column(String(20), default="success")
    audit_metadata: Mapped[str] = mapped_column(Text, default="{}")


class AgentConversationACL(Base, TimestampMixin):
    """Per-conversation agent access control."""
    __tablename__ = "agent_conversation_acls"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(String(64), ForeignKey("conversations.id"), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.id"), nullable=False, index=True)
    permission: Mapped[str] = mapped_column(String(20), default="allow")  # allow | deny
    granted_by: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False)
