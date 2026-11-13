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


def _read_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    if value in {"true", "1", "yes", "on"}:
        return True
    if value in {"false", "0", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean")


@dataclass(frozen=True)
class Settings:
    database_url: str
    app_env: str
    jwt_secret: str
    jwt_expire_minutes: int
    cors_origins: tuple[str, ...]
    chatbot_enabled: bool
    chatbot_max_message_length: int
    chatbot_llm_enabled: bool
    chatbot_llm_base_url: str
    chatbot_llm_api_key: str
    chatbot_llm_model: str


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
    try:
        chatbot_max_message_length = int(os.getenv("CHATBOT_MAX_MESSAGE_LENGTH", "500"))
    except ValueError as exc:
        raise RuntimeError("CHATBOT_MAX_MESSAGE_LENGTH must be an integer") from exc
    if not 1 <= chatbot_max_message_length <= 500:
        raise RuntimeError("CHATBOT_MAX_MESSAGE_LENGTH must be between 1 and 500")
    chatbot_llm_enabled = _read_bool("CHATBOT_LLM_ENABLED", False)
    chatbot_llm_base_url = os.getenv("CHATBOT_LLM_BASE_URL", "").strip()
    chatbot_llm_model = os.getenv("CHATBOT_LLM_MODEL", "").strip()
    if chatbot_llm_enabled and (not chatbot_llm_base_url or not chatbot_llm_model):
        raise RuntimeError(
            "CHATBOT_LLM_BASE_URL and CHATBOT_LLM_MODEL are required when "
            "CHATBOT_LLM_ENABLED is true"
        )
    return Settings(
        database_url,
        APP_ENV,
        secret,
        expiry,
        origins,
        _read_bool("CHATBOT_ENABLED", True),
        chatbot_max_message_length,
        chatbot_llm_enabled,
        chatbot_llm_base_url,
        os.getenv("CHATBOT_LLM_API_KEY", "").strip(),
        chatbot_llm_model,
    )


settings = get_settings()
