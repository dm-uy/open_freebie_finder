"""Request and diagnostic schemas for isolated provider validation."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints, model_validator

from backend.app.core.providers.models import ProviderManifest

Identifier = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=512)]


class ProviderValidationRequest(BaseModel):
    """Select exactly one provider without persisting a credential override."""

    model_config = ConfigDict(extra="forbid")
    provider_id: Identifier | None = None
    manifest: ProviderManifest | None = None
    api_key: SecretStr | None = Field(default=None, min_length=1, max_length=8192)
    model_id: Identifier | None = None

    @model_validator(mode="after")
    def check_selection(self) -> "ProviderValidationRequest":
        if (self.provider_id is None) == (self.manifest is None):
            raise ValueError("Select exactly one provider.")
        for value in (self.provider_id, self.model_id):
            if value is not None and not value.strip():
                raise ValueError("Identifiers must not be blank.")
        if self.api_key is not None and not self.api_key.get_secret_value().strip():
            raise ValueError("Credentials must not be blank.")
        return self


class ValidationCheck(BaseModel):
    name: Literal["configuration", "catalog", "completion"]
    status: Literal["passed", "failed", "skipped"]
    code: str | None = None
    http_status: int | None = None
    duration_ms: float = 0.0
    message: str


class ProviderValidationReport(BaseModel):
    provider_id: str
    valid: bool = False
    model_id: str | None = None
    eligible_model_count: int = 0
    model_ids: list[str] = Field(default_factory=list)
    checks: list[ValidationCheck] = Field(default_factory=list)
    total_duration_ms: float = 0.0
