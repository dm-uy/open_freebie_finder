"""Main FastAPI entrypoint for Open Freebie Finder."""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.admin import admin_router
from backend.app.api.v1 import v1_router
from backend.app.config import get_settings
from backend.app.core.discovery.orchestrator import DiscoveryOrchestrator
from backend.app.core.providers.registry import get_registry

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for background services and resource pools."""
    registry = getattr(app.state, "provider_registry", None) or get_registry()
    discovery = DiscoveryOrchestrator(registry)
    app.state.discovery = discovery
    stop_event = asyncio.Event()
    worker = asyncio.create_task(discovery.run(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)


def create_app(provider_registry=None) -> FastAPI:
    """FastAPI application factory."""
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Zero-cost LLM inference proxy and smart load balancer powered by free-tier models.",
        lifespan=lifespan,
    )

    if provider_registry is not None:
        application.state.provider_registry = provider_registry

    # Enable CORS for frontend clients
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount OpenAI-compatible v1 endpoints
    application.include_router(v1_router, prefix="/v1")

    # Mount Admin API endpoints
    application.include_router(admin_router, prefix="/api/admin")

    @application.get("/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        """Health check endpoint confirming proxy server availability."""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
        }

    return application


app = create_app()
