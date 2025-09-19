"""Tests for the metrics endpoint."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_metrics_structure(client: TestClient):
    """Ensure the metrics endpoint matches the Streamlit UI expectations."""
    first_response = client.get("/api/v1/metrics")
    assert first_response.status_code == 200

    payload = first_response.json()
    assert "timestamp" in payload
    assert "application" in payload
    assert "system" in payload

    application = payload["application"]
    for key in [
        "uptime_seconds",
        "total_requests",
        "active_connections",
        "version",
        "environment",
        "llm_provider",
        "embedding_provider",
        "debug_mode",
    ]:
        assert key in application, f"Missing application metric: {key}"

    system = payload["system"]
    for key in [
        "cpu_percent",
        "memory_percent",
        "memory_used_mb",
        "memory_total_mb",
        "disk_percent",
    ]:
        assert key in system, f"Missing system metric: {key}"

    second_response = client.get("/api/v1/metrics")
    assert second_response.status_code == 200

    second_payload = second_response.json()
    assert (
        second_payload["application"]["total_requests"]
        == application["total_requests"] + 1
    )
    assert second_payload["application"]["uptime_seconds"] >= application["uptime_seconds"]
