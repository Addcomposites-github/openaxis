"""Tests for geometry endpoints."""

import io
import pytest


@pytest.mark.unit
class TestGeometryImport:
    def test_import_nonexistent_file(self, client):
        """Importing a file that doesn't exist returns 404 (with service) or 200 (mock)."""
        response = client.post(
            "/api/geometry/import",
            json={"filePath": "/tmp/nonexistent_test_file.stl"},
        )
        # With real geometry_service: 404 (file not found)
        # Without service: 200 (mock response)
        assert response.status_code in (200, 404)

    def test_upload_alias_matches_import(self, client):
        """POST /api/geometry/upload is an alias for /api/geometry/import."""
        r1 = client.post("/api/geometry/import", json={"filePath": "/tmp/x.stl"})
        r2 = client.post("/api/geometry/upload", json={"filePath": "/tmp/x.stl"})
        # Both should return the same status code
        assert r1.status_code == r2.status_code


@pytest.mark.unit
class TestGeometryUploadFile:
    def test_upload_stl_file(self, client):
        # Minimal STL binary header (80 bytes) + 0 triangles (4 bytes)
        stl_content = b"\x00" * 80 + b"\x00\x00\x00\x00"
        response = client.post(
            "/api/geometry/upload-file",
            files={"file": ("cube.stl", io.BytesIO(stl_content), "application/octet-stream")},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["originalName"] == "cube.stl"
        assert data["format"] == "stl"
        assert "serverPath" in data

    def test_upload_rejects_unsupported_format(self, client):
        response = client.post(
            "/api/geometry/upload-file",
            files={"file": ("bad.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "Unsupported format" in response.json()["error"]

    def test_upload_accepts_obj(self, client):
        response = client.post(
            "/api/geometry/upload-file",
            files={"file": ("model.obj", io.BytesIO(b"v 0 0 0\n"), "text/plain")},
        )
        assert response.status_code == 200
        assert response.json()["data"]["format"] == "obj"


@pytest.mark.unit
class TestGeometryMeshOps:
    """Geometry boolean/repair/analyze with invalid geometry IDs."""

    def test_boolean_invalid_geometry(self, client):
        response = client.post(
            "/api/geometry/boolean",
            json={
                "geometryIdA": "nonexistent_a",
                "geometryIdB": "nonexistent_b",
                "operation": "union",
            },
        )
        # 503 without service, 400 with service (invalid geometry IDs)
        assert response.status_code in (400, 503)

    def test_repair_invalid_geometry(self, client):
        response = client.post(
            "/api/geometry/repair",
            json={"geometryId": "nonexistent"},
        )
        assert response.status_code in (400, 503)

    def test_analyze_invalid_geometry(self, client):
        response = client.post(
            "/api/geometry/analyze",
            json={"geometryId": "nonexistent"},
        )
        assert response.status_code in (400, 503)
