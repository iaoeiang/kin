"""AgentNet API entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agentnet.common.database import settings
from agentnet.auth.routes import router as auth_router, get_current_user_dep
from agentnet.agents.routes import router as agents_router
from agentnet.credentials.routes import router as credentials_router
from agentnet.common.agent_session import router as agent_api_router
from agentnet.contacts.routes import router as contacts_router
from agentnet.conversations.routes import router as conversations_router
from agentnet.websocket.handler import router as ws_router
from agentnet.audit.routes import router as audit_router
from agentnet.events.routes import router as events_router
from agentnet.security.routes import router as security_router
from agentnet.messages.routes import router as messages_router
from agentnet.users.routes import router as users_router
from agentnet.upload.routes import router as upload_router
from agentnet.common.rate_limiter import add_rate_limiting
from agentnet.admin.routes import router as admin_router
from agentnet.common.logging_config import setup_logging

import structlog

import agentnet.common.models  # noqa — ensure models loaded


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    log = structlog.get_logger("http")
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    log.info("request", method=request.method, path=request.url.path,
             status=response.status_code, duration_ms=round(duration * 1000, 1))
    return response


app.include_router(auth_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(credentials_router, prefix="/api")
app.include_router(agent_api_router)
app.include_router(contacts_router)
app.include_router(conversations_router)
app.include_router(ws_router)
app.include_router(audit_router)
app.include_router(events_router)
app.include_router(security_router)
app.include_router(messages_router)
app.include_router(users_router)
app.include_router(upload_router)
app.include_router(admin_router)
add_rate_limiting(app)

# Serve uploaded files
from pathlib import Path
upload_dir = Path("/home/agentuser/agentnet/uploads")
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "version": "0.1.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
    )
