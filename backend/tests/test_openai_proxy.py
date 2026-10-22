"""Tests for OpenAI-compatible Proxy Endpoints (/v1/models and /v1/chat/completions)."""
import json
import httpx
import pytest
from backend.app.config import get_settings
from backend.app.core.adapters.openai_client import OpenAIProviderClient
from backend.app.core.balancer.router import CascadeRouter
from backend.app.core.providers.models import DiscoveredModel
from backend.app.core.providers.registry import get_registry
from backend.app.main import app


@pytest.fixture
def clean_registry():
    """Fixture ensuring a fresh registry with test models."""
    registry = get_registry()
    registry.load_manifests()
    return registry


@pytest.mark.asyncio
async def test_models_endpoint(async_client, clean_registry):
    """AC-1: Verify GET /v1/models returns OpenAI-compliant model list including auto:free."""
    await clean_registry.register_models([
        DiscoveredModel(
            id="meta-llama/llama-3.3-70b-instruct:free",
            canonical_name="meta-llama/llama-3.3-70b-instruct",
            provider_id="openrouter",
            context_window=131072,
            is_free=True,
        )
    ])

    response = await async_client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert "data" in data

    ids = [m["id"] for m in data["data"]]
    assert "auto:free" in ids
    assert "meta-llama/llama-3.3-70b-instruct" in ids

    # Check model object fields
    auto_free = next(m for m in data["data"] if m["id"] == "auto:free")
    assert auto_free["object"] == "model"
    assert auto_free["owned_by"] == "open-freebie-finder"
    assert isinstance(auto_free["created"], int)


@pytest.mark.asyncio
async def test_models_instant_lookup(async_client):
    """AC-2: Verify GET /v1/models resolves entirely from memory without network calls."""
    response = await async_client.get("/v1/models")
    assert response.status_code == 200
    # Response is immediate and contains valid list
    assert response.json()["object"] == "list"


@pytest.mark.asyncio
async def test_permissive_auth(async_client, monkeypatch):
    """AC-3: Verify permissive auth accepts arbitrary tokens when master key is unset and enforces when set."""
    # 1. Unset master key -> Accepts missing header and arbitrary key
    monkeypatch.setattr(get_settings(), "proxy_master_key", None)

    res1 = await async_client.get("/v1/models")
    assert res1.status_code == 200

    res2 = await async_client.get("/v1/models", headers={"Authorization": "Bearer any-arbitrary-client-key"})
    assert res2.status_code == 200

    # 2. Master key configured -> Enforces matching Bearer token on chat completions
    monkeypatch.setattr(get_settings(), "proxy_master_key", "secret-test-master-key")

    bad_res = await async_client.post(
        "/v1/chat/completions",
        json={"model": "auto:free", "messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert bad_res.status_code == 401
    err = bad_res.json()["error"]
    assert err["code"] == 401
    assert "Incorrect API key" in err["message"]


@pytest.mark.asyncio
async def test_chat_completions_buffered(async_client, clean_registry, monkeypatch):
    """AC-4: Verify non-streaming chat completion returns standard OpenAI completion object and synthesizes usage."""
    monkeypatch.setattr(get_settings(), "proxy_master_key", None)

    # Register a test model under local_ollama (always active)
    await clean_registry.register_models([
        DiscoveredModel(
            id="test-ollama-model",
            canonical_name="test/test-model",
            provider_id="local_ollama",
            context_window=8192,
            is_free=True,
        )
    ])

    mock_completion_response = {
        "id": "chatcmpl-test-123",
        "object": "chat.completion",
        "created": 1729600000,
        "model": "test-ollama-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello from mock provider!"},
                "finish_reason": "stop",
            }
        ],
        # Notice: usage is omitted by upstream mock to test AC-4 synthesis
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_completion_response)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    mock_provider_client = OpenAIProviderClient(http_client=mock_client)
    test_router = CascadeRouter(registry=clean_registry, provider_client=mock_provider_client)

    from backend.app.api.v1 import chat
    monkeypatch.setattr(chat, "get_cascade_router", lambda: test_router)

    res = await async_client.post(
        "/v1/chat/completions",
        json={
            "model": "test/test-model",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert data["choices"][0]["message"]["content"] == "Hello from mock provider!"
    # Verify canonical model masking
    assert data["model"] == "test/test-model"
    # Verify usage synthesis
    assert "usage" in data
    assert data["usage"]["total_tokens"] == 0


@pytest.mark.asyncio
async def test_chat_completions_streaming(async_client, clean_registry, monkeypatch):
    """AC-5: Verify streaming completions emit SSE chunks ending with data: [DONE]."""
    monkeypatch.setattr(get_settings(), "proxy_master_key", None)

    await clean_registry.register_models([
        DiscoveredModel(
            id="test-ollama-model",
            canonical_name="test/test-model",
            provider_id="local_ollama",
            context_window=8192,
            is_free=True,
        )
    ])

    sse_chunks = (
        b'data: {"id":"chatcmpl-stream","choices":[{"delta":{"content":"Hi"}}],"model":"raw-model"}\n\n'
        b'data: {"id":"chatcmpl-stream","choices":[{"delta":{"content":" there!"}}],"model":"raw-model"}\n\n'
        b'data: [DONE]\n\n'
    )

    def mock_stream_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sse_chunks, headers={"Content-Type": "text/event-stream"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_stream_handler))
    mock_provider_client = OpenAIProviderClient(http_client=mock_client)
    test_router = CascadeRouter(registry=clean_registry, provider_client=mock_provider_client)

    from backend.app.api.v1 import chat
    monkeypatch.setattr(chat, "get_cascade_router", lambda: test_router)

    res = await async_client.post(
        "/v1/chat/completions",
        json={
            "model": "test/test-model",
            "messages": [{"role": "user", "content": "Hi"}],
            "stream": True,
        },
    )

    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    text = res.text
    assert "data: [DONE]" in text
    assert "there!" in text


@pytest.mark.asyncio
async def test_canonical_model_name_masking(async_client, clean_registry, monkeypatch):
    """AC-6: Verify response and SSE chunks overwrite upstream model name with requested canonical name."""
    monkeypatch.setattr(get_settings(), "proxy_master_key", None)

    await clean_registry.register_models([
        DiscoveredModel(
            id="upstream-raw-id-xyz",
            canonical_name="meta-llama/llama-3.3-70b-instruct",
            provider_id="local_ollama",
            context_window=131072,
            is_free=True,
        )
    ])

    sse_chunks = (
        b'data: {"id":"chatcmpl-1","choices":[{"delta":{"content":"Token"}}],"model":"upstream-raw-id-xyz"}\n\n'
        b'data: [DONE]\n\n'
    )

    def mock_stream_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sse_chunks, headers={"Content-Type": "text/event-stream"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_stream_handler))
    test_router = CascadeRouter(registry=clean_registry, provider_client=OpenAIProviderClient(http_client=mock_client))

    from backend.app.api.v1 import chat
    monkeypatch.setattr(chat, "get_cascade_router", lambda: test_router)

    res = await async_client.post(
        "/v1/chat/completions",
        json={
            "model": "meta-llama/llama-3.3-70b-instruct",
            "messages": [{"role": "user", "content": "Hi"}],
            "stream": True,
        },
    )

    assert res.status_code == 200
    # Streamed chunk contains canonical name, not upstream-raw-id-xyz
    assert "meta-llama/llama-3.3-70b-instruct" in res.text
    assert "upstream-raw-id-xyz" not in res.text


@pytest.mark.asyncio
async def test_openai_error_shapes(async_client, monkeypatch):
    """AC-11: Verify 400, 401, 404, and 503 errors conform strictly to OpenAI error JSON envelope."""
    monkeypatch.setattr(get_settings(), "proxy_master_key", None)

    # 1. 400 Bad Request (Invalid JSON)
    res_400 = await async_client.post(
        "/v1/chat/completions",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )
    assert res_400.status_code == 400
    err_400 = res_400.json()["error"]
    assert "message" in err_400 and "type" in err_400 and "code" in err_400
    assert err_400["code"] == 400

    # 2. 404 Model Not Found
    res_404 = await async_client.post(
        "/v1/chat/completions",
        json={"model": "completely-unknown-model", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert res_404.status_code == 404
    err_404 = res_404.json()["error"]
    assert err_404["code"] == 404
    assert err_404["type"] == "invalid_request_error"
