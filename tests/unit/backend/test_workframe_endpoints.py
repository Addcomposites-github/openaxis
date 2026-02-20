"""Tests for work frame endpoints."""

import pytest


@pytest.mark.unit
class TestGetWorkframes:
    def test_get_all_returns_list(self, client):
        response = client.get("/api/workframes")
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        # Even without the service, the fallback returns a default frame
        assert len(data) >= 1

    def test_default_frame_has_expected_fields(self, client):
        data = client.get("/api/workframes").json()["data"][0]
        assert "id" in data
        assert "name" in data
        assert "position" in data


@pytest.mark.unit
class TestGetWorkframeById:
    def test_get_nonexistent_frame(self, client):
        from backend.server import state

        response = client.get("/api/workframes/nonexistent_frame")
        if state.workframe_service is None:
            assert response.status_code == 503
        else:
            assert response.status_code == 404


@pytest.mark.unit
class TestCreateWorkframe:
    def test_create_without_service(self, client):
        from backend.server import state

        if state.workframe_service is None:
            response = client.post(
                "/api/workframes",
                json={
                    "id": "wf_test",
                    "name": "Test Frame",
                    "position": [0, 0, 0],
                    "rotation": [0, 0, 0],
                },
            )
            assert response.status_code == 503


@pytest.mark.unit
class TestUpdateWorkframe:
    def test_update_without_service(self, client):
        from backend.server import state

        if state.workframe_service is None:
            response = client.put(
                "/api/workframes/wf_test",
                json={"name": "Updated"},
            )
            assert response.status_code == 503


@pytest.mark.unit
class TestDeleteWorkframe:
    def test_delete_without_service(self, client):
        from backend.server import state

        if state.workframe_service is None:
            response = client.delete("/api/workframes/wf_test")
            assert response.status_code == 503


@pytest.mark.unit
class TestAlignWorkframe:
    def test_align_without_service(self, client):
        from backend.server import state

        if state.workframe_service is None:
            response = client.post(
                "/api/workframes/align",
                json={
                    "origin": [0.0, 0.0, 0.0],
                    "zPoint": [0.0, 0.0, 1.0],
                    "xPoint": [1.0, 0.0, 0.0],
                },
            )
            assert response.status_code == 503


@pytest.mark.unit
class TestTransformPoint:
    def test_transform_without_service(self, client):
        from backend.server import state

        if state.workframe_service is None:
            response = client.post(
                "/api/workframes/transform-point",
                json={
                    "point": [1.0, 2.0, 3.0],
                    "frameId": "wf_test",
                    "direction": "to_frame",
                },
            )
            assert response.status_code == 503
