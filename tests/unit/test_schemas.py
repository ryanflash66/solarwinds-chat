"""Tests for Pydantic schemas and models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.schemas import (
    ChatRequest, 
    ChatResponse, 
    SourceDoc, 
    SolutionRecord
)


@pytest.mark.unit
def test_chat_request_valid():
    """Test ChatRequest with valid data."""
    request = ChatRequest(query="How do I fix printer issues?")
    
    assert request.query == "How do I fix printer issues?"


@pytest.mark.unit
def test_chat_request_empty_query():
    """Test ChatRequest with empty query should fail validation."""
    with pytest.raises(ValidationError):
        ChatRequest(query="")


@pytest.mark.unit
def test_chat_request_whitespace_query():
    """Test ChatRequest with whitespace-only query should fail validation."""
    with pytest.raises(ValidationError):
        ChatRequest(query="   ")


@pytest.mark.unit
def test_chat_response_valid():
    """Test ChatResponse with valid data."""
    sources = [
        SourceDoc(
            id="test-1",
            title="Test Solution",
            score=0.85,
            category="Hardware"
        )
    ]
    
    response = ChatResponse(
        answer="Here's how to fix it...",
        sources=sources,
        query_id="test-query-123",
        response_time_ms=500
    )
    
    assert response.answer == "Here's how to fix it..."
    assert len(response.sources) == 1
    assert response.sources[0].title == "Test Solution"
    assert response.response_time_ms == 500


@pytest.mark.unit
def test_source_doc_valid():
    """Test SourceDoc with valid data."""
    doc = SourceDoc(
        id="solution-123",
        title="Printer Configuration Guide",
        score=0.92,
        category="Hardware",
        url="https://example.com/solution/123"
    )
    
    assert doc.id == "solution-123"
    assert doc.title == "Printer Configuration Guide"
    assert doc.score == 0.92
    assert doc.category == "Hardware"
    assert doc.url == "https://example.com/solution/123"


@pytest.mark.unit
def test_source_doc_optional_fields():
    """Test SourceDoc with only required fields."""
    doc = SourceDoc(
        id="solution-456",
        title="Basic Solution",
        score=0.7
    )
    
    assert doc.id == "solution-456"
    assert doc.title == "Basic Solution"
    assert doc.score == 0.7
    assert doc.category is None
    assert doc.url is None


@pytest.mark.unit
def test_solution_record_valid():
    """Test SolutionRecord with valid data."""
    now = datetime.utcnow()
    
    solution = SolutionRecord(
        id="sol-789",
        title="Network Troubleshooting",
        category="Network",
        content="This is the solution content...",
        updated_at=now,
        tags=["network", "troubleshooting"],
        url="https://kb.example.com/network/789"
    )
    
    assert solution.id == "sol-789"
    assert solution.title == "Network Troubleshooting"
    assert solution.category == "Network"
    assert solution.updated_at == now
    assert "network" in solution.tags
    assert len(solution.tags) == 2


@pytest.mark.unit
def test_solution_record_minimal():
    """Test SolutionRecord with minimal required fields."""
    solution = SolutionRecord(
        id="sol-minimal",
        title="Minimal Solution",
        category="General",
        content="Basic content"
    )
    
    assert solution.id == "sol-minimal"
    assert solution.title == "Minimal Solution"
    assert solution.category == "General"
    assert solution.content == "Basic content"
    assert isinstance(solution.updated_at, datetime)
    assert solution.tags == []
    assert solution.url is None