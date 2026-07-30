"""WebSocket handler — real-time messaging with Redis Pub/Sub scaling."""
from __future__ import annotations

import asyncio
import json
import structlog

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from agentnet.auth.routes import _verify_token
from agentnet.common.database import async_session
from agentnet.common.models import ConversationMember, Message, User
from agentnet.common.redis_client import get_redis

router = APIRouter()
log = structlog.get_logger("ws")


# ── In-memory user→WebSocket mapping (per-instance) ──
_active: dict[str, list[WebSocket]] = {}
_lock = asyncio.Lock()


async def add_connection(user_id: str, ws: WebSocket):
    async with _lock:
        if user_id not in _active:
            _active[user_id] = []
        _active[user_id].append(ws)


async def remove_connection(user_id: str, ws: WebSocket):
    async with _lock:
        if user_id in _active:
            _active[user_id] = [w for w in _active[user_id] if w != ws]
            if not _active[user_id]:
                del _active[user_id]


async def send_to_user(user_id: str, data: dict) -> bool:
    """Send to all WS connections for a user on this instance."""
    if user_id not in _active:
        return False
    sent = False
    for ws in _active[user_id]:
        try:
            await ws.send_json(data)
            sent = True
        except Exception:
            pass
    return sent


async def broadcast_to_conversation(conv_id: str, data: dict):
    """Send to all members of a conversation via Redis Pub/Sub."""
    async with async_session() as db:
        result = await db.execute(
            select(ConversationMember).where(ConversationMember.conversation_id == conv_id)
        )
        members = result.scalars().all()

    message = json.dumps({"type": "conv_broadcast", "conv_id": conv_id, "payload": data})

    # 1. Send to local connected users directly
    for m in members:
        local_sent = await send_to_user(m.user_id, {**data, "local": True})
        # 2. If user not connected locally, publish to Redis for other instances
        if not local_sent:
            redis = await get_redis()
            await redis.publish("kin:ws:broadcast", json.dumps({
                "user_id": m.user_id,
                "payload": data,
            }))
        else:
            log.info("ws_local_delivery", user_id=m.user_id[:8], conv_id=conv_id)


# ── Redis Pub/Sub listener (runs in background) ──
_listener_task: asyncio.Task | None = None


async def _redis_listener():
    """Listen for cross-instance WS messages via Redis."""
    try:
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe("kin:ws:broadcast")
        log.info("ws_redis_subscriber_started")

        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
                user_id = data.get("user_id")
                payload = data.get("payload", {})
                if user_id:
                    await send_to_user(user_id, payload)
            except Exception as e:
                log.error("ws_redis_listener_error", error=str(e))
    except asyncio.CancelledError:
        pass
    except Exception as e:
        log.error("ws_redis_listener_crashed", error=str(e))


def start_listener():
    global _listener_task
    if _listener_task is None or _listener_task.done():
        _listener_task = asyncio.create_task(_redis_listener())


def stop_listener():
    global _listener_task
    if _listener_task and not _listener_task.done():
        _listener_task.cancel()


# ── WebSocket endpoint ──
@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket with token auth + real-time message push."""
    user = None
    try:
        raw = await ws.receive_text()
        data = json.loads(raw)
        token = data.get("token", "")
        async with async_session() as db:
            user = await _verify_token(token, db)
    except Exception:
        await ws.close(code=4001)
        return

    user_id = user.id
    await ws.accept()
    await add_connection(user_id, ws)

    # Ensure Redis listener is running
    start_listener()

    try:
        await ws.send_json({"type": "connected", "user_id": user_id})

        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await ws.send_json({"type": "pong"})

            elif msg_type == "subscribe":
                """Subscribe to conversation notifications."""
                conv_id = data.get("conversation_id")
                if conv_id:
                    log.info("ws_subscribe", user_id=user_id[:8], conv_id=conv_id)
                    await ws.send_json({"type": "subscribed", "conversation_id": conv_id})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.error("ws_error", error=str(e))
    finally:
        await remove_connection(user_id, ws)
