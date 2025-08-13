"""Custom exceptions for the application."""

from typing import Any, Dict, Optional


class SolarWindsChatbotException(Exception):
    """Base exception for SolarWinds Chatbot."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.status_code = status_code


class ConfigurationError(SolarWindsChatbotException):
    """Raised when there's a configuration error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, details, status_code=500)


class SolarWindsAPIError(SolarWindsChatbotException):
    """Raised when SolarWinds API returns an error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, details, status_code=502)


class VectorStoreError(SolarWindsChatbotException):
    """Raised when vector store operations fail."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, details, status_code=503)


class LLMProviderError(SolarWindsChatbotException):
    """Raised when LLM provider operations fail."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, details, status_code=503)


# Alias for backward compatibility
LLMError = LLMProviderError


class EmbeddingError(SolarWindsChatbotException):
    """Raised when embedding operations fail."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, details, status_code=503)


class RateLimitError(SolarWindsChatbotException):
    """Raised when rate limits are exceeded."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, details, status_code=429)


class ValidationError(SolarWindsChatbotException):
    """Raised when request validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, details, status_code=400)