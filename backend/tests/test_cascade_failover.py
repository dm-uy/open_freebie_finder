from backend.tests.eligibility_fixtures import install_fixture_evidence
"""Unit and Integration Tests for Two-Tier Cascade Failover and Circuit Breaker."""
import httpx
import pytest
from backend.app.config import get_settings
from backend.app.core.adapters.openai_client import (
    OpenAIProviderClient,
    UpstreamRateLimitError,
)
from backend.app.core.balancer.router import CascadeRouter
from backend.app.core.providers.models import DiscoveredModel
from backend.app.core.providers.registry import ProviderRegistry


@pytest.fixture
def test_registry():
    """Create test registry with sample manifests and models."""
    registry = ProviderRegistry()
    install_fixture_evidence(registry)
    registry.load_manifests()
    return registry


@pytest.mark.asyncio
async def test_tier1_same_model_failover(test_registry):
    """AC-7: Verify that when Candidate 1 returns 503, router transparently falls over to Candidate 2."""
    # Register same canonical model under two different active providers (local_ollama and groq)
    # Give groq a dummy key for testing
    groq_manifest = test_registry.get_manifest("groq")
    assert groq_manifest is not None
    ollama_manifest = test_registry.get_manifest("local_ollama")
    assert ollama_manifest is not None

    test_models = [
        DiscoveredModel(
            id="llama-3.3-70b-primary",
            canonical_name="meta-llama/llama-3.3-70b-instruct",
            provider_id="local_ollama",
            context_window=131072,
            is_free=True,
        ),
        DiscoveredModel(
            id="llama-3.3-70b-secondary",
            canonical_name="meta-llama/llama-3.3-70b-instruct",
            provider_id="local_ollama",
            context_window=131072,
            is_free=True,
        ),
    ]
    await test_registry.register_models(test_models)

    call_counts = {"primary": 0, "secondary": 0}

    def mock_handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode("utf-8")
        if "llama-3.3-70b-primary" in body:
            call_counts["primary"] += 1
            # Primary candidate hits service failure!
            return httpx.Response(503, json={"error": {"message": "Service failure reached"}})
        elif "llama-3.3-70b-secondary" in body:
            call_counts["secondary"] += 1
            return httpx.Response(200, json={
                "id": "chatcmpl-failover-success",
                "object": "chat.completion",
                "created": 1729600000,
                "model": "llama-3.3-70b-secondary",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "Failover success!"}}],
            })
        return httpx.Response(404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    router = CascadeRouter(
        registry=test_registry,
        provider_client=OpenAIProviderClient(http_client=mock_client),
    )

    response = await router.route_completion(
        requested_model="meta-llama/llama-3.3-70b-instruct",
        payload={"messages": [{"role": "user", "content": "Hello"}]},
    )

    # Both candidates were called sequentially
    assert call_counts["primary"] == 1
    assert call_counts["secondary"] == 1

    # Client receives successful 200 OK with masked canonical name
    assert response["choices"][0]["message"]["content"] == "Failover success!"
    assert response["model"] == "meta-llama/llama-3.3-70b-instruct"

    # Candidate 1 is placed on cooldown
    assert router.is_on_cooldown("local_ollama", "llama-3.3-70b-primary") is True
    # Candidate 2 is NOT on cooldown
    assert router.is_on_cooldown("local_ollama", "llama-3.3-70b-secondary") is False


@pytest.mark.asyncio
async def test_circuit_breaker_cooldown(test_registry):
    """AC-9: Verify that a candidate placed on cooldown is excluded from subsequent candidate queues."""
    test_models = [
        DiscoveredModel(
            id="model-a",
            canonical_name="model-test",
            provider_id="local_ollama",
            context_window=4096,
            is_free=True,
        ),
        DiscoveredModel(
            id="model-b",
            canonical_name="model-test",
            provider_id="local_ollama",
            context_window=4096,
            is_free=True,
        ),
    ]
    await test_registry.register_models(test_models)

    router = CascadeRouter(registry=test_registry)
    # Initially both are available
    candidates = router.resolve_candidates("model-test")
    assert len(candidates) == 2

    # Put model-a on cooldown
    router.set_cooldown("local_ollama", "model-a", duration=100.0)
    assert router.is_on_cooldown("local_ollama", "model-a") is True

    # Resolving candidates now filters out model-a
    updated_candidates = router.resolve_candidates("model-test")
    assert len(updated_candidates) == 1
    assert updated_candidates[0].id == "model-b"


@pytest.mark.asyncio
async def test_streaming_first_token_failover(test_registry):
    """AC-8: Verify that early 503/error on stream pre-buffer triggers cascade to secondary candidate."""
    test_models = [
        DiscoveredModel(
            id="stream-model-1",
            canonical_name="stream-test-model",
            provider_id="local_ollama",
            context_window=8192,
            is_free=True,
        ),
        DiscoveredModel(
            id="stream-model-2",
            canonical_name="stream-test-model",
            provider_id="local_ollama",
            context_window=8192,
            is_free=True,
        ),
    ]
    await test_registry.register_models(test_models)

    call_counts = {"c1": 0, "c2": 0}

    def mock_stream_handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode("utf-8")
        if "stream-model-1" in body:
            call_counts["c1"] += 1
            # Candidate 1 fails on stream initiation with 503
            return httpx.Response(503, json={"error": "Service failureed"})
        elif "stream-model-2" in body:
            call_counts["c2"] += 1
            sse = (
                b'data: {"id":"c2-stream","choices":[{"delta":{"content":"Chunk 1"}}],"model":"stream-model-2"}\n\n'
                b'data: {"id":"c2-stream","choices":[{"delta":{"content":" Chunk 2"}}],"model":"stream-model-2"}\n\n'
                b'data: [DONE]\n\n'
            )
            return httpx.Response(200, content=sse, headers={"Content-Type": "text/event-stream"})
        return httpx.Response(404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_stream_handler))
    router = CascadeRouter(
        registry=test_registry,
        provider_client=OpenAIProviderClient(http_client=mock_client),
    )

    stream_gen = await router.route_stream_completion(
        requested_model="stream-test-model",
        payload={"messages": [{"role": "user", "content": "Stream me"}]},
    )

    # Collect yielded chunks
    collected = []
    async for chunk in stream_gen:
        collected.append(chunk)

    full_text = "".join(collected)
    assert "Chunk 1" in full_text
    assert "Chunk 2" in full_text
    assert "data: [DONE]" in full_text

    # Both were called (Candidate 1 failed, Candidate 2 streamed)
    assert call_counts["c1"] == 1
    assert call_counts["c2"] == 1
    # Candidate 1 is placed on cooldown
    assert router.is_on_cooldown("local_ollama", "stream-model-1") is True


@pytest.mark.asyncio
async def test_exhausted_pool_returns_503(test_registry):
    """AC-11: Verify that when all pool candidates fail, router raises 503 error."""
    test_models = [
        DiscoveredModel(
            id="failing-model",
            canonical_name="failing-model",
            provider_id="local_ollama",
            context_window=4096,
            is_free=True,
        )
    ]
    await test_registry.register_models(test_models)

    def mock_failing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal error")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_failing_handler))
    router = CascadeRouter(
        registry=test_registry,
        provider_client=OpenAIProviderClient(http_client=mock_client),
    )

    from backend.app.core.adapters.openai_client import UpstreamProviderError
    with pytest.raises(UpstreamProviderError) as exc_info:
        await router.route_completion(
            requested_model="failing-model",
            payload={"messages": [{"role": "user", "content": "Hello"}]},
        )
    assert exc_info.value.status_code == 503
    assert "All free pool candidates exhausted" in str(exc_info.value)


@pytest.mark.asyncio
async def test_tier2_fallback_when_tier1_exhausted(test_registry):
    """Verify that when Tier 1 candidate fails, Tier 2 alternative model is used with model name masking."""
    test_models = [
        DiscoveredModel(
            id="primary-tier1-id",
            canonical_name="requested/target-model",
            provider_id="local_ollama",
            context_window=8192,
            is_free=True,
        ),
        DiscoveredModel(
            id="backup-tier2-id",
            canonical_name="backup/alternative-model",
            provider_id="local_ollama",
            context_window=8192,
            is_free=True,
        ),
    ]
    await test_registry.register_models(test_models)

    call_log = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode("utf-8")
        if "primary-tier1-id" in body:
            call_log.append("tier1")
            return httpx.Response(503, json={"error": "Service failure exceeded on Tier 1"})
        elif "backup-tier2-id" in body:
            call_log.append("tier2")
            return httpx.Response(200, json={
                "id": "chatcmpl-tier2-success",
                "object": "chat.completion",
                "created": 1729600000,
                "model": "backup-tier2-id",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "Served by Tier 2 backup!"}}],
            })
        return httpx.Response(404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    router = CascadeRouter(
        registry=test_registry,
        provider_client=OpenAIProviderClient(http_client=mock_client),
    )

    response = await router.route_completion(
        requested_model="requested/target-model",
        payload={"messages": [{"role": "user", "content": "Hello"}]},
    )

    assert call_log == ["tier1", "tier2"]
    assert response["choices"][0]["message"]["content"] == "Served by Tier 2 backup!"
    # Even though served by Tier 2 backup, client sees their requested model name (canonical masking)
    assert response["model"] == "requested/target-model"


@pytest.mark.asyncio
async def test_streaming_role_first_failover(test_registry):
    """Verify that an in-stream 503 occurring after a role-only chunk triggers failover to Candidate 2."""
    test_models = [
        DiscoveredModel(
            id="role-first-failing",
            canonical_name="role-stream-model",
            provider_id="local_ollama",
            context_window=8192,
            is_free=True,
        ),
        DiscoveredModel(
            id="role-second-working",
            canonical_name="role-stream-model",
            provider_id="local_ollama",
            context_window=8192,
            is_free=True,
        ),
    ]
    await test_registry.register_models(test_models)

    call_counts = {"c1": 0, "c2": 0}

    def mock_stream_handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode("utf-8")
        if "role-first-failing" in body:
            call_counts["c1"] += 1
            # Emits role chunk first, then immediately emits an in-stream 503 error!
            sse_failing = (
                b'data: {"id":"c1","choices":[{"delta":{"role":"assistant"}}],"model":"role-first-failing"}\n\n'
                b'data: {"error":{"message":"Service failure exceeded","code":503}}\n\n'
            )
            return httpx.Response(200, content=sse_failing, headers={"Content-Type": "text/event-stream"})
        elif "role-second-working" in body:
            call_counts["c2"] += 1
            sse_working = (
                b'data: {"id":"c2","choices":[{"delta":{"role":"assistant"}}],"model":"role-second-working"}\n\n'
                b'data: {"id":"c2","choices":[{"delta":{"content":"Recovered stream!"}}],"model":"role-second-working"}\n\n'
                b'data: [DONE]\n\n'
            )
            return httpx.Response(200, content=sse_working, headers={"Content-Type": "text/event-stream"})
        return httpx.Response(404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_stream_handler))
    router = CascadeRouter(
        registry=test_registry,
        provider_client=OpenAIProviderClient(http_client=mock_client),
    )

    stream_gen = await router.route_stream_completion(
        requested_model="role-stream-model",
        payload={"messages": [{"role": "user", "content": "Hi"}]},
    )

    chunks = []
    async for chunk in stream_gen:
        chunks.append(chunk)

    full_text = "".join(chunks)
    # Stream cleanly failed over to candidate 2 without client receiving error!
    assert "Recovered stream!" in full_text
    assert call_counts["c1"] == 1
    assert call_counts["c2"] == 1
    assert router.is_on_cooldown("local_ollama", "role-first-failing") is True


@pytest.mark.asyncio
async def test_max_failover_attempts_limit(test_registry):
    """Verify that router tries at most MAX_FAILOVER_ATTEMPTS (3) candidates before returning 503."""
    test_models = [
        DiscoveredModel(
            id=f"failing-cand-{i}",
            canonical_name="multi-fail-model",
            provider_id="local_ollama",
            context_window=4096,
            is_free=True,
        )
        for i in range(5)  # 5 failing candidates
    ]
    await test_registry.register_models(test_models)

    call_counts = {"attempts": 0}

    def mock_all_fail(request: httpx.Request) -> httpx.Response:
        call_counts["attempts"] += 1
        return httpx.Response(500, text="Downstream error")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_all_fail))
    router = CascadeRouter(
        registry=test_registry,
        provider_client=OpenAIProviderClient(http_client=mock_client),
    )

    from backend.app.core.adapters.openai_client import UpstreamProviderError
    with pytest.raises(UpstreamProviderError) as exc_info:
        await router.route_completion(
            requested_model="multi-fail-model",
            payload={"messages": [{"role": "user", "content": "Hi"}]},
        )

    # Exactly 3 attempts were made before stopping
    assert call_counts["attempts"] == 3
    assert exc_info.value.status_code == 503
