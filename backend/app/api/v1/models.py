"""OpenAI-compatible /v1/models endpoint."""
import time
from typing import Any
from fastapi import APIRouter, Request
from backend.app.core.providers.registry import get_registry
from backend.app.core.tasks.catalog import TASKS
from backend.app.core.tasks.http import error, query_task, request_id

router = APIRouter()


@router.get("/models", tags=["OpenAI Compatible"])
async def list_models(request: Request) -> dict[str, Any]:
    """Return OpenAI-compatible list of available models from in-memory cache (< 2ms, zero I/O)."""
    registry = getattr(request.app.state, "provider_registry", None) or get_registry()
    task = query_task(request, {"chat", *TASKS}, "chat")
    if task is None:
        return error(400, "unsupported_free_request", request_id(request, registry))
    if task != "chat":
        return {"object": "list", "data": [{"id": row.public_id, "object": "model",
            "created": int(time.time()), "owned_by": "openrouter"}
            for row in registry.tasks.eligible_rows(task)]}
    discovered = registry.get_eligible_models()

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
