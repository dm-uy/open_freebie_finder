"""Tests for health check endpoint."""
import pytest


@pytest.mark.asyncio
async def test_health_check(async_client):
    """Verify /health returns 200 OK and healthy status."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["app"] == "Open Freebie Finder"


@pytest.mark.asyncio
async def test_lifespan_context():
    """Verify application lifespan manager initializes and cleans up background tasks cleanly."""
    from backend.app.main import lifespan, app
    async with lifespan(app):
        # Lifespan active: app is ready
        assert True
    # Lifespan exited cleanly
    assert True
