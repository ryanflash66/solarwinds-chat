"""Chat endpoints with RAG implementation."""

import time
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse, SourceDoc
from app.services.indexing_service import indexing_service
from app.services.llm import llm_service
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


async def generate_rag_response(query: str, sources: list[SourceDoc]) -> str:
    """
    Generate a response using the RAG pattern with real LLM integration.
    
    Args:
        query: User query
        sources: Relevant source documents
        
    Returns:
        Generated response from LLM
    """
    try:
        # Use the LLM service to generate a response
        response = await llm_service.generate_response(query, sources)
        return response
    except Exception as e:
        logger.error(f"LLM generation failed: {str(e)}")
        # Fallback to template response if LLM fails
        return generate_fallback_response(query, sources)


def generate_fallback_response(query: str, sources: list[SourceDoc]) -> str:
    """
    Generate a fallback template response when LLM is unavailable.
    
    Args:
        query: User query
        sources: Relevant source documents
        
    Returns:
        Template-based response for IT staff
    """
    if not sources:
        return (
            "I couldn't find any specific solutions related to your query in our SolarWinds knowledge base. "
            "Please try rephrasing your question or escalate to a senior IT staff member for assistance. "
            "(Note: LLM service unavailable - using fallback response)"
        )
    
    # Create context from sources for IT staff
    context_parts = []
    for i, source in enumerate(sources, 1):
        context_parts.append(f"{i}. {source.title} (Relevance: {source.score:.2f})")
    
    context = "\n".join(context_parts)
    
    # Generate template response for IT staff
    response = f"""Based on the query "{query}", here are {len(sources)} relevant SolarWinds solution(s) to help you assist the user:

{context}

To resolve this issue:
1. Review the solutions listed above (ranked by relevance)
2. Follow the documented procedures in SolarWinds
3. If the issue persists, consider escalation to senior IT staff

(Note: LLM service unavailable - using fallback response. Full AI-powered guidance will be available once LLM service is configured.)"""
    
    return response


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint with RAG (Retrieval-Augmented Generation).
    
    This endpoint:
    1. Searches for relevant solutions using semantic similarity
    2. Generates a response based on the retrieved context
    3. Returns the response with source citations
    
    Args:
        request: Chat request with user query
        
    Returns:
        Generated response with source documents
    """
    start_time = time.time()
    query_id = str(uuid.uuid4())
    
    try:
        logger.info(f"Chat request received", extra={
            "query_id": query_id,
            "query": request.query[:100] + "..." if len(request.query) > 100 else request.query,
        })
        
        # Step 1: Retrieve relevant solutions using semantic search
        sources = await indexing_service.search_solutions(
            query=request.query,
            top_k=4,  # Get top 4 most relevant solutions
            min_score=0.1  # Minimum similarity threshold
        )
        
        logger.info(f"Retrieved {len(sources)} relevant sources", extra={
            "query_id": query_id,
            "source_count": len(sources),
        })
        
        # Step 2: Generate response using RAG pattern with LLM
        answer = await generate_rag_response(request.query, sources)
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        response = ChatResponse(
            answer=answer,
            sources=sources,
            query_id=query_id,
            response_time_ms=response_time_ms,
        )
        
        logger.info(f"Chat response generated", extra={
            "query_id": query_id,
            "response_time_ms": response_time_ms,
            "sources_used": len(sources),
        })
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", extra={
            "query_id": query_id,
            "query": request.query,
        })
        
        # Return error response
        return ChatResponse(
            answer="I'm sorry, but I encountered an error while processing your request. Please try again later or contact support.",
            sources=[],
            query_id=query_id,
            response_time_ms=int((time.time() - start_time) * 1000),
        )