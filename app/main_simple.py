"""Simplified FastAPI application for quick testing."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.health import router as health_router
from app.api.v1.chat import router as chat_router
from app.api.v1.solutions import router as solutions_router
from app.api.v1.metrics import router as metrics_router
from app.core.config import settings
from app.core.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


def create_application() -> FastAPI:
    """Create and configure the FastAPI application without heavy startup."""
    
    app = FastAPI(
        title=settings.app_name,
        description="IT Solutions Chatbot with RAG-powered SolarWinds integration",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        # No lifespan for faster startup
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(
        health_router,
        prefix=settings.api_v1_prefix,
        tags=["health"],
    )
    
    app.include_router(
        chat_router,
        prefix=settings.api_v1_prefix,
        tags=["chat"],
    )
    
    app.include_router(
        solutions_router,
        prefix=settings.api_v1_prefix,
        tags=["solutions"],
    )
    
    app.include_router(
        metrics_router,
        prefix=settings.api_v1_prefix,
        tags=["metrics"],
    )
    
    logger.info("FastAPI application created successfully (simple mode)")
    
    return app


# Create the application
app = create_application()


# Root endpoint
@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "SolarWinds IT Solutions Chatbot API (Simple Mode)",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "Documentation disabled in production",
        "status": "running",
    }