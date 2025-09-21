"""Health check endpoints."""

import time
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import SolarWindsChatbotException
from app.core.logging import get_logger
from app.services.indexing_service import indexing_service
from app.services.llm import llm_service
from app.services.solarwinds import solarwinds_service
from app.services.sync_service import sync_service

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


HealthCheckFn = Callable[[], Awaitable[Dict[str, Any]]]

EXPECTED_HEALTH_EXCEPTIONS: tuple[type[BaseException], ...] = (
    SolarWindsChatbotException,
    TimeoutError,
    ConnectionError,
)


async def _safe_check(component_name: str, check_fn: HealthCheckFn) -> Dict[str, Any]:
    """Execute a health check function while handling expected failures."""

    try:
        return await check_fn()
    except EXPECTED_HEALTH_EXCEPTIONS as exc:
        logger.error(
            "Health check component failure",
            extra={
                "component": component_name,
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
        )
        human_readable = component_name.replace("_", " ")
        return {
            "status": "unhealthy",
            "message": f"{human_readable} error: {exc}",
        }
    except Exception as exc:  # pragma: no cover - surfacing unexpected errors
        logger.exception(
            "Unexpected health check failure",
            extra={"component": component_name},
        )
        raise


async def check_vector_store() -> Dict[str, Any]:
    """Evaluate the vector store health."""

    stats = await indexing_service.get_index_stats()
    health = await indexing_service.health_check()

    if stats.get("initialized") and health.get("healthy"):
        return {"status": "healthy", "message": "Vector store operational"}

    error = health.get("error") or stats.get("error") or "Service not initialized"
    return {"status": "degraded", "message": error}


async def check_embedding_service() -> Dict[str, Any]:
    """Evaluate the embedding service health."""

    health = await indexing_service.health_check()
    if health.get("healthy"):
        return {"status": "healthy", "message": "Embedding service operational"}

    return {
        "status": "degraded",
        "message": health.get("error") or "Embedding service degraded",
    }


async def check_llm_service() -> Dict[str, Any]:
    """Evaluate the LLM service health."""

    health = await llm_service.health_check()
    status = health.get("status", "unknown")
    provider = health.get("provider")
    message = (
        health.get("message")
        or health.get("error")
        or (f"Provider: {provider}" if provider else "LLM service status unknown")
    )

    result: Dict[str, Any] = {"status": status, "message": message}
    if provider:
        result["provider"] = provider
    if model := health.get("model"):
        result["model"] = model
    return result


async def check_sync_service() -> Dict[str, Any]:
    """Evaluate the sync service health."""

    status = await sync_service.get_sync_status()
    if error := status.get("error"):
        return {"status": "unhealthy", "message": error}

    service_running = bool(status.get("service_running"))
    message = (
        "Sync service running" if service_running else "Sync service not running"
    )
    result: Dict[str, Any] = {
        "status": "healthy" if service_running else "degraded",
        "message": message,
    }

    for key in ("last_sync_time", "next_sync_time"):
        if status.get(key):
            result[key] = status[key]

    return result


async def check_solarwinds_api() -> Dict[str, Any]:
    """Report SolarWinds API configuration status."""

    client = getattr(solarwinds_service, "client", None)
    configured = bool(client and getattr(client, "api_key", None))
    return {
        "status": "healthy" if configured else "disabled",
        "message": (
            "SolarWinds API configured"
            if configured
            else "SolarWinds API not configured"
        ),
    }


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

    service_checks: list[tuple[str, HealthCheckFn]] = [
        ("vector_store", check_vector_store),
        ("embedding_service", check_embedding_service),
        ("llm_service", check_llm_service),
        ("sync_service", check_sync_service),
        ("solarwinds_api", check_solarwinds_api),
    ]

    for component_name, check_fn in service_checks:
        components[component_name] = await _safe_check(component_name, check_fn)
    
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