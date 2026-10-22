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
from backend.app.core.discovery.openrouter import OpenRouterDiscoveryService
from backend.app.core.providers.registry import get_registry

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for background services and resource pools."""
    # Startup actions: warm up model cache immediately and launch periodic crawler
    registry = get_registry()
    discovery_service = OpenRouterDiscoveryService(registry=registry)

    # Initial non-blocking startup discovery task
    initial_discovery_task = asyncio.create_task(discovery_service.discover_free_models())

    # Periodic discovery crawler task
    stop_event = asyncio.Event()

    async def periodic_discovery_worker() -> None:
        while not stop_event.is_set():
            try:
                # Wait for next interval or stop signal
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=float(settings.discovery_interval_seconds))
                    break  # Stop requested
                except asyncio.TimeoutError:
                    pass  # Interval elapsed, proceed to discover

                logger.info("Executing scheduled model discovery cycle...")
                await discovery_service.discover_free_models()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Periodic model discovery encountered an error: %s", str(exc))

    crawler_task = asyncio.create_task(periodic_discovery_worker())

    yield

    # Shutdown actions
    stop_event.set()
    initial_discovery_task.cancel()
    crawler_task.cancel()
    try:
        await asyncio.gather(initial_discovery_task, crawler_task, return_exceptions=True)
    except Exception:
        pass


def create_app() -> FastAPI:
    """FastAPI application factory."""
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Zero-cost LLM inference proxy and smart load balancer powered by free-tier models.",
        lifespan=lifespan,
    )

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
