"""Admin API Package."""
from fastapi import APIRouter
from backend.app.api.admin.telemetry import router as telemetry_router
from backend.app.api.admin.providers import router as providers_router
from backend.app.api.admin.models import router as models_router

admin_router = APIRouter()
admin_router.include_router(telemetry_router)
admin_router.include_router(providers_router)
admin_router.include_router(models_router)

__all__ = ["admin_router"]
