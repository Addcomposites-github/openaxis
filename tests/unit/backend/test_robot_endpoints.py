"""Tests for robot endpoints."""

import pytest


@pytest.mark.unit
class TestRobotConfig:
    def test_get_config_returns_robot_info(self, client):
        response = client.get("/api/robot/config")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "name" in data
        # Real service returns 'jointLimits', mock returns 'dof'
        assert "jointLimits" in data or "dof" in data

    def test_get_config_with_name_param(self, client):
        response = client.get("/api/robot/config?name=abb_irb6700")
        assert response.status_code == 200
        assert response.json()["data"]["name"] is not None


@pytest.mark.unit
class TestRobotAvailable:
    def test_available_returns_list(self, client):
        response = client.get("/api/robot/available")
        assert response.status_code == 200
        assert isinstance(response.json()["data"], list)


@pytest.mark.unit
class TestRobotJointLimits:
    def test_joint_limits_returns_data(self, client):
        response = client.get("/api/robot/joint-limits")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "jointNames" in data
        assert "limits" in data

    def test_joint_limits_has_six_joints(self, client):
        data = client.get("/api/robot/joint-limits").json()["data"]
        assert len(data["jointNames"]) == 6


@pytest.mark.unit
class TestRobotState:
    def test_get_state(self, client):
        response = client.get("/api/robot/state")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "connected" in data
        assert "joint_positions" in data


@pytest.mark.unit
class TestRobotFK:
    def test_fk_with_zero_joints(self, client):
        response = client.post("/api/robot/fk", json={"jointValues": [0.0] * 6})
        assert response.status_code == 200
        data = response.json()["data"]
        assert "position" in data
        assert "valid" in data

    def test_fk_with_tcp_offset(self, client):
        response = client.post(
            "/api/robot/fk",
            json={"jointValues": [0.0] * 6, "tcpOffset": [0.0, 0.0, 0.15]},
        )
        assert response.status_code == 200


@pytest.mark.unit
class TestRobotIK:
    def test_ik_returns_solution(self, client):
        response = client.post(
            "/api/robot/ik",
            json={"targetPosition": [1.5, 0.0, 1.0]},
        )
        assert response.status_code == 200
        assert "data" in response.json()

    def test_ik_validates_target_length(self, client):
        response = client.post(
            "/api/robot/ik",
            json={"targetPosition": [1.0, 2.0]},  # too few elements
        )
        assert response.status_code == 422  # validation error


@pytest.mark.unit
class TestRobotSolveTrajectory:
    def test_solve_trajectory_returns_result(self, client):
        response = client.post(
            "/api/robot/solve-trajectory",
            json={"waypoints": [[1.5, 0.0, 1.0], [1.5, 0.1, 1.0]]},
        )
        assert response.status_code == 200
        assert "data" in response.json()

    def test_solve_trajectory_empty_waypoints_rejected(self, client):
        response = client.post(
            "/api/robot/solve-trajectory",
            json={"waypoints": []},
        )
        assert response.status_code == 422  # min_length=1


@pytest.mark.unit
class TestRobotConnection:
    def test_connect(self, client):
        response = client.post("/api/robot/connect")
        assert response.status_code == 200
        assert response.json()["data"]["connected"] is True

    def test_disconnect(self, client):
        client.post("/api/robot/connect")
        response = client.post("/api/robot/disconnect")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["connected"] is False
        assert data["enabled"] is False

    def test_home_requires_connection(self, client):
        # Ensure disconnected
        client.post("/api/robot/disconnect")
        response = client.post("/api/robot/home")
        assert response.status_code == 400

    def test_home_when_connected(self, client):
        client.post("/api/robot/connect")
        response = client.post("/api/robot/home")
        assert response.status_code == 200
        assert response.json()["data"]["joint_positions"] == [0.0] * 6


@pytest.mark.unit
class TestRobotLoad:
    def test_load_robot(self, client):
        response = client.post("/api/robot/load", json={"name": "abb_irb6700"})
        assert response.status_code == 200
        data = response.json()["data"]
        assert "loaded" in data or "mock" in data
