"""AgentNet API — configuration via env vars + .env"""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Kin"
    app_env: str = "production"
    debug: bool = True
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://agentnet:changeme_dev_only@localhost:5432/agentnet"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "changeme_in_production_use_openssl_rand_64"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Email verification (SMTP)
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = ""
    smtp_from_name: str = "Kin"
    verification_code_ttl_minutes: int = 10
    verification_from_email: str = "noreply@kin.cq.cn"

    # Message encryption (AES-256-GCM at rest)
    # Auto-generated on first read if not set
    message_encryption_key: str = ""

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
