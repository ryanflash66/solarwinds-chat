"""Application configuration using Pydantic Settings."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
    )

    # Application Settings
    app_name: str = Field(default="SolarWinds IT Solutions Chatbot", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # API Settings  
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")
    cors_origins: list[str] = Field(default=[
        "http://localhost:3000",      # Next.js (original plan)
        "http://localhost:8501",      # Streamlit local development
        "https://*.streamlit.app"     # Streamlit Cloud deployment
    ], description="CORS allowed origins")

    # SolarWinds API Settings
    solarwinds_api_key: Optional[str] = Field(default=None, description="SolarWinds API key")
    solarwinds_base_url: Optional[str] = Field(default=None, description="SolarWinds base URL")
    solarwinds_rate_limit: int = Field(default=10, description="SolarWinds API rate limit per minute")

    # Vector Store Settings
    chroma_host: str = Field(default="localhost", description="Chroma host")
    chroma_port: int = Field(default=8000, description="Chroma port")
    chroma_collection_name: str = Field(default="solutions", description="Chroma collection name")

    # LLM Provider Settings
    llm_provider: str = Field(default="openrouter", description="LLM provider (openrouter or local)")
    
    # OpenRouter Settings (when llm_provider=openrouter)
    openrouter_api_key: Optional[str] = Field(default=None, description="OpenRouter API key")
    openrouter_model: str = Field(default="anthropic/claude-3-sonnet", description="OpenRouter model")
    
    # Local LLM Settings (when llm_provider=local)
    ollama_base_url: str = Field(default="http://localhost:11434", description="OLLAMA base URL")
    ollama_model: str = Field(default="llama2", description="OLLAMA model name")

    # Embedding Settings
    embedding_provider: str = Field(default="openai", description="Embedding provider (openai or local)")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key for embeddings")
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding model name")
    embedding_dimension: int = Field(default=1536, description="Embedding dimension")

    # Redis Settings
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    redis_db: int = Field(default=0, description="Redis database number")

    # Background Job Settings
    sync_interval_minutes: int = Field(default=5, description="SolarWinds sync interval in minutes")
    max_workers: int = Field(default=4, description="Maximum number of background workers")

    # Performance Settings
    max_search_results: int = Field(default=4, description="Maximum number of search results")
    response_timeout_seconds: int = Field(default=30, description="Response timeout in seconds")
    
    # Security Settings
    allowed_hosts: list[str] = Field(default=["*"], description="Allowed hosts")


# Global settings instance
# Create settings with explicit environment variables for development
import os
os.environ.setdefault('DEBUG', 'true')
os.environ.setdefault('LLM_PROVIDER', 'ollama')
os.environ.setdefault('EMBEDDING_PROVIDER', 'local')

settings = Settings()