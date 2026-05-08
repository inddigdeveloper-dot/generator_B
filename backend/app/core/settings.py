from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    app_title: str = "GMB Review Generator"
    debug: bool = False

    allowed_origins: str = "http://localhost:5173"
    frontend_url: str = "http://localhost:5173"

    google_client_id: str
    google_client_secret: Optional[str] = None  # not used in ID-token flow; reserved for server-side OAuth

    gemini_api_key: Optional[str] = None

    # OpenRouter — free-tier multi-model provider (default)
    openrouter_api_key: Optional[str] = None

    # Redis URL for shared rate-limit storage across workers (optional, falls back to in-memory)
    redis_url: Optional[str] = None

    # LLM provider selection: "openrouter" | "gemini" | "ollama" | "openai_compat"
    llm_provider: str = "openrouter"

    # Ollama (private VPS)
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = "llama3.2:3b"

    # OpenAI-compatible (vLLM, LM Studio, Together, etc.)
    openai_compat_url: Optional[str] = None
    openai_compat_key: Optional[str] = None
    openai_compat_model: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )


settings = Settings()
