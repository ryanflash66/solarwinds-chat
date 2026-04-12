"""Test configuration and fixtures for the SolarWinds IT Solutions Chatbot."""

import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Ensure test mode
os.environ["DEBUG"] = "true"

from app.main import app
from app.core.config import settings
from app.services.indexing_service import indexing_service
from app.services.llm import llm_service
from app.services.sync_service import sync_service


@pytest.fixture(autouse=True, scope="session")
def mock_services():
    """Patch external service methods so tests run without Docker services."""
    patches = [
        # Indexing service
        patch.object(indexing_service, "initialize", new_callable=AsyncMock),
        patch.object(indexing_service, "cleanup", new_callable=AsyncMock),
        patch.object(
            indexing_service,
            "search_solutions",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch.object(
            indexing_service,
            "health_check",
            new_callable=AsyncMock,
            return_value={"healthy": True},
        ),
        # LLM service
        patch.object(llm_service, "initialize", new_callable=AsyncMock),
        patch.object(llm_service, "cleanup", new_callable=AsyncMock),
        patch.object(
            llm_service,
            "generate_response",
            new_callable=AsyncMock,
            return_value="Mock response",
        ),
        patch.object(
            llm_service,
            "health_check",
            new_callable=AsyncMock,
            return_value={"provider": "mock", "status": "healthy"},
        ),
        # Sync service
        patch.object(sync_service, "start", new_callable=AsyncMock),
        patch.object(sync_service, "stop", new_callable=AsyncMock),
        patch.object(
            sync_service,
            "get_sync_status",
            new_callable=AsyncMock,
            return_value={"service_running": False},
        ),
    ]

    started = [p.start() for p in patches]
    yield started
    for p in patches:
        p.stop()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def async_client():
    """Create an async test client for the FastAPI application."""
    async with AsyncClient(app=app, base_url="http://test") as async_test_client:
        yield async_test_client


@pytest.fixture
def test_settings():
    """Provide test-specific settings."""
    return {
        "debug": True,
        "log_level": "DEBUG",
        "embedding_provider": "local",
        "llm_provider": "openrouter",
    }


@pytest.fixture
def sample_solution_data():
    """Provide sample solution data for testing."""
    return {
        "id": "test-solution-001",
        "title": "Test Printer Solution",
        "category": "Hardware",
        "content": "This is a test solution for printer issues. Follow these steps to resolve common printer problems.",
        "tags": ["printer", "hardware", "troubleshooting"],
        "url": "https://solarwinds.example.com/solutions/test-001",
    }


@pytest.fixture
def sample_chat_request():
    """Provide sample chat request data for testing."""
    return {"query": "How do I fix printer spooler issues?"}


@pytest.fixture
def sample_embedding():
    """Provide sample embedding vector for testing."""
    return [0.1] * 384  # 384-dimensional vector for local embeddings
