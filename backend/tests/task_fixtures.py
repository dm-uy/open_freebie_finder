"""Synthetic task sources; no fixture is a production free-access certificate."""
from backend.app.config import Settings
from backend.app.core.providers.models import ProviderManifest
from backend.app.core.providers.registry import ProviderRegistry


def registry(monkeypatch, master=None):
    monkeypatch.setenv("TASK_FIXTURE_KEY", "synthetic-task-credential")
    manifest = ProviderManifest(id="openrouter", name="Fixture", base_url="https://openrouter.ai/api/v1",
        models_endpoint="https://openrouter.ai/api/v1/models", eligibility_profile="openrouter_zero_price",
        auth={"type": "bearer", "api_key_env": "TASK_FIXTURE_KEY"})
    return ProviderRegistry(settings=Settings(_env_file=None, proxy_master_key=master), manifests=[manifest])


def source(task, raw="fixture-model", prices=None):
    return {"data": [{"id": raw, "architecture": {"input_modalities": ["text"], "output_modalities": [task]},
        "pricing": prices if prices is not None else {"prompt": "0", "completion": "0", "request": "0"}}]}


def publish(registry, task="embeddings", raw="fixture-model"):
    registry.tasks.publish(task, source(task, raw), registry.tasks.binding(task))
    return registry.tasks.get(task, "openrouter::" + raw)
