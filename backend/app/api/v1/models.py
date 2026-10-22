"""OpenAI-compatible /v1/models endpoint."""
import time
from typing import Any
from fastapi import APIRouter
from backend.app.core.providers.registry import get_registry

router = APIRouter()


@router.get("/models", tags=["OpenAI Compatible"])
async def list_models() -> dict[str, Any]:
    """Return OpenAI-compatible list of available models from in-memory cache (< 2ms, zero I/O)."""
    registry = get_registry()
    discovered = registry.get_models()

    now = int(time.time())
    model_entries: list[dict[str, Any]] = [
        {
            "id": "auto:free",
            "object": "model",
            "created": now,
            "owned_by": "open-freebie-finder",
        }
    ]

    # Deduplicate by canonical name and aggregate providers in owned_by
    canonical_providers: dict[str, set[str]] = {}
    for m in discovered:
        canonical_providers.setdefault(m.canonical_name, set()).add(m.provider_id)

    for canonical_name in sorted(canonical_providers.keys()):
        providers_str = ",".join(sorted(canonical_providers[canonical_name]))
        model_entries.append(
            {
                "id": canonical_name,
                "object": "model",
                "created": now,
                "owned_by": providers_str or "open-freebie-finder",
            }
        )

    return {
        "object": "list",
        "data": model_entries,
    }
