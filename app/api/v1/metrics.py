"""Metrics endpoints for monitoring and observability."""

import psutil
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class SystemMetrics(BaseModel):
    """System metrics model."""
    
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_usage_percent: float
    uptime_seconds: float


class ApplicationMetrics(BaseModel):
    """Application metrics model."""
    
    timestamp: datetime
    version: str
    environment: str
    llm_provider: str
    embedding_provider: str
    debug_mode: bool
    system: SystemMetrics
    
    # TODO: Add business metrics in future phases
    # - total_queries_processed: int
    # - average_response_time_ms: float
    # - vector_store_documents: int
    # - last_sync_time: Optional[datetime]
    # - error_rate_percent: float


# Store application start time for uptime calculation
_start_time = time.time()


@router.get(
    "/metrics",
    response_model=ApplicationMetrics,
    status_code=status.HTTP_200_OK,
    summary="Application Metrics",
    description="Returns comprehensive application and system metrics for monitoring",
)
async def get_metrics() -> ApplicationMetrics:
    """
    Get application and system metrics.
    
    Returns:
        ApplicationMetrics: Current application and system metrics
    """
    current_time = time.time()
    uptime = current_time - _start_time
    
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    system_metrics = SystemMetrics(
        cpu_percent=cpu_percent,
        memory_percent=memory.percent,
        memory_used_mb=memory.used / (1024 * 1024),
        memory_total_mb=memory.total / (1024 * 1024),
        disk_usage_percent=disk.percent,
        uptime_seconds=uptime,
    )
    
    logger.info("Metrics requested", extra={
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "uptime_seconds": uptime,
    })
    
    return ApplicationMetrics(
        timestamp=datetime.utcnow(),
        version="1.0.0",
        environment="development" if settings.debug else "production",
        llm_provider=settings.llm_provider,
        embedding_provider=settings.embedding_provider,
        debug_mode=settings.debug,
        system=system_metrics,
    )


@router.get(
    "/metrics/prometheus",
    status_code=status.HTTP_200_OK,
    summary="Prometheus Metrics",
    description="Returns metrics in Prometheus format for scraping",
    response_class=type("PlainTextResponse", (), {
        "media_type": "text/plain",
        "__init__": lambda self, content: setattr(self, "body", content.encode()),
    }),
)
async def get_prometheus_metrics():
    """
    Get metrics in Prometheus format.
    
    Returns:
        str: Metrics in Prometheus exposition format
    """
    current_time = time.time()
    uptime = current_time - _start_time
    
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    # Generate Prometheus format metrics
    prometheus_metrics = f"""# HELP solarwinds_chatbot_uptime_seconds Time since application start
# TYPE solarwinds_chatbot_uptime_seconds gauge
solarwinds_chatbot_uptime_seconds {uptime}

# HELP solarwinds_chatbot_cpu_percent CPU usage percentage
# TYPE solarwinds_chatbot_cpu_percent gauge
solarwinds_chatbot_cpu_percent {cpu_percent}

# HELP solarwinds_chatbot_memory_percent Memory usage percentage
# TYPE solarwinds_chatbot_memory_percent gauge
solarwinds_chatbot_memory_percent {memory.percent}

# HELP solarwinds_chatbot_memory_used_bytes Memory used in bytes
# TYPE solarwinds_chatbot_memory_used_bytes gauge
solarwinds_chatbot_memory_used_bytes {memory.used}

# HELP solarwinds_chatbot_info Application information
# TYPE solarwinds_chatbot_info gauge
solarwinds_chatbot_info{{version="1.0.0",llm_provider="{settings.llm_provider}",embedding_provider="{settings.embedding_provider}"}} 1
"""

    logger.debug("Prometheus metrics requested")
    return prometheus_metrics


@router.get(
    "/metrics/health-summary",
    status_code=status.HTTP_200_OK,
    summary="Health Summary",
    description="Returns a simple health summary for quick status checks",
)
async def get_health_summary() -> Dict[str, Any]:
    """
    Get a simple health summary.
    
    Returns:
        Dict[str, Any]: Simple health status summary
    """
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    # Determine health status based on resource usage
    health_status = "healthy"
    if cpu_percent > 80 or memory.percent > 90:
        health_status = "degraded"
    if cpu_percent > 95 or memory.percent > 95:
        health_status = "unhealthy"
    
    return {
        "status": health_status,
        "cpu_ok": cpu_percent < 80,
        "memory_ok": memory.percent < 90,
        "timestamp": datetime.utcnow().isoformat(),
    }