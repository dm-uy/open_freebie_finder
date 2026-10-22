"""In-memory circular ring buffer for request telemetry."""
import asyncio
import collections
import logging
from typing import Optional, List
from backend.app.config import get_settings
from backend.app.core.telemetry.models import RequestTrace, TelemetryStats

logger = logging.getLogger("backend.app.telemetry")


class TelemetryStore:
    """Thread-safe bounded in-memory FIFO buffer for request telemetry traces."""

    def __init__(self, max_records: int = 500) -> None:
        self._max_records = max_records
        self._buffer: collections.deque[RequestTrace] = collections.deque(maxlen=max_records)
        self._lock = asyncio.Lock()
        self._total_requests: int = 0
        self._successful_requests: int = 0
        self._failed_requests: int = 0
        self._failover_count: int = 0

    async def record_trace(self, trace: RequestTrace) -> None:
        """Record a completed request trace into the ring buffer.

        Guaranteed to be fail-safe: any unexpected exception is caught and logged
        so that client request completion is never disrupted (BR-4, AC-9).
        """
        try:
            async with self._lock:
                self._total_requests += 1
                if trace.success:
                    self._successful_requests += 1
                else:
                    self._failed_requests += 1

                if len(trace.attempts) >= 2:
                    self._failover_count += 1

                self._buffer.append(trace)
        except Exception as exc:
            logger.warning("Failed to record request telemetry trace: %s", str(exc))

    async def get_recent(self, limit: int = 50) -> List[RequestTrace]:
        """Return the most recent traces ordered newest-first."""
        async with self._lock:
            # Buffer stores oldest to newest; reverse to return newest-first
            traces = list(self._buffer)
            traces.reverse()
            return traces[:limit]

    async def get_stats(self, total_cached_models: int = 0) -> TelemetryStats:
        """Return aggregated operational telemetry metrics."""
        async with self._lock:
            return TelemetryStats(
                total_requests=self._total_requests,
                successful_requests=self._successful_requests,
                failed_requests=self._failed_requests,
                failover_count=self._failover_count,
                total_cached_models=total_cached_models,
            )

    async def clear(self) -> None:
        """Clear all stored traces and counters (useful for isolated tests)."""
        async with self._lock:
            self._buffer.clear()
            self._total_requests = 0
            self._successful_requests = 0
            self._failed_requests = 0
            self._failover_count = 0


_telemetry_store: Optional[TelemetryStore] = None


def get_telemetry_store() -> TelemetryStore:
    """Return singleton instance of TelemetryStore initialized from configuration."""
    global _telemetry_store
    if _telemetry_store is None:
        settings = get_settings()
        _telemetry_store = TelemetryStore(max_records=settings.max_telemetry_records)
    return _telemetry_store
