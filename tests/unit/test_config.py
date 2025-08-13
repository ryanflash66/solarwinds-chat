"""Tests for configuration management."""

import pytest
from app.core.config import Settings


@pytest.mark.unit
def test_settings_defaults():
    """Test that settings have reasonable defaults."""
    settings = Settings()
    
    # Check basic defaults
    assert settings.app_name == "SolarWinds IT Solutions Chatbot"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.debug is False  # Should default to False
    assert settings.log_level == "INFO"
    
    # Check CORS origins
    assert isinstance(settings.cors_origins, list)
    assert len(settings.cors_origins) > 0
    
    # Check vector store defaults
    assert settings.chroma_host == "localhost"
    assert settings.chroma_port == 8000
    assert settings.chroma_collection_name == "solutions"
    
    # Check performance defaults
    assert settings.max_search_results == 4
    assert settings.response_timeout_seconds == 30


@pytest.mark.unit
def test_settings_validation():
    """Test settings validation."""
    # Test invalid log level would be caught by Pydantic if we had validation
    settings = Settings()
    
    # Check types
    assert isinstance(settings.debug, bool)
    assert isinstance(settings.chroma_port, int)
    assert isinstance(settings.max_search_results, int)


@pytest.mark.unit  
def test_settings_environment_override():
    """Test that environment variables override defaults."""
    import os
    
    # Save original values
    original_debug = os.environ.get('DEBUG')
    original_log_level = os.environ.get('LOG_LEVEL')
    
    try:
        # Set environment variables
        os.environ['DEBUG'] = 'true'
        os.environ['LOG_LEVEL'] = 'DEBUG'
        
        # Create new settings instance
        settings = Settings()
        
        assert settings.debug is True
        assert settings.log_level == 'DEBUG'
        
    finally:
        # Restore original values
        if original_debug is not None:
            os.environ['DEBUG'] = original_debug
        elif 'DEBUG' in os.environ:
            del os.environ['DEBUG']
            
        if original_log_level is not None:
            os.environ['LOG_LEVEL'] = original_log_level
        elif 'LOG_LEVEL' in os.environ:
            del os.environ['LOG_LEVEL']