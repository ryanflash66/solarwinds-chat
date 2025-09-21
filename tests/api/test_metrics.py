"""Tests for the metrics endpoint."""

import time

import pytest
from fastapi.testclient import TestClient

import app.api.v1.metrics as metrics_module
from app.api.v1.metrics import get_uptime_seconds, reset_metrics_state


@pytest.fixture(autouse=True)
def reset_metrics_globals() -> None:
    """Ensure metrics module state is reset before and after each test."""

    reset_metrics_state()
    yield
    reset_metrics_state()


@pytest.fixture()
def metrics_payload(client: TestClient) -> dict:
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    return response.json()


@pytest.mark.api
def test_metrics_structure(metrics_payload: dict):
    """Ensure top-level keys exist."""

    assert "timestamp" in metrics_payload
    assert "application" in metrics_payload
    assert "system" in metrics_payload


@pytest.mark.api
@pytest.mark.parametrize(
    "field",
    [
        "uptime_seconds",
        "total_requests",
        "active_connections",
        "version",
        "environment",
        "llm_provider",
        "embedding_provider",
        "debug_mode",
    ],
)
def test_application_metrics_fields(metrics_payload: dict, field: str) -> None:
    """Application section exposes expected fields."""

    assert field in metrics_payload["application"], f"Missing application metric: {field}"


@pytest.mark.api
@pytest.mark.parametrize(
    "field",
    [
        "cpu_percent",
        "memory_percent",
        "memory_used_mb",
        "memory_total_mb",
        "disk_percent",
    ],
)
def test_system_metrics_fields(metrics_payload: dict, field: str) -> None:
    """System section exposes expected fields."""

    assert field in metrics_payload["system"], f"Missing system metric: {field}"


@pytest.mark.api
def test_total_requests_increments(client: TestClient, metrics_payload: dict) -> None:
    """Total request counter increments on each call."""

    second_response = client.get("/api/v1/metrics")
    assert second_response.status_code == 200

    second_payload = second_response.json()
    assert (
        second_payload["application"]["total_requests"]
        == metrics_payload["application"]["total_requests"] + 1
    )
    assert (
        second_payload["application"]["uptime_seconds"]
        >= metrics_payload["application"]["uptime_seconds"]
    )


@pytest.mark.api
def test_metrics_uptime_resets_on_reset_metrics_state() -> None:
    """Ensure uptime and start time update when metrics state resets."""

    time.sleep(0.1)
    uptime_before = get_uptime_seconds()
    start_time_before = metrics_module._start_time

    reset_metrics_state()

    uptime_after = get_uptime_seconds()
    start_time_after = metrics_module._start_time

    assert uptime_after < 0.05, f"Uptime after reset should be near zero, got {uptime_after}"
    assert (
        start_time_after > start_time_before
    ), "_start_time should be updated after reset"
