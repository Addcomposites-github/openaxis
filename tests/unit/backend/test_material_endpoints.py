"""Tests for material endpoints."""

import pytest


@pytest.mark.unit
class TestGetMaterials:
    def test_get_all_materials(self, client):
        response = client.get("/api/materials")
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)

    def test_filter_by_process_type(self, client):
        response = client.get("/api/materials?process_type=waam")
        assert response.status_code == 200
        assert isinstance(response.json()["data"], list)


@pytest.mark.unit
class TestMaterialsSummary:
    def test_summary_returns_dict(self, client):
        response = client.get("/api/materials/summary")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "totalMaterials" in data


@pytest.mark.unit
class TestProcessTypes:
    def test_process_types_returns_list(self, client):
        response = client.get("/api/materials/process-types")
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        assert len(data) > 0


@pytest.mark.unit
class TestGetMaterialById:
    def test_get_nonexistent_material(self, client):
        """Without service: 503. With service but not found: 404."""
        from backend.server import state

        response = client.get("/api/materials/nonexistent_mat")
        if state.material_service is None:
            assert response.status_code == 503
        else:
            assert response.status_code == 404


@pytest.mark.unit
class TestCreateMaterial:
    def test_create_without_service(self, client):
        from backend.server import state

        if state.material_service is None:
            response = client.post(
                "/api/materials",
                json={
                    "id": "custom_001",
                    "name": "Test Material",
                    "processType": "waam",
                    "category": "metal",
                },
            )
            assert response.status_code == 503


@pytest.mark.unit
class TestDeleteMaterial:
    def test_delete_without_service(self, client):
        from backend.server import state

        if state.material_service is None:
            response = client.delete("/api/materials/some_mat")
            assert response.status_code == 503
