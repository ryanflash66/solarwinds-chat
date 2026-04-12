"""Tests for health check endpoints."""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.api
def test_health_endpoint(client: TestClient):
    """Test the health check endpoint returns correct status."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()

    # Check basic structure
    assert "status" in data
    assert "timestamp" in data
    assert "components" in data

    # The base components are always present
    components = data["components"]
    for component in ["api", "config", "logging"]:
        assert component in components
        assert "status" in components[component]
        assert "message" in components[component]

    # Verify that each component entry has the expected shape
    for name, info in components.items():
        assert isinstance(info, dict), f"Component '{name}' should be a dict"
        assert "status" in info, f"Component '{name}' missing 'status' key"


@pytest.mark.api
@pytest.mark.asyncio
async def test_health_endpoint_async(async_client: AsyncClient):
    """Test the health check endpoint with async client."""
    response = await async_client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert isinstance(data["components"], dict)


@pytest.mark.api
def test_root_endpoint(client: TestClient):
    """Test the root endpoint returns correct information."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert "message" in data
    assert "version" in data
    assert "docs" in data
    assert "SolarWinds" in data["message"]
