"""Application Configuration."""
from functools import lru_cache
from typing import Optional
from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable loading."""

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings,
                                   dotenv_settings, file_secret_settings):
        def typed(source):
            def read():
                values = source()
                for name in ("max_failover_attempts", "circuit_breaker_cooldown_seconds", "eligibility_refresh_seconds", "eligibility_ttl_seconds"):
                    raw = values.get(name)
                    if isinstance(raw, str) and raw.isascii() and raw.isdigit():
                        values[name] = int(raw)
                return values
            return read
        return init_settings, typed(env_settings), typed(dotenv_settings), file_secret_settings

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
    circuit_breaker_cooldown_seconds: int = Field(default=60, ge=1, le=300, strict=True)
    max_telemetry_records: int = 500
    max_failover_attempts: int = Field(default=3, ge=1, le=10, strict=True)
    eligibility_refresh_seconds: int = Field(default=60, ge=10, le=300, strict=True)
    eligibility_ttl_seconds: int = Field(default=120, ge=20, le=600, strict=True)

    @model_validator(mode="after")
    def evidence_intervals(self):
        if self.eligibility_ttl_seconds < 2 * self.eligibility_refresh_seconds:
            raise ValueError("Invalid eligibility interval configuration.")
        return self

    free_account_confirmations: list[str] = Field(default_factory=list)

    @field_validator("free_account_confirmations", mode="before")
    @classmethod
    def account_confirmations(cls, value):
        allowed = {"groq", "nvidia_nim", "mistral", "huggingface"}
        if (not isinstance(value, list) or any(type(v) is not str or v not in allowed for v in value)
                or len(set(value)) != len(value)):
            raise ValueError("Invalid account assertion configuration.")
        return value

    routing_provider_priority: list[str] = Field(default_factory=list)

    @field_validator("routing_provider_priority")
    @classmethod
    def unique_priority(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("Invalid routing priority configuration.")
        return value

    # Master API Key (Optional: if set, proxy validates Authorization: Bearer <key>)
    proxy_master_key: Optional[str] = None

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
    try:
        return Settings()
    except (ValidationError, ValueError):
        raise ValueError("Invalid application configuration.") from None
