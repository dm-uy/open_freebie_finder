"""Main FastAPI entrypoint for Open Freebie Finder."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for background services and resource pools."""
    # Startup actions
    yield
    # Shutdown actions


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
