"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request schema."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User query for the chatbot",
        example="How do I reset the printer spooler service?"
    )


class SourceDoc(BaseModel):
    """Source document reference schema."""
    
    id: str = Field(..., description="Solution document ID")
    title: str = Field(..., description="Solution title") 
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    category: Optional[str] = Field(None, description="Solution category")
    url: Optional[str] = Field(None, description="Link to original solution")


class ChatResponse(BaseModel):
    """Chat response schema."""
    
    answer: str = Field(..., description="Generated answer from the chatbot")
    sources: List[SourceDoc] = Field(
        default_factory=list,
        description="Relevant source documents used to generate the answer"
    )
    query_id: Optional[str] = Field(None, description="Unique query identifier for tracking")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")


class SolutionRecord(BaseModel):
    """Solution record schema for vector store metadata."""
    
    id: str = Field(..., description="Unique solution identifier")
    title: str = Field(..., description="Solution title")
    category: str = Field(..., description="Solution category")
    content: str = Field(..., description="Solution content/body")
    updated_at: datetime = Field(..., description="Last updated timestamp")
    tags: List[str] = Field(default_factory=list, description="Solution tags")
    url: Optional[str] = Field(None, description="Original solution URL")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SyncStatus(BaseModel):
    """Sync status schema."""
    
    last_sync: Optional[datetime] = Field(None, description="Last successful sync timestamp")
    next_sync: Optional[datetime] = Field(None, description="Next scheduled sync timestamp")
    total_solutions: int = Field(0, description="Total number of solutions in vector store")
    sync_in_progress: bool = Field(False, description="Whether sync is currently running")
    last_error: Optional[str] = Field(None, description="Last sync error message")


class ErrorResponse(BaseModel):
    """Error response schema."""
    
    error: str = Field(..., description="Error message")
    details: dict = Field(default_factory=dict, description="Additional error details")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")