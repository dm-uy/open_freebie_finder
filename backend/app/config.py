"""Application Configuration."""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable loading."""

    # Server Configuration
    app_name: str = "Open Freebie Finder"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS Configuration
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Database
    database_url: str = "sqlite+aiosqlite:///backend/data/freebie_finder.db"

    # Discovery Configuration
    discovery_interval_seconds: int = 900  # 15 minutes
    circuit_breaker_cooldown_seconds: int = 60

    # Provider API Keys (optional in environment, can also be supplied via UI/API)
    openrouter_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None
    google_ai_studio_api_key: Optional[str] = None
    github_pat_token: Optional[str] = None
    cerebras_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    cloudflare_api_token: Optional[str] = None
    cloudflare_account_id: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
