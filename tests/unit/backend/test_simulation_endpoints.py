"""Tests for simulation endpoints."""

import pytest


@pytest.mark.unit
class TestSimulationState:
    def test_get_state(self, client):
        response = client.get("/api/simulation/state")
        assert response.status_code == 200
        data = response.json()["data"]
        # Either real state or fallback dict
        assert isinstance(data, dict)


@pytest.mark.unit
class TestSimulationTrajectory:
    def test_get_trajectory(self, client):
        response = client.get("/api/simulation/trajectory")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "waypoints" in data or "status" in data


@pytest.mark.unit
class TestSimulationList:
    def test_list_simulations(self, client):
        response = client.get("/api/simulation/list")
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)


@pytest.mark.unit
class TestSimulationCreate:
    def test_create_requires_toolpath(self, client):
        response = client.post(
            "/api/simulation/create",
            json={"toolpathId": "nonexistent_tp"},
        )
        assert response.status_code == 404

    def test_create_with_seeded_toolpath(self, client, seeded_toolpath):
        response = client.post(
            "/api/simulation/create",
            json={"toolpathId": seeded_toolpath},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "status" in data or "id" in data


@pytest.mark.unit
class TestSimulationStart:
    def test_start_simulation(self, client):
        response = client.post(
            "/api/simulation/start",
            json={"toolpathId": None},
        )
        assert response.status_code == 200
        assert "status" in response.json()["data"]


@pytest.mark.unit
class TestSimulationStop:
    def test_stop_simulation(self, client):
        response = client.post("/api/simulation/stop")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "stopped"
