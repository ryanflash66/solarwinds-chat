"""Tests for graceful error handling across API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.services.indexing_service import indexing_service
from app.services.llm import llm_service


@pytest.mark.api
class TestChatErrorHandling:
    """Chat endpoint should degrade gracefully when services fail."""

    def test_chat_returns_graceful_response_when_search_fails(self, client: TestClient):
        """When search_solutions raises, chat should still return 200 with an error message."""
        with patch.object(
            indexing_service,
            "search_solutions",
            new_callable=AsyncMock,
            side_effect=Exception("vector store unavailable"),
        ):
            response = client.post("/api/v1/chat", json={"query": "test query"})
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            # The answer should indicate an error occurred
            assert len(data["answer"]) > 0

    def test_chat_returns_graceful_response_when_llm_fails(self, client: TestClient):
        """When LLM generation raises, chat should still return 200 with a fallback."""
        with patch.object(
            llm_service,
            "generate_response",
            new_callable=AsyncMock,
            side_effect=Exception("LLM service down"),
        ):
            response = client.post("/api/v1/chat", json={"query": "test query"})
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert len(data["answer"]) > 0


@pytest.mark.api
class TestRouteErrors:
    """Basic HTTP error scenarios."""

    def test_unknown_route_returns_404(self, client: TestClient):
        """Requesting a non-existent route should return 404."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_chat_with_invalid_json_returns_422(self, client: TestClient):
        """POST to chat with missing required fields should return 422."""
        response = client.post("/api/v1/chat", json={})
        assert response.status_code == 422

    def test_chat_with_empty_body_returns_422(self, client: TestClient):
        """POST to chat with no body at all should return 422."""
        response = client.post(
            "/api/v1/chat",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422
