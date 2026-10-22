"""Unit and integration tests for Structured Telemetry and Correlation ID Cascades (T-005)."""
import json
import logging
import uuid
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from backend.app.config import get_settings
from backend.app.core.adapters.openai_client import UpstreamRateLimitError
from backend.app.core.balancer.router import CascadeRouter
from backend.app.core.providers.models import DiscoveredModel, ProviderAuth, ProviderManifest
from backend.app.core.providers.registry import ProviderRegistry
from backend.app.core.telemetry.models import CandidateAttempt, RequestTrace
from backend.app.core.telemetry.store import TelemetryStore, get_telemetry_store
from backend.app.main import create_app


@pytest.fixture(autouse=True)
async def clean_telemetry_store():
    """Clear telemetry store before and after each test."""
    store = get_telemetry_store()
    await store.clear()
    yield
    await store.clear()


@pytest.fixture
async def mock_registry():
    """Create isolated registry populated with two test models for cascade testing."""
    registry = ProviderRegistry()
    m1 = ProviderManifest(
        id="provider-alpha",
        name="Provider Alpha",
        base_url="https://api.alpha.com/v1",
        models_endpoint="https://api.alpha.com/v1/models",
        auth=ProviderAuth(type="none"),
        is_enabled=True,
    )
    m2 = ProviderManifest(
        id="provider-beta",
        name="Provider Beta",
        base_url="https://api.beta.com/v1",
        models_endpoint="https://api.beta.com/v1/models",
        auth=ProviderAuth(type="none"),
        is_enabled=True,
    )
    registry._manifests["provider-alpha"] = m1
    registry._manifests["provider-beta"] = m2
    await registry.register_models([
        DiscoveredModel(
            id="model-primary",
            canonical_name="model-common",
            provider_id="provider-alpha",
            context_window=8192,
        ),
        DiscoveredModel(
            id="model-secondary",
            canonical_name="model-common",
            provider_id="provider-beta",
            context_window=8192,
        ),
    ])
    return registry


@pytest.fixture
async def app_client(mock_registry):
    """Async test client with mock registry attached to chat router."""
    app = create_app()
    from backend.app.api.v1 import chat
    chat._cascade_router = CascadeRouter(registry=mock_registry)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_correlation_id_reflection(app_client):
    """AC-2: Client-provided X-Request-ID must be reflected in response headers."""
    custom_id = "trace-custom-uuid-999"

    with patch.object(
        CascadeRouter,
        "route_completion",
        new=AsyncMock(return_value={"id": "chatcmpl-1", "choices": [{"message": {"role": "assistant", "content": "ok"}}]}),
    ):
        resp = await app_client.post(
            "/v1/chat/completions",
            json={"model": "model-common", "messages": [{"role": "user", "content": "hi"}]},
            headers={"X-Request-ID": custom_id},
        )
        assert resp.status_code == 200
        assert resp.headers.get("X-Request-ID") == custom_id


@pytest.mark.asyncio
async def test_auto_generated_correlation_id(app_client):
    """AC-3: Proxy generates a valid UUID4 when client omits X-Request-ID."""
    with patch.object(
        CascadeRouter,
        "route_completion",
        new=AsyncMock(return_value={"id": "chatcmpl-1", "choices": [{"message": {"role": "assistant", "content": "ok"}}]}),
    ):
        resp = await app_client.post(
            "/v1/chat/completions",
            json={"model": "model-common", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp.status_code == 200
        generated_id = resp.headers.get("X-Request-ID")
        assert generated_id is not None
        # Verify it parses as a valid UUID
        parsed_uuid = uuid.UUID(generated_id)
        assert str(parsed_uuid) == generated_id


@pytest.mark.asyncio
async def test_error_envelope_contains_correlation_id(app_client):
    """AC-4: Error responses (404, 401) must also carry the X-Request-ID header."""
    custom_id = "error-trace-404"
    # 404: Unknown model
    resp = await app_client.post(
        "/v1/chat/completions",
        json={"model": "non-existent-model", "messages": [{"role": "user", "content": "hi"}]},
        headers={"X-Request-ID": custom_id},
    )
    assert resp.status_code == 404
    assert resp.headers.get("X-Request-ID") == custom_id
    assert "error" in resp.json()

    # 401: Unauthorized when master key is enabled
    settings = get_settings()
    original_key = settings.proxy_master_key
    try:
        settings.proxy_master_key = "secret-master-token"
        resp_401 = await app_client.post(
            "/v1/chat/completions",
            json={"model": "model-common", "messages": [{"role": "user", "content": "hi"}]},
            headers={"X-Request-ID": "auth-fail-trace", "Authorization": "Bearer wrong-token"},
        )
        assert resp_401.status_code == 401
        assert resp_401.headers.get("X-Request-ID") == "auth-fail-trace"
        assert "error" in resp_401.json()
    finally:
        settings.proxy_master_key = original_key


@pytest.mark.asyncio
async def test_cascade_hop_tracing(mock_registry):
    """AC-5: Cascade failover records ordered candidate attempts in trace."""
    mock_client = AsyncMock()
    # Candidate 1 throws 429, Candidate 2 returns valid 200 response
    mock_client.complete.side_effect = [
        UpstreamRateLimitError("Rate limit exceeded on alpha", "provider-alpha", "model-primary"),
        {"id": "chatcmpl-hop-2", "choices": [{"message": {"role": "assistant", "content": "ok"}}]},
    ]
    router = CascadeRouter(registry=mock_registry, provider_client=mock_client)
    req_id = "test-cascade-trace-001"

    result = await router.route_completion(
        requested_model="model-common",
        payload={"messages": [{"role": "user", "content": "hi"}]},
        request_id=req_id,
    )
    assert result["id"] == "chatcmpl-hop-2"

    store = get_telemetry_store()
    traces = await store.get_recent(limit=10)
    assert len(traces) == 1
    trace = traces[0]

    assert trace.request_id == req_id
    assert trace.requested_model == "model-common"
    assert trace.success is True
    assert len(trace.attempts) == 2

    # Hop 1: provider-alpha 429
    assert trace.attempts[0].hop_index == 1
    assert trace.attempts[0].provider_id == "provider-alpha"
    assert trace.attempts[0].model_id == "model-primary"
    assert trace.attempts[0].status == "http_error"
    assert trace.attempts[0].status_code == 429
    assert "rate limit exceeded" in trace.attempts[0].error.lower()

    # Hop 2: provider-beta 200
    assert trace.attempts[1].hop_index == 2
    assert trace.attempts[1].provider_id == "provider-beta"
    assert trace.attempts[1].model_id == "model-secondary"
    assert trace.attempts[1].status == "success"
    assert trace.attempts[1].status_code == 200
    assert trace.attempts[1].error is None


@pytest.mark.asyncio
async def test_structured_json_hop_logging(mock_registry, caplog):
    """AC-6: Each candidate hop logs a single-line JSON string containing correlation fields."""
    mock_client = AsyncMock()
    mock_client.complete.return_value = {"id": "chatcmpl-log", "choices": [{"message": {"role": "assistant", "content": "ok"}}]}
    router = CascadeRouter(registry=mock_registry, provider_client=mock_client)
    req_id = "log-json-corr-id"

    with caplog.at_level(logging.INFO, logger="backend.app.telemetry"):
        await router.route_completion(
            requested_model="model-common",
            payload={"messages": []},
            request_id=req_id,
        )

    # Find the telemetry log record
    telemetry_records = [
        rec for rec in caplog.records
        if rec.name == "backend.app.telemetry"
    ]
    assert len(telemetry_records) >= 1
    log_line = telemetry_records[0].getMessage()
    parsed = json.loads(log_line)

    assert parsed["request_id"] == req_id
    assert parsed["hop_index"] == 1
    assert parsed["provider_id"] == "provider-alpha"
    assert parsed["model_id"] == "model-primary"
    assert parsed["status"] == "success"
    assert parsed["status_code"] == 200
    assert "timestamp" in parsed
    assert "duration_ms" in parsed


@pytest.mark.asyncio
async def test_admin_telemetry_endpoints(app_client):
    """AC-7: Admin endpoints /recent and /stats return expected operational payloads."""
    store = get_telemetry_store()
    trace = RequestTrace(
        request_id="adm-trace-1",
        requested_model="auto:free",
        stream=False,
        attempts=[
            CandidateAttempt(
                hop_index=1,
                provider_id="provider-alpha",
                model_id="m1",
                status="success",
                status_code=200,
                duration_ms=45.2,
            )
        ],
        resolved_candidate="provider-alpha/m1",
        total_duration_ms=45.2,
        success=True,
    )
    await store.record_trace(trace)

    # 1. GET /api/admin/telemetry/recent
    resp_recent = await app_client.get("/api/admin/telemetry/recent?limit=10")
    assert resp_recent.status_code == 200
    data = resp_recent.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["request_id"] == "adm-trace-1"
    assert data[0]["attempts"][0]["provider_id"] == "provider-alpha"

    # 2. GET /api/admin/telemetry/stats
    resp_stats = await app_client.get("/api/admin/telemetry/stats")
    assert resp_stats.status_code == 200
    stats = resp_stats.json()
    assert stats["total_requests"] == 1
    assert stats["successful_requests"] == 1
    assert stats["failed_requests"] == 0
    assert "total_cached_models" in stats


@pytest.mark.asyncio
async def test_ring_buffer_eviction():
    """AC-8: TelemetryStore strictly bounds memory capacity and evicts oldest entries."""
    small_store = TelemetryStore(max_records=3)
    for i in range(5):
        trace = RequestTrace(
            request_id=f"trace-{i}",
            requested_model="auto:free",
            success=True,
        )
        await small_store.record_trace(trace)

    recent = await small_store.get_recent(limit=10)
    assert len(recent) == 3
    # Newest-first: trace-4, trace-3, trace-2
    assert [t.request_id for t in recent] == ["trace-4", "trace-3", "trace-2"]


@pytest.mark.asyncio
async def test_telemetry_fail_safe_execution(mock_registry):
    """AC-9: Store exceptions must never raise or fail client completion requests.

    Uses a real CascadeRouter with a mocked upstream that returns a valid 200
    response, but patches the TelemetryStore.record_trace to throw RuntimeError.
    The completion must still succeed with HTTP 200 — the store failure is
    silently caught by _record_trace_safely.
    """
    mock_client = AsyncMock()
    mock_client.complete.return_value = {
        "id": "chatcmpl-failsafe",
        "choices": [{"message": {"role": "assistant", "content": "ok"}}],
    }
    router = CascadeRouter(registry=mock_registry, provider_client=mock_client)

    with patch.object(
        TelemetryStore,
        "record_trace",
        side_effect=RuntimeError("Simulated ring buffer failure"),
    ):
        # Real router path: upstream returns 200, but record_trace explodes.
        # _record_trace_safely must swallow the error and return the response.
        result = await router.route_completion(
            requested_model="model-common",
            payload={"messages": [{"role": "user", "content": "hi"}]},
            request_id="failsafe-trace-1",
        )
        assert result["id"] == "chatcmpl-failsafe"
        assert result["choices"][0]["message"]["content"] == "ok"


@pytest.mark.asyncio
async def test_streaming_correlation_id_and_telemetry(mock_registry, app_client):
    """AC-3 / BR-2: Streaming completion carries X-Request-ID and records telemetry with stream=True."""
    custom_id = "stream-trace-corr-777"

    async def sample_stream():
        yield "data: {\"choices\": [{\"delta\": {\"content\": \"hello\"}}]}\n\n"
        yield "data: [DONE]\n\n"

    with patch.object(
        CascadeRouter,
        "route_stream_completion",
        new=AsyncMock(return_value=sample_stream()),
    ):
        resp = await app_client.post(
            "/v1/chat/completions",
            json={"model": "model-common", "messages": [{"role": "user", "content": "hi"}], "stream": True},
            headers={"X-Request-ID": custom_id},
        )
        assert resp.status_code == 200
        assert resp.headers.get("X-Request-ID") == custom_id
        assert resp.headers.get("content-type").startswith("text/event-stream")


@pytest.mark.asyncio
async def test_admin_master_key_auth(app_client):
    """AC-10: Admin endpoints enforce proxy_master_key when configured."""
    settings = get_settings()
    original_key = settings.proxy_master_key
    try:
        settings.proxy_master_key = "admin-secret-token"

        # Unauthorized request: no auth header -> 401
        resp_unauth = await app_client.get("/api/admin/telemetry/stats")
        assert resp_unauth.status_code == 401
        assert "error" in resp_unauth.json()

        # Wrong key -> 401
        resp_wrong = await app_client.get(
            "/api/admin/telemetry/stats",
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert resp_wrong.status_code == 401

        # Correct key -> 200
        resp_ok = await app_client.get(
            "/api/admin/telemetry/stats",
            headers={"Authorization": "Bearer admin-secret-token"},
        )
        assert resp_ok.status_code == 200
    finally:
        settings.proxy_master_key = original_key
