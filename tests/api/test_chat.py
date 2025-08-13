"""Tests for chat endpoints."""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.api
def test_chat_endpoint_basic(client: TestClient, sample_chat_request):
    """Test the chat endpoint with a basic request."""
    response = client.post("/api/v1/chat", json=sample_chat_request)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "answer" in data
    assert "sources" in data
    assert "query_id" in data
    assert "response_time_ms" in data
    
    # Check data types
    assert isinstance(data["answer"], str)
    assert isinstance(data["sources"], list)
    assert isinstance(data["response_time_ms"], int)
    assert len(data["answer"]) > 0


@pytest.mark.api
@pytest.mark.asyncio
async def test_chat_endpoint_async(async_client: AsyncClient, sample_chat_request):
    """Test the chat endpoint with async client."""
    response = await async_client.post("/api/v1/chat", json=sample_chat_request)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "answer" in data
    assert isinstance(data["sources"], list)


@pytest.mark.api
def test_chat_endpoint_empty_query(client: TestClient):
    """Test the chat endpoint with empty query."""
    response = client.post("/api/v1/chat", json={"query": ""})
    
    # Should still return 200 but with appropriate message
    assert response.status_code == 422  # Validation error for empty query


@pytest.mark.api
def test_chat_endpoint_invalid_json(client: TestClient):
    """Test the chat endpoint with invalid JSON."""
    response = client.post("/api/v1/chat", json={})
    
    assert response.status_code == 422  # Missing required field


@pytest.mark.api
def test_chat_endpoint_long_query(client: TestClient):
    """Test the chat endpoint with a very long query."""
    long_query = "How do I fix " + "very " * 100 + "complex printer issues?"
    
    response = client.post("/api/v1/chat", json={"query": long_query})
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data