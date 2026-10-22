"""Admin Telemetry and Observability Endpoints."""
import hmac
from typing import Optional, List, Any
from fastapi import APIRouter, Header, Query, status
from fastapi.responses import JSONResponse
from backend.app.config import get_settings
from backend.app.core.providers.registry import get_registry
from backend.app.core.telemetry.models import RequestTrace, TelemetryStats
from backend.app.core.telemetry.store import get_telemetry_store

router = APIRouter(prefix="/telemetry", tags=["Admin Telemetry"])


def _verify_admin_auth(authorization: Optional[str]) -> Optional[JSONResponse]:
    """Verify authorization against optional proxy_master_key."""
    settings = get_settings()
    if not settings.proxy_master_key:
        return None  # Permissive dev mode if master key not configured

    expected = f"Bearer {settings.proxy_master_key}"
    if not authorization or not hmac.compare_digest(authorization.strip(), expected):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "message": "Incorrect API key provided.",
                    "type": "invalid_request_error",
                    "code": 401,
                }
            },
        )
    return None


@router.get("/recent", response_model=List[RequestTrace])
async def get_recent_telemetry(
    limit: int = Query(default=50, ge=1, le=500),
    authorization: Optional[str] = Header(None),
) -> Any:
    """Retrieve recent request traces ordered newest-first."""
    auth_err = _verify_admin_auth(authorization)
    if auth_err:
        return auth_err

    store = get_telemetry_store()
    traces = await store.get_recent(limit=limit)
    return traces


@router.get("/stats", response_model=TelemetryStats)
async def get_telemetry_stats(
    authorization: Optional[str] = Header(None),
) -> Any:
    """Retrieve aggregated operational metrics and registered model count."""
    auth_err = _verify_admin_auth(authorization)
    if auth_err:
        return auth_err

    registry = get_registry()
    total_cached_models = len(registry.get_models())

    store = get_telemetry_store()
    stats = await store.get_stats(total_cached_models=total_cached_models)
    return stats
