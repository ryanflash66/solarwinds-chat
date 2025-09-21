"""Health check endpoints."""

import inspect
import time
from datetime import datetime
from typing import Any, Callable, Dict

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


async def _safe_check(
    component_name: str,
    check_fn: Callable[[], Any],
    mapper: Callable[[Any], Dict[str, Any]],
) -> Dict[str, Any]:
    """Execute a health check function safely and map the result."""

    try:
        result = check_fn()
        if inspect.isawaitable(result):
            result = await result

        mapped = mapper(result)
        if "status" not in mapped:
            raise ValueError("Component mapper must include a 'status' field")
        return mapped
    except Exception as exc:  # pragma: no cover - defensive logging path
        logger.exception(
            "Health check component failure",
            extra={"component": component_name},
        )
        human_readable = component_name.replace("_", " ")
        return {
            "status": "unhealthy",
            "message": f"{human_readable} error: {exc}",
        }


async def _get_index_stats() -> Dict[str, Any]:
    from app.services.indexing_service import indexing_service

    return await indexing_service.get_index_stats()


async def _get_embedding_health() -> Dict[str, Any]:
    from app.services.indexing_service import indexing_service

    return await indexing_service.health_check()


async def _get_llm_health() -> Dict[str, Any]:
    from app.services.llm import llm_service

    return await llm_service.health_check()


async def _get_sync_status() -> Dict[str, Any]:
    from app.services.sync_service import sync_service

    return await sync_service.get_sync_status()


def _get_solarwinds_configuration() -> Dict[str, Any]:
    from app.services.solarwinds import solarwinds_service

    client = getattr(solarwinds_service, "client", None)
    configured = bool(client and client.api_key)
    message = (
        "SolarWinds API configured"
        if configured
        else "SolarWinds API not configured"
    )
    return {"configured": configured, "message": message}


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

    service_checks = [
        (
            "vector_store",
            _get_index_stats,
            lambda stats: {
                "status": "healthy" if stats.get("initialized") else "degraded",
                "message": (
                    "Vector store operational"
                    if stats.get("initialized")
                    else stats.get("error", "Service not initialized")
                ),
            },
        ),
        (
            "embedding_service",
            _get_embedding_health,
            lambda health: {
                "status": "healthy" if health.get("healthy") else "degraded",
                "message": health.get("error") or "Embedding service operational",
            },
        ),
        (
            "llm_service",
            _get_llm_health,
            lambda health: {
                "status": health.get("status", "unknown"),
                "message": health.get("error")
                or f"Provider: {health.get('provider', 'unknown')}",
            },
        ),
        (
            "sync_service",
            _get_sync_status,
            lambda sync_status: {
                "status": "healthy"
                if sync_status.get("service_running")
                else "degraded",
                "message": (
                    "Sync service running"
                    if sync_status.get("service_running")
                    else "Sync service not running"
                ),
            },
        ),
        (
            "solarwinds_api",
            _get_solarwinds_configuration,
            lambda config: {
                "status": "healthy" if config.get("configured") else "disabled",
                "message": config.get("message", "SolarWinds API not configured"),
            },
        ),
    ]

    for component_name, check_fn, mapper in service_checks:
        components[component_name] = await _safe_check(
            component_name,
            check_fn,
            mapper,
        )
    
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