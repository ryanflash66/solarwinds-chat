"""Simple health check endpoints that don't import heavy services."""

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
    timestamp: str
    uptime_seconds: float
    components: Dict[str, Any]


# Store application start time
_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check (Quick Mode)",
    description="Returns basic health status without checking heavy services",
)
async def health_check() -> HealthResponse:
    """
    Perform a basic health check of the application.
    
    This version doesn't check heavy services to ensure fast response times.
    """
    current_time = time.time()
    uptime = current_time - _start_time
    
    # Basic system components only
    components = {
        "api": {"status": "healthy", "message": "API is operational"},
        "config": {"status": "healthy", "message": "Configuration loaded successfully"},
        "logging": {"status": "healthy", "message": "Logging system operational"},
        "mode": {"status": "info", "message": "Running in quick-start mode"},
        "note": {"status": "info", "message": "For full service health checks, use the complete deployment"}
    }
    
    # Determine overall status
    overall_status = "healthy"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat() + "Z",
        uptime_seconds=uptime,
        components=components
    )