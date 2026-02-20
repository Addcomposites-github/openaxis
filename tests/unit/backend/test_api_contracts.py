"""Tests for API response shape contracts.

Validates that every endpoint returns the expected JSON structure
({ status, data } or { status, error }) so the frontend can rely
on a consistent contract.
"""

import pytest


@pytest.mark.unit
class TestApiResponseContract:
    """Every successful response must have { status: "success", data: ... }."""

    @pytest.mark.parametrize("path", [
        "/api/health",
        "/api/robot/config",
        "/api/robot/available",
        "/api/robot/joint-limits",
        "/api/robot/state",
        "/api/simulation/state",
        "/api/simulation/trajectory",
        "/api/simulation/list",
        "/api/materials",
        "/api/materials/summary",
        "/api/materials/process-types",
        "/api/workframes",
        "/api/postprocessor/formats",
        "/api/monitoring/sensors",
        "/api/monitoring/system",
        "/api/tools",
    ])
    def test_get_endpoints_return_standard_shape(self, client, path):
        """All GET endpoints must return well-formed JSON."""
        response = client.get(path)
        assert response.status_code == 200
        body = response.json()
        # Health endpoint uses a different schema (direct fields)
        if path == "/api/health":
            assert "status" in body
            assert body["status"] == "ok"
            assert "version" in body
            assert "services" in body
        else:
            assert "status" in body
            assert body["status"] == "success"
            assert "data" in body


@pytest.mark.unit
class TestErrorResponseContract:
    """Error responses must have { status: "error", error: "..." }."""

    @pytest.mark.parametrize("path", [
        "/api/projects/nonexistent_contract_test",
        "/api/toolpath/nonexistent_contract_test",
    ])
    def test_404_returns_error_shape(self, client, path):
        response = client.get(path)
        assert response.status_code == 404
        body = response.json()
        assert body["status"] == "error"
        assert "error" in body
        assert isinstance(body["error"], str)

    def test_422_returns_validation_error(self, client):
        """Pydantic validation errors should return 422."""
        response = client.post("/api/robot/ik", json={"targetPosition": [1.0]})
        assert response.status_code == 422

    def test_post_endpoints_return_standard_shape(self, client):
        """POST robot/fk with valid input returns standard response."""
        response = client.post("/api/robot/fk", json={"jointValues": [0.0] * 6})
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert "data" in body
