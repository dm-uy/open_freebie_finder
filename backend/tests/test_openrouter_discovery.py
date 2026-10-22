"""Unit tests for OpenRouter Free Model Discovery Engine."""
import httpx
import pytest
from backend.app.core.discovery.openrouter import OpenRouterDiscoveryService
from backend.app.core.providers.models import DiscoveredModel
from backend.app.core.providers.registry import ProviderRegistry

MOCK_OPENROUTER_RESPONSE = {
    "data": [
        {
            "id": "meta-llama/llama-3.3-70b-instruct:free",
            "name": "Meta: Llama 3.3 70B Instruct (free)",
            "context_length": 131072,
            "pricing": {"prompt": "0", "completion": "0"},
            "description": "Free high performance 70B model",
        },
        {
            "id": "google/gemini-2.0-flash-exp:free",
            "name": "Google: Gemini 2.0 Flash (free)",
            "context_length": 1048576,
            "pricing": {"prompt": "0", "completion": "0"},
            "description": "Free multimodal Gemini experimental",
        },
        {
            "id": "openai/gpt-4o",
            "name": "OpenAI: GPT-4o",
            "context_length": 128000,
            "pricing": {"prompt": "0.0000025", "completion": "0.00001"},
            "description": "Paid commercial model",
        },
        {
            "id": "anthropic/claude-3.5-sonnet",
            "name": "Anthropic: Claude 3.5 Sonnet",
            "context_length": 200000,
            "pricing": {"prompt": "0.000003", "completion": "0.000015"},
            "description": "Paid commercial model",
        },
        {
            "id": "partial-free/half-cost-model",
            "name": "Partial Free Model",
            "context_length": 8192,
            "pricing": {"prompt": "0", "completion": "0.000001"},  # Non-zero completion
            "description": "Must not be included",
        },
        {
            "id": "unknown-context/model:free",
            "name": "Model with Missing Context",
            "context_length": None,  # Missing context length
            "pricing": {"prompt": "0", "completion": "0"},
        },
    ]
}


@pytest.mark.asyncio
async def test_filter_zero_cost_models():
    """AC-3: Verify discovery extracts ONLY models where prompt and completion costs are strictly zero."""
    registry = ProviderRegistry()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=MOCK_OPENROUTER_RESPONSE)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        service = OpenRouterDiscoveryService(registry=registry, http_client=client)
        models = await service.discover_free_models()

    # Out of 6 models, only 3 are 100% free (llama-3.3, gemini-2.0, unknown-context)
    assert len(models) == 3
    ids = {m.id for m in models}
    assert "meta-llama/llama-3.3-70b-instruct:free" in ids
    assert "google/gemini-2.0-flash-exp:free" in ids
    assert "unknown-context/model:free" in ids
    assert "openai/gpt-4o" not in ids
    assert "partial-free/half-cost-model" not in ids


@pytest.mark.asyncio
async def test_canonical_name_mapping():
    """AC-5: Verify :free suffixes are stripped to produce clean canonical names."""
    registry = ProviderRegistry()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=MOCK_OPENROUTER_RESPONSE)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        service = OpenRouterDiscoveryService(registry=registry, http_client=client)
        models = await service.discover_free_models()

    llama = next(m for m in models if m.id == "meta-llama/llama-3.3-70b-instruct:free")
    assert llama.canonical_name == "meta-llama/llama-3.3-70b-instruct"

    gemini = next(m for m in models if m.id == "google/gemini-2.0-flash-exp:free")
    assert gemini.canonical_name == "google/gemini-2.0-flash-exp"


@pytest.mark.asyncio
async def test_context_window_extraction():
    """AC-4: Verify context_window is extracted and missing values default safely to 4096."""
    registry = ProviderRegistry()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=MOCK_OPENROUTER_RESPONSE)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        service = OpenRouterDiscoveryService(registry=registry, http_client=client)
        models = await service.discover_free_models()

    llama = next(m for m in models if m.id == "meta-llama/llama-3.3-70b-instruct:free")
    assert llama.context_window == 131072

    unknown = next(m for m in models if m.id == "unknown-context/model:free")
    assert unknown.context_window == 4096


@pytest.mark.asyncio
async def test_resilience_on_errors():
    """AC-7: Verify discovery handles 429, 500, and network errors gracefully while preserving cache."""
    registry = ProviderRegistry()
    # Pre-populate registry with an existing model
    await registry.register_models([
        DiscoveredModel(
            id="cached/test-model:free",
            canonical_name="cached/test-model",
            provider_id="openrouter",
            context_window=8192,
            is_free=True,
        )
    ])

    # 1. Simulate 429 Too Many Requests
    def handler_429(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "Rate limit exceeded"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_429)) as client:
        service = OpenRouterDiscoveryService(registry=registry, http_client=client)
        models = await service.discover_free_models()
        assert models == []
        # Pre-existing cached model remains intact
        assert len(registry.get_models()) == 1

    # 2. Simulate 500 Internal Server Error
    def handler_500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_500)) as client:
        service = OpenRouterDiscoveryService(registry=registry, http_client=client)
        models = await service.discover_free_models()
        assert models == []
        assert len(registry.get_models()) == 1

    # 3. Simulate Connection Timeout
    def handler_timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connection timed out")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler_timeout)) as client:
        service = OpenRouterDiscoveryService(registry=registry, http_client=client)
        models = await service.discover_free_models()
        assert models == []
        assert len(registry.get_models()) == 1
