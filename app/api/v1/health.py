"""Health check endpoints."""

import inspect
import time
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import SolarWindsChatbotException
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

HealthCheckFn = Callable[[], Awaitable[Dict[str, Any]] | Dict[str, Any]]

EXPECTED_HEALTH_EXCEPTIONS: tuple[type[BaseException], ...] = (
    SolarWindsChatbotException,
    TimeoutError,
    ConnectionError,
    OSError,
)


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


async def _resolve_result(result: Any) -> Dict[str, Any]:
    """Normalize sync/async health check results into dictionaries."""

    if inspect.isawaitable(result):
        result = await result

    if not isinstance(result, dict):  # pragma: no cover - defensive validation
        raise TypeError("Health check functions must return a dictionary")

    return result


async def _safe_check(component_name: str, check_fn: HealthCheckFn) -> Dict[str, Any]:
    """Execute a health check function safely and map the result."""

    try:
        result = await _resolve_result(check_fn())
        if "status" not in result:
            raise ValueError("Component health result must include a 'status' field")
        return result
    except EXPECTED_HEALTH_EXCEPTIONS as exc:
        human_readable = component_name.replace("_", " ")
        logger.warning(
            "Health check component degraded",
            extra={"component": component_name, "error": str(exc)},
        )
        return {
            "status": "degraded",
            "message": f"{human_readable} issue: {exc}",
        }
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


def _flag_check_factory(
    get_data: Callable[[], Awaitable[Dict[str, Any]] | Dict[str, Any]],
    flag_key: str,
    *,
    ok_status: str = "healthy",
    fail_status: str = "degraded",
    ok_msg: str = "",
    fail_msg: str = "",
    exclude_keys: tuple[str, ...] = (),
) -> HealthCheckFn:
    """Create a simple health check from a flag in a data payload."""

    async def _check() -> Dict[str, Any]:
        data = await _resolve_result(get_data())
        is_ok = bool(data.get(flag_key))
        message = ok_msg if is_ok else (data.get("error") or fail_msg)

        result: Dict[str, Any] = {
            "status": ok_status if is_ok else fail_status,
            "message": message,
        }

        excluded_keys = set(exclude_keys)
        excluded_keys.update({flag_key, "error"})

        for key, value in data.items():
            if key in excluded_keys:
                continue
            result[key] = value

        return result

    return _check


async def check_vector_store() -> Dict[str, Any]:
    """Evaluate the health of the vector store and indexing pipeline."""

    from app.services.indexing_service import indexing_service

    stats = await indexing_service.get_index_stats()
    health = await indexing_service.health_check()

    if stats.get("initialized") and health.get("healthy"):
        result: Dict[str, Any] = {
            "status": "healthy",
            "message": "Vector store operational",
        }
    else:
        errors: list[str] = []
        if not stats.get("initialized"):
            errors.append(f"Stats: {stats.get('error', 'Not initialized')}")
        if not health.get("healthy"):
            errors.append(f"Health: {health.get('error', 'Unhealthy')}")
        error_message = "; ".join(errors) if errors else "Service not initialized"
        result = {
            "status": "degraded",
            "message": error_message,
        }

    # Preserve additional diagnostic details when available
    if "vector_store" in stats:
        result["vector_store"] = stats["vector_store"]
    if "embedding_service" in stats:
        result["embedding_service"] = stats["embedding_service"]
    if "timestamp" in health:
        result["checked_at"] = health["timestamp"]

    return result


async def check_llm_service() -> Dict[str, Any]:
    """Evaluate the health of the LLM provider layer."""

    from app.services.llm import llm_service

    health = await llm_service.health_check()
    status = health.get("status", "unknown")
    message = health.get("error") or f"Provider: {health.get('provider', 'unknown')}"

    result: Dict[str, Any] = {
        "status": status,
        "message": message,
    }

    for key in ("provider", "model"):
        if health.get(key):
            result[key] = health[key]

    return result


def _get_embedding_service_info() -> Awaitable[Dict[str, Any]]:
    from app.services.embedding import embedding_service

    return embedding_service.get_service_info()


def _get_sync_status() -> Awaitable[Dict[str, Any]]:
    from app.services.sync_service import sync_service

    return sync_service.get_sync_status()


def _get_solarwinds_configuration() -> Dict[str, Any]:
    from app.services.solarwinds import solarwinds_service

    client = getattr(solarwinds_service, "client", None)
    configured = bool(client and client.api_key)
    return {
        "configured": configured,
        "message": (
            "SolarWinds API configured"
            if configured
            else "SolarWinds API not configured"
        ),
    }


check_embedding_service = _flag_check_factory(
    _get_embedding_service_info,
    flag_key="initialized",
    ok_msg="Embedding service operational",
    fail_msg="Embedding service degraded",
)


check_sync_service = _flag_check_factory(
    _get_sync_status,
    flag_key="service_running",
    ok_msg="Sync service running",
    fail_msg="Sync service not running",
    exclude_keys=("last_sync_time", "next_sync_time"),
)


check_solarwinds_api = _flag_check_factory(
    _get_solarwinds_configuration,
    flag_key="configured",
    ok_status="healthy",
    fail_status="disabled",
    ok_msg="SolarWinds API configured",
    fail_msg="SolarWinds API not configured",
)


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
        ("vector_store", check_vector_store),
        ("embedding_service", check_embedding_service),
        ("llm_service", check_llm_service),
        ("sync_service", check_sync_service),
        ("solarwinds_api", check_solarwinds_api),
    ]

    for component_name, check_fn in service_checks:
        components[component_name] = await _safe_check(
            component_name,
            check_fn,
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