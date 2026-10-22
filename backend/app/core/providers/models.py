"""Pydantic schemas for declarative providers and discovered models."""
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class ProviderAuth(BaseModel):
    """Authentication configuration for an upstream provider."""

    type: Literal["bearer", "header", "none"] = Field(
        default="bearer",
        description="Authentication method: bearer token, custom header, or none (local).",
    )
    api_key_env: Optional[str] = Field(
        default=None,
        description="Name of the environment variable containing the provider API key.",
    )
    custom_header_name: Optional[str] = Field(
        default=None,
        description="Header name when type is 'header' (e.g., 'X-API-Key').",
    )


class DiscoveryRule(BaseModel):
    """Rule for discovering and filtering free models from a provider."""

    type: Literal["openrouter_free", "all_available", "regex", "manual"] = Field(
        default="all_available",
        description="Discovery strategy for detecting free models.",
    )
    filter_expression: Optional[str] = Field(
        default=None,
        description="Optional filter expression (e.g. regex pattern matching model.id).",
    )
    model_id_field: str = Field(
        default="id",
        description="JSON key identifying the model ID in the provider's /models response.",
    )
    context_length_field: str = Field(
        default="context_length",
        description="JSON key identifying context window size in the provider's response.",
    )
    static_models: list[str] = Field(
        default_factory=list,
        description="Explicit list of model IDs when discovery type is 'manual'.",
    )


class ProviderManifest(BaseModel):
    """Declarative specification for an upstream inference provider."""

    id: str = Field(
        ...,
        description="Unique identifier for the provider (e.g., 'openrouter', 'groq').",
    )
    name: str = Field(
        ...,
        description="Human-readable display name.",
    )
    base_url: str = Field(
        ...,
        description="Base URL for OpenAI-compatible completions API.",
    )
    models_endpoint: str = Field(
        ...,
        description="Full URL or relative endpoint for listing available models.",
    )
    auth: ProviderAuth = Field(
        default_factory=ProviderAuth,
        description="Authentication configuration.",
    )
    discovery: DiscoveryRule = Field(
        default_factory=DiscoveryRule,
        description="Discovery strategy and rules.",
    )
    is_enabled: bool = Field(
        default=True,
        description="Whether this provider is currently enabled in routing pools.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the provider tier, limits, and quotas.",
    )

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Ensure provider ID is a non-empty alphanumeric lowercase string with underscores."""
        clean = v.strip().lower()
        if not clean or not clean.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Provider ID must contain only alphanumeric characters, dashes, or underscores.")
        return clean

    @field_validator("base_url", "models_endpoint")
    @classmethod
    def validate_urls(cls, v: str) -> str:
        """Ensure URLs are valid http/https URLs (allowing template parameters like {account_id})."""
        clean = v.strip()
        if not (clean.startswith("http://") or clean.startswith("https://")):
            raise ValueError(f"URL must start with http:// or https://: {clean}")
        return clean


class DiscoveredModel(BaseModel):
    """Represents a discovered model instance available through a specific provider."""

    id: str = Field(
        ...,
        description="Raw provider model identifier (e.g., 'meta-llama/llama-3.3-70b-instruct:free').",
    )
    canonical_name: str = Field(
        ...,
        description="Normalized canonical model name without provider-specific suffixes (e.g. 'meta-llama/llama-3.3-70b-instruct').",
    )
    provider_id: str = Field(
        ...,
        description="Identifier of the provider hosting this model instance.",
    )
    context_window: int = Field(
        default=4096,
        description="Maximum supported context window size in tokens.",
    )
    is_free: bool = Field(
        default=True,
        description="Flag denoting zero-cost status.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider metadata (pricing details, architecture info, etc.).",
    )
