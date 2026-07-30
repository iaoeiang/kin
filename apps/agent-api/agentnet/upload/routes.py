"""File upload endpoint for message attachments."""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from agentnet.auth.routes import get_current_user_dep
from agentnet.common.config import settings
from agentnet.common.models import User

router = APIRouter(prefix="/api/upload", tags=["upload"])

UPLOAD_DIR = Path(settings.upload_dir) if hasattr(settings, 'upload_dir') and settings.upload_dir else Path("/home/agentuser/agentnet/uploads")
ALLOWED_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "application/pdf": "pdf",
    "text/plain": "txt",
}
MAX_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user_dep),
):
    """Upload a file and return its URL."""
    # Validate type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_TYPES.keys())}")

    # Validate size
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, detail="File too large (max 10MB)")

    # Save
    ext = ALLOWED_TYPES[file.content_type]
    filename = f"{uuid.uuid4().hex[:16]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filepath = UPLOAD_DIR / filename
    filepath.write_bytes(content)

    return {
        "status": "ok",
        "url": f"/uploads/{filename}",
        "filename": filename,
        "content_type": file.content_type,
        "size": len(content),
    }


@router.get("/config")
async def upload_config(user: User = Depends(get_current_user_dep)):
    """Return upload configuration for the frontend."""
    return {
        "max_size": MAX_SIZE,
        "max_size_mb": MAX_SIZE / (1024 * 1024),
        "allowed_types": list(ALLOWED_TYPES.keys()),
        "allowed_extensions": [f".{ext}" for ext in ALLOWED_TYPES.values()],
    }
