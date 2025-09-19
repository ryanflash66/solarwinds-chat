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
    components: Dict[str, Any] = {
        "api": {"status": "healthy", "message": "API is operational"},
        "config": {"status": "healthy", "message": "Configuration loaded successfully"},
        "logging": {"status": "healthy", "message": "Logging system operational"},
    }

    # Indexing and embedding services
    try:
        from app.services.indexing_service import indexing_service

        stats = await indexing_service.get_index_stats()
        health = await indexing_service.health_check()

        if stats.get("initialized") and health.get("healthy"):
            components["vector_store"] = {
                "status": "healthy",
                "message": "Vector store operational",
            }
            components["embedding_service"] = {
                "status": "healthy",
                "message": "Embedding service operational",
            }
        else:
            error_message = health.get("error") or stats.get("error") or "Service not initialized"
            components["vector_store"] = {
                "status": "degraded",
                "message": error_message,
            }
            components["embedding_service"] = {
                "status": "degraded",
                "message": error_message,
            }
    except Exception as exc:
        message = str(exc)
        components["vector_store"] = {
            "status": "unhealthy",
            "message": f"Vector store error: {message}",
        }
        components["embedding_service"] = {
            "status": "unhealthy",
            "message": f"Embedding error: {message}",
        }

    # LLM provider
    try:
        from app.services.llm import llm_service

        llm_status = await llm_service.health_check()
        components["llm_service"] = {
            "status": llm_status.get("status", "unknown"),
            "message": llm_status.get("error")
            or f"Provider: {llm_status.get('provider', 'unknown')}",
        }
    except Exception as exc:
        components["llm_service"] = {
            "status": "unhealthy",
            "message": f"LLM service error: {str(exc)}",
        }

    # Sync service
    try:
        from app.services.sync_service import sync_service

        sync_status = await sync_service.get_sync_status()
        components["sync_service"] = {
            "status": "healthy" if sync_status.get("service_running") else "degraded",
            "message": "Sync service running"
            if sync_status.get("service_running")
            else "Sync service not running",
        }
    except Exception as exc:
        components["sync_service"] = {
            "status": "unhealthy",
            "message": f"Sync service error: {str(exc)}",
        }

    # SolarWinds API configuration
    try:
        from app.services.solarwinds import solarwinds_service

        if getattr(solarwinds_service, "client", None) and solarwinds_service.client.api_key:
            components["solarwinds_api"] = {
                "status": "healthy",
                "message": "SolarWinds API configured",
            }
        else:
            components["solarwinds_api"] = {
                "status": "disabled",
                "message": "SolarWinds API not configured",
            }
    except Exception as exc:
        components["solarwinds_api"] = {
            "status": "unhealthy",
            "message": f"SolarWinds error: {str(exc)}",
        }
    
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