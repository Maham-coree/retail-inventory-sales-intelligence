"""Application settings loaded from environment-specific dotenv files."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

APP_DIR = Path(__file__).resolve().parents[1]
base_values = dotenv_values(APP_DIR / ".env")
APP_ENV = os.getenv("APP_ENV") or base_values.get("APP_ENV") or "development"
APP_ENV = APP_ENV.lower()
if APP_ENV not in {"development", "production"}:
    raise RuntimeError("APP_ENV must be development or production")

selected_env = APP_DIR / f".env.{APP_ENV}"
load_dotenv(selected_env if selected_env.exists() else APP_DIR / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    database_url: str
    app_env: str
    jwt_secret: str
    jwt_expire_minutes: int
    cors_origins: tuple[str, ...]


def get_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required; configure it in fastapi_backend/.env")
    secret = os.getenv("JWT_SECRET", "")
    if not secret and APP_ENV == "production":
        raise RuntimeError("JWT_SECRET is required in production")
    if not secret:
        secret = "development-only-secret-change-before-deployment"
    try:
        expiry = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    except ValueError as exc:
        raise RuntimeError("JWT_EXPIRE_MINUTES must be an integer") from exc
    if expiry < 1:
        raise RuntimeError("JWT_EXPIRE_MINUTES must be positive")
    origins = tuple(
        item.strip()
        for item in os.getenv(
            "CORS_ORIGINS",
            "http://127.0.0.1:8000,http://localhost:8000",
        ).split(",")
        if item.strip()
    )
    return Settings(database_url, APP_ENV, secret, expiry, origins)


settings = get_settings()
