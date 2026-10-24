"""Safe task inventories including explicit unsupported/free-evidence gaps."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from backend.app.core.providers.registry import get_registry
from backend.app.core.tasks.catalog import TASKS
from backend.app.core.tasks.http import authenticated, error, query_task, request_id
from backend.app.core.tasks.views import inventory

router = APIRouter()


@router.get("/models/catalog")
async def models_catalog(request: Request):
    registry = getattr(request.app.state, "provider_registry", None) or get_registry()
    rid = request_id(request, registry)
    if not authenticated(request, registry):
        return error(401, "authentication_error", rid)
    task = query_task(request, {"all", "chat", *TASKS}, "all")
    if task is None:
        return error(400, "unsupported_free_request", rid)
    return JSONResponse(inventory(registry, task), headers={"X-Request-ID": rid})
