"""Health check endpoints."""

import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    components: Dict[str, Any]


# Store application start time
_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Returns the health status of the application and its components",
)
async def health_check() -> HealthResponse:
    """
    Perform a health check of the application.
    
    Returns:
        HealthResponse: Current health status and system information
    """
    current_time = time.time()
    uptime = current_time - _start_time
    
    # Check system components
    components = {
        "api": {"status": "healthy", "message": "API is operational"},
        "config": {"status": "healthy", "message": "Configuration loaded successfully"},
        "logging": {"status": "healthy", "message": "Logging system operational"},
    }
    
    # Check optional services
    try:
        from app.services.indexing_service import indexing_service
        health_check = await indexing_service.health_check()
        components["vector_store"] = {"status": "healthy", "message": "Vector store operational"}
        components["embeddings"] = {"status": "healthy", "message": "Embedding service operational"}
    except Exception as e:
        components["vector_store"] = {"status": "unhealthy", "message": f"Vector store error: {str(e)}"}
    
    try:
        from app.services.llm import llm_service
        llm_health = await llm_service.health_check()
        components["llm"] = llm_health
    except Exception as e:
        components["llm"] = {"status": "unhealthy", "message": f"LLM service error: {str(e)}"}
    
    try:
        from app.services.sync_service import sync_service
        sync_status = sync_service.get_sync_status()
        components["sync_service"] = {"status": "healthy", "message": "Sync service operational"}
    except Exception as e:
        components["sync_service"] = {"status": "unhealthy", "message": f"Sync service error: {str(e)}"}
    
    try:
        from app.services.solarwinds import solarwinds_service
        # Only test if configured
        if hasattr(solarwinds_service, 'api_client') and solarwinds_service.api_client:
            components["solarwinds"] = {"status": "healthy", "message": "SolarWinds API configured"}
        else:
            components["solarwinds"] = {"status": "disabled", "message": "SolarWinds API not configured (development)"}
    except Exception as e:
        components["solarwinds"] = {"status": "unhealthy", "message": f"SolarWinds error: {str(e)}"}
    
    logger.info("Health check requested", extra={
        "uptime_seconds": uptime,
        "components": len(components)
    })
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        environment="development" if settings.debug else "production",
        uptime_seconds=uptime,
        components=components,
    )


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness Check",
    description="Returns readiness status for load balancer health checks",
)
async def readiness_check() -> Dict[str, str]:
    """
    Perform a readiness check for Kubernetes/container orchestration.
    
    Returns:
        Dict[str, str]: Simple ready status
    """
    logger.debug("Readiness check requested")
    return {"status": "ready"}


@router.get(
    "/liveness",
    status_code=status.HTTP_200_OK,
    summary="Liveness Check", 
    description="Returns liveness status for container health monitoring",
)
async def liveness_check() -> Dict[str, str]:
    """
    Perform a liveness check for container health monitoring.
    
    Returns:
        Dict[str, str]: Simple alive status
    """
    logger.debug("Liveness check requested")
    return {"status": "alive"}