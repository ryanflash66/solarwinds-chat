"""Quick-start FastAPI application - starts fast without heavy dependencies."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.health_simple import router as health_router
from app.api.v1.chat_simple import router as chat_router
from app.api.v1.metrics import router as metrics_router
from app.core.config import settings
from app.core.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


def create_application() -> FastAPI:
    """Create and configure the FastAPI application for quick startup."""
    
    app = FastAPI(
        title=settings.app_name + " (Quick Start)",
        description="IT Solutions Chatbot - Quick Start Mode",
        version="1.0.0-quick",
        docs_url="/docs",
        redoc_url="/redoc",
        # No lifespan events for instant startup
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include only lightweight routers
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
        metrics_router,
        prefix=settings.api_v1_prefix,
        tags=["metrics"],
    )
    
    # Add a simple solutions endpoint
    @app.get(f"{settings.api_v1_prefix}/solutions/search")
    async def search_solutions():
        """Simple solutions search placeholder."""
        return [{
            "id": "quick-start-1",
            "title": "System Starting Up",
            "score": 1.0,
            "message": "Full search capabilities will be available once all services are loaded."
        }]
    
    @app.get(f"{settings.api_v1_prefix}/solutions/stats") 
    async def solutions_stats():
        """Simple solutions stats placeholder."""
        return {
            "total_documents": "Loading...",
            "collection_name": settings.chroma_collection_name,
            "status": "Quick start mode - full indexing available after complete startup"
        }
    
    logger.info("FastAPI application created successfully (quick start mode)")
    
    return app


# Create the application
app = create_application()


# Root endpoint
@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "SolarWinds IT Solutions Chatbot API (Quick Start Mode)",
        "version": "1.0.0-quick",
        "docs": "/docs",
        "status": "running",
        "mode": "quick-start",
        "note": "This is a quick-start version with simplified responses. For full AI functionality, use the complete deployment."
    }