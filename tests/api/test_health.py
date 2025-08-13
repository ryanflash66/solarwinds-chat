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
    
    # Check components exist
    components = data["components"]
    expected_components = [
        "vector_store",
        "embedding_service", 
        "llm_service",
        "sync_service",
        "solarwinds_api"
    ]
    
    for component in expected_components:
        assert component in components
        assert "status" in components[component]
        assert "message" in components[component]


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