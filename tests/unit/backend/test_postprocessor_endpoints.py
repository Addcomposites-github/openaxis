"""Tests for post processor endpoints."""

import pytest


@pytest.mark.unit
class TestPostProcessorFormats:
    def test_formats_returns_list(self, client):
        response = client.get("/api/postprocessor/formats")
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        # Each format should have id, name, extension
        for fmt in data:
            assert "id" in fmt
            assert "name" in fmt
            assert "extension" in fmt

    def test_formats_include_gcode(self, client):
        data = client.get("/api/postprocessor/formats").json()["data"]
        ids = [f["id"] for f in data]
        assert "gcode" in ids


@pytest.mark.unit
class TestPostProcessorConfig:
    def test_config_without_service(self, client):
        from backend.server import state

        if state.postprocessor_service is None:
            response = client.get("/api/postprocessor/config/gcode")
            assert response.status_code == 503


@pytest.mark.unit
class TestPostProcessorExport:
    def test_export_nonexistent_toolpath(self, client):
        response = client.post(
            "/api/postprocessor/export",
            json={"toolpathId": "no_such_tp", "format": "gcode"},
        )
        assert response.status_code == 404

    def test_export_without_service(self, client, seeded_toolpath):
        from backend.server import state

        if state.postprocessor_service is None:
            response = client.post(
                "/api/postprocessor/export",
                json={"toolpathId": seeded_toolpath, "format": "gcode"},
            )
            assert response.status_code == 503
