"""Admin API Package."""
from fastapi import APIRouter
from backend.app.api.admin.telemetry import router as telemetry_router

admin_router = APIRouter()
admin_router.include_router(telemetry_router)

__all__ = ["admin_router"]
