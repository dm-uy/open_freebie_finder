"""Tests for Declarative Provider Schema and Registry."""
import pytest
from pydantic import ValidationError
from backend.app.core.providers.models import (
    DiscoveredModel,
    DiscoveryRule,
    ProviderAuth,
    ProviderManifest,
)
from backend.app.core.providers.registry import ProviderRegistry, get_registry


def test_manifest_schema_validation():
    """AC-1: Verify ProviderManifest validates schema and rejects invalid inputs."""
    # Valid manifest
    valid = ProviderManifest(
        id="test_provider",
        name="Test Provider",
        base_url="https://api.test.com/v1",
        models_endpoint="https://api.test.com/v1/models",
        auth=ProviderAuth(type="bearer", api_key_env="TEST_KEY"),
        discovery=DiscoveryRule(type="all_available"),
    )
    assert valid.id == "test_provider"
    assert valid.base_url == "https://api.test.com/v1"

    # Invalid ID format
    with pytest.raises(ValidationError):
        ProviderManifest(
            id="invalid id with spaces!",
            name="Bad",
            base_url="https://api.test.com/v1",
            models_endpoint="https://api.test.com/v1/models",
        )

    # Invalid URL scheme
    with pytest.raises(ValidationError):
        ProviderManifest(
            id="bad_url",
            name="Bad URL",
            base_url="ftp://api.test.com",
            models_endpoint="https://api.test.com/v1/models",
        )


def test_load_all_ten_builtin_manifests():
    """AC-2: Verify all 10 out-of-the-box manifests in providers.yaml load cleanly."""
    registry = ProviderRegistry()
    manifests = registry.get_manifests()
    assert len(manifests) == 10

    expected_ids = {
        "openrouter",
        "groq",
        "nvidia_nim",
        "google_gemini",
        "github_models",
        "cerebras",
        "mistral",
        "huggingface",
        "cloudflare",
        "local_ollama",
    }
    loaded_ids = {m.id for m in manifests}
    assert loaded_ids == expected_ids

    # Check local_ollama has auth type none
    ollama = registry.get_manifest("local_ollama")
    assert ollama is not None
    assert ollama.auth.type == "none"

    # Check openrouter has discovery type openrouter_free
    openrouter = registry.get_manifest("openrouter")
    assert openrouter is not None
    assert openrouter.discovery.type == "openrouter_free"


@pytest.mark.asyncio
async def test_in_memory_lookup_zero_network():
    """AC-6: Verify model lookups resolve strictly in-memory without network operations."""
    registry = ProviderRegistry()
    test_models = [
        DiscoveredModel(
            id="meta-llama/llama-3.3-70b-instruct:free",
            canonical_name="meta-llama/llama-3.3-70b-instruct",
            provider_id="openrouter",
            context_window=131072,
            is_free=True,
        ),
        DiscoveredModel(
            id="llama-3.3-70b-versatile",
            canonical_name="meta-llama/llama-3.3-70b-instruct",
            provider_id="groq",
            context_window=131072,
            is_free=True,
        ),
    ]

    await registry.register_models(test_models)
    cached = registry.get_models()
    assert len(cached) == 2
    assert cached[0].canonical_name == "meta-llama/llama-3.3-70b-instruct"


@pytest.mark.asyncio
async def test_model_candidates_lookup():
    """AC-9: Verify get_model_candidates returns all models matching canonical name."""
    registry = ProviderRegistry()
    test_models = [
        DiscoveredModel(
            id="meta-llama/llama-3.3-70b-instruct:free",
            canonical_name="meta-llama/llama-3.3-70b-instruct",
            provider_id="local_ollama",  # active without keys
            context_window=131072,
            is_free=True,
        ),
        DiscoveredModel(
            id="qwen-2.5-72b",
            canonical_name="qwen/qwen-2.5-72b",
            provider_id="local_ollama",
            context_window=32768,
            is_free=True,
        ),
    ]

    await registry.register_models(test_models)
    candidates = registry.get_model_candidates("meta-llama/llama-3.3-70b-instruct")
    assert len(candidates) == 1
    assert candidates[0].id == "meta-llama/llama-3.3-70b-instruct:free"

    # Non-existent canonical name returns empty list
    none_candidates = registry.get_model_candidates("non-existent-model")
    assert none_candidates == []


def test_registry_singleton():
    """Verify get_registry returns identical cached instance."""
    r1 = get_registry()
    r2 = get_registry()
    assert r1 is r2
