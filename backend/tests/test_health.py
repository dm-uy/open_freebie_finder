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
