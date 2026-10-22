"""Data models for structured request telemetry and cascade tracing."""
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field


class CandidateAttempt(BaseModel):
    """Telemetry record for a single candidate attempt within a cascade sequence."""
    hop_index: int
    provider_id: str
    model_id: str
    status: str  # "success" | "cooldown_skipped" | "http_error" | "stream_error"
    status_code: Optional[int] = None
    duration_ms: float
    error: Optional[str] = None


class RequestTrace(BaseModel):
    """Complete trace record for an incoming completion request spanning all candidate hops."""
    request_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    requested_model: str
    stream: bool = False
    attempts: List[CandidateAttempt] = Field(default_factory=list)
    resolved_candidate: Optional[str] = None
    total_duration_ms: float = 0.0
    success: bool = False


class TelemetryStats(BaseModel):
    """Aggregated operational metrics for administrative observability."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    failover_count: int = 0
    total_cached_models: int = 0
