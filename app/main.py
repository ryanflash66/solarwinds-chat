"""Main FastAPI application."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.health import router as health_router
from app.api.v1.chat import router as chat_router
from app.api.v1.solutions import router as solutions_router
from app.api.v1.metrics import router as metrics_router
from app.core.config import settings
from app.core.exceptions import SolarWindsChatbotException
from app.core.logging import setup_logging, get_logger
from app.services.sync_service import sync_service
from app.services.indexing_service import indexing_service
from app.services.llm import llm_service

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    logger.info("Starting SolarWinds IT Solutions Chatbot")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Log level: {settings.log_level}")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"Embedding Provider: {settings.embedding_provider}")
    
    # Initialize services
    try:
        logger.info("Starting indexing service")
        await indexing_service.initialize()
    except Exception as e:
        logger.error(f"Failed to start indexing service: {str(e)}")
        # Continue startup even if indexing service fails
    
    try:
        logger.info("Starting LLM service")
        await llm_service.initialize()
    except Exception as e:
        logger.error(f"Failed to start LLM service: {str(e)}")
        # Continue startup even if LLM service fails
    
    try:
        logger.info("Starting background sync service")
        await sync_service.start()
    except Exception as e:
        logger.error(f"Failed to start sync service: {str(e)}")
        # Continue startup even if sync service fails
    
    yield
    
    # Shutdown
    logger.info("Shutting down SolarWinds IT Solutions Chatbot")
    
    # Cleanup services
    try:
        logger.info("Stopping background sync service")
        await sync_service.stop()
    except Exception as e:
        logger.error(f"Error stopping sync service: {str(e)}")
    
    try:
        logger.info("Stopping LLM service")
        await llm_service.cleanup()
    except Exception as e:
        logger.error(f"Error stopping LLM service: {str(e)}")
    
    try:
        logger.info("Stopping indexing service")
        await indexing_service.cleanup()
    except Exception as e:
        logger.error(f"Error stopping indexing service: {str(e)}")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title=settings.app_name,
        description="IT Solutions Chatbot with RAG-powered SolarWinds integration",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
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
    
    return app


# Exception handlers
def setup_exception_handlers(app: FastAPI) -> None:
    """Setup custom exception handlers."""
    
    @app.exception_handler(SolarWindsChatbotException)
    async def custom_exception_handler(
        request: Request, exc: SolarWindsChatbotException
    ) -> JSONResponse:
        """Handle custom application exceptions."""
        logger.error(
            f"Application error: {exc.message}",
            extra={
                "url": str(request.url),
                "method": request.method,
                "details": exc.details,
                "status_code": exc.status_code,
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "details": exc.details,
                "status_code": exc.status_code,
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.exception(
            "Unexpected error occurred",
            extra={
                "url": str(request.url),
                "method": request.method,
                "error_type": type(exc).__name__,
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "details": {} if not settings.debug else {"message": str(exc)},
                "status_code": 500,
            }
        )


# Create the application
app = create_application()
setup_exception_handlers(app)


# Root endpoint
@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "SolarWinds IT Solutions Chatbot API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "Documentation disabled in production",
    }