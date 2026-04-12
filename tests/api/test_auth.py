"""Tests for API key authentication."""

from unittest.mock import patch

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.core.auth import verify_api_key


# ---------------------------------------------------------------------------
# Helper: build a tiny app that uses the verify_api_key dependency
# ---------------------------------------------------------------------------

def _make_auth_app() -> FastAPI:
    """Create a minimal FastAPI app with the auth dependency on a test route."""
    test_app = FastAPI()

    @test_app.get("/protected")
    async def protected_route(key=Depends(verify_api_key)):
        return {"status": "ok"}

    @test_app.get("/health")
    async def health_route():
        """Health-style endpoint with no auth dependency."""
        return {"status": "healthy"}

    return test_app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAuthDisabled:
    """When api_key is not configured (None), all endpoints pass without auth."""

    def test_no_auth_when_api_key_not_set(self):
        """Protected endpoint should be accessible when API_KEY is not configured."""
        with patch("app.core.auth.settings") as mock_settings:
            mock_settings.api_key = None
            app = _make_auth_app()
            client = TestClient(app)
            response = client.get("/protected")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    def test_no_auth_when_api_key_empty_string(self):
        """Protected endpoint should be accessible when API_KEY is empty string."""
        with patch("app.core.auth.settings") as mock_settings:
            mock_settings.api_key = ""
            app = _make_auth_app()
            client = TestClient(app)
            response = client.get("/protected")
            assert response.status_code == 200


class TestAuthEnabled:
    """When api_key is configured, requests must supply a valid X-API-Key header."""

    def test_missing_header_returns_401(self):
        """Request without X-API-Key header should return 401."""
        with patch("app.core.auth.settings") as mock_settings:
            mock_settings.api_key = "test-secret-key"
            app = _make_auth_app()
            client = TestClient(app)
            response = client.get("/protected")
            assert response.status_code == 401

    def test_wrong_key_returns_401(self):
        """Request with incorrect API key should return 401."""
        with patch("app.core.auth.settings") as mock_settings:
            mock_settings.api_key = "test-secret-key"
            app = _make_auth_app()
            client = TestClient(app)
            response = client.get("/protected", headers={"X-API-Key": "wrong-key"})
            assert response.status_code == 401

    def test_correct_key_returns_200(self):
        """Request with correct API key should succeed."""
        with patch("app.core.auth.settings") as mock_settings:
            mock_settings.api_key = "test-secret-key"
            app = _make_auth_app()
            client = TestClient(app)
            response = client.get(
                "/protected", headers={"X-API-Key": "test-secret-key"}
            )
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}


class TestHealthAlwaysAccessible:
    """Health endpoints without auth dependency should always be accessible."""

    def test_health_accessible_when_api_key_configured(self):
        """Health endpoint (no auth dependency) remains accessible regardless of api_key setting."""
        with patch("app.core.auth.settings") as mock_settings:
            mock_settings.api_key = "test-secret-key"
            app = _make_auth_app()
            client = TestClient(app)
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}

    def test_health_accessible_when_api_key_not_set(self):
        """Health endpoint remains accessible when api_key is None."""
        with patch("app.core.auth.settings") as mock_settings:
            mock_settings.api_key = None
            app = _make_auth_app()
            client = TestClient(app)
            response = client.get("/health")
            assert response.status_code == 200
