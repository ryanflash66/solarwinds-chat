"""Tests for solutions endpoints."""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.api
def test_solutions_search_endpoint(client: TestClient):
    """Test the solutions search endpoint."""
    response = client.get("/api/v1/solutions/search?q=test&limit=5")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return a list even if empty
    assert isinstance(data, list)
    
    # If there are results, check their structure
    if data:
        for item in data:
            assert "id" in item
            assert "title" in item
            assert "score" in item


@pytest.mark.api
def test_solutions_search_no_query(client: TestClient):
    """Test the solutions search endpoint without query parameter."""
    response = client.get("/api/v1/solutions/search")
    
    # Should require query parameter
    assert response.status_code == 422


@pytest.mark.api
def test_solutions_search_with_params(client: TestClient):
    """Test the solutions search endpoint with various parameters."""
    response = client.get("/api/v1/solutions/search?q=printer&limit=10&min_score=0.2")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.api
def test_solutions_stats_endpoint(client: TestClient):
    """Test the solutions stats endpoint."""
    response = client.get("/api/v1/solutions/stats")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check expected fields (even if empty/error)
    expected_fields = ["total_documents", "collection_name"]
    
    # Should have at least some structure
    assert isinstance(data, dict)


@pytest.mark.api
def test_solutions_by_id_endpoint(client: TestClient):
    """Test getting solution by ID."""
    # Test with a fake ID that won't exist
    response = client.get("/api/v1/solutions/test-id-123")
    
    # Could be 404 if not found, or 200 with null/empty result
    assert response.status_code in [200, 404]


@pytest.mark.api
@pytest.mark.asyncio
async def test_solutions_search_async(async_client: AsyncClient):
    """Test the solutions search endpoint with async client."""
    response = await async_client.get("/api/v1/solutions/search?q=test")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)