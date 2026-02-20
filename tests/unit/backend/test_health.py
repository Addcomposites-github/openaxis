"""Tests for health and project endpoints."""

import pytest


@pytest.mark.unit
class TestHealth:
    def test_health_returns_ok(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "services" in data
        assert "version" in data

    def test_health_services_are_booleans(self, client):
        data = client.get("/api/health").json()
        for name, available in data["services"].items():
            assert isinstance(available, bool), f"Service '{name}' should be bool"


@pytest.mark.unit
class TestProjects:
    def test_list_projects_initially_empty(self, client):
        # Clear projects first
        from backend.server import state
        state.projects.clear()
        response = client.get("/api/projects")
        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_create_project(self, client):
        response = client.post("/api/projects", json={"name": "Test Project"})
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "Test Project"
        assert "id" in data

    def test_create_project_with_custom_id(self, client):
        response = client.post(
            "/api/projects",
            json={"name": "Custom", "id": "custom_001"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] == "custom_001"

    def test_get_project(self, client):
        # Create first
        client.post("/api/projects", json={"name": "Get Me", "id": "get_test"})
        response = client.get("/api/projects/get_test")
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Get Me"

    def test_get_project_not_found(self, client):
        response = client.get("/api/projects/nonexistent_id_12345")
        assert response.status_code == 404

    def test_update_project(self, client):
        client.post("/api/projects", json={"name": "Before", "id": "upd_test"})
        response = client.put(
            "/api/projects/upd_test",
            json={"name": "After"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "After"

    def test_update_project_not_found(self, client):
        response = client.put(
            "/api/projects/nonexistent_upd",
            json={"name": "Fail"},
        )
        assert response.status_code == 404

    def test_delete_project(self, client):
        client.post("/api/projects", json={"name": "Delete Me", "id": "del_test"})
        response = client.delete("/api/projects/del_test")
        assert response.status_code == 200
        # Verify it's gone
        response = client.get("/api/projects/del_test")
        assert response.status_code == 404

    def test_delete_project_not_found(self, client):
        response = client.delete("/api/projects/nonexistent_del")
        assert response.status_code == 404
