from pathlib import Path
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the backend/ directory so the default .env path works regardless
# of which directory uvicorn is started from.
_BACKEND_DIR = Path(__file__).resolve().parents[2]

# Env-file search order (later file wins on conflict):
#   1. backend/.env           — standard, committed template filled locally
#   2. developer secrets file — Windows dev machine override (ignored on Linux)
_ENV_FILES = (
    str(_BACKEND_DIR / ".env"),
    r"C:\hk\secrets\secret_generator.env",
)


class Settings(BaseSettings):
    database_url: str

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        # Railway (and many PaaS) emit postgres:// or postgresql:// without
        # the driver suffix that SQLAlchemy requires.
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg2://", 1)
        if v.startswith("postgresql://") and "+psycopg2" not in v:
            return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    app_title: str = "GMB Review Generator"
    debug: bool = False

    allowed_origins: str = "http://localhost:5173"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    google_client_id: str
    google_client_secret: Optional[str] = None  # reserved for server-side OAuth

    gemini_api_key: Optional[str] = None

    openrouter_api_key: Optional[str] = None
    openrouter_use_paid: bool = False

    groq_api_key: Optional[str] = None

    llm_provider: str = "openrouter"

    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = "llama3.2:3b"

    openai_compat_url: Optional[str] = None
    openai_compat_key: Optional[str] = None
    openai_compat_model: Optional[str] = None

    # Redis — optional, enables shared rate limiting + cache across workers
    redis_url: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )


settings = Settings()
