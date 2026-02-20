"""
Tests for the pipeline orchestrator.

Tests use mocked services to validate step chaining, partial failure,
progress callbacks, and result structure — without requiring ORNL Slicer 2
or roboticstoolbox-python to be installed.
"""

import pytest
from unittest.mock import MagicMock, patch

from openaxis.pipeline import Pipeline, PipelineConfig, PipelineResult


@pytest.fixture
def mock_toolpath_service():
    svc = MagicMock()
    svc.generate_toolpath.return_value = {
        "id": "tp_001",
        "totalLayers": 5,
        "layerHeight": 2.0,
        "processType": "waam",
        "segments": [
            {
                "type": "perimeter",
                "layer": 0,
                "speed": 50.0,
                "points": [[10, 0, 0], [20, 0, 0], [20, 10, 0]],
            },
        ],
        "statistics": {
            "totalPoints": 3,
            "totalSegments": 1,
            "layerCount": 1,
            "estimatedTime": 10,
            "estimatedMaterial": 50,
        },
    }
    return svc


@pytest.fixture
def mock_simulation_service():
    svc = MagicMock()
    svc.create_simulation.return_value = {
        "id": "sim_001",
        "status": "ready",
        "totalLayers": 5,
    }
    svc.get_trajectory.return_value = {
        "waypoints": [
            {"position": [1.5, 0.0, 0.5], "time": 0.0},
            {"position": [1.6, 0.0, 0.5], "time": 1.0},
            {"position": [1.7, 0.0, 0.5], "time": 2.0},
        ],
        "totalTime": 2.0,
        "totalWaypoints": 3,
    }
    return svc


@pytest.fixture
def mock_robot_service():
    svc = MagicMock()
    svc.solve_toolpath_ik.return_value = {
        "trajectory": [[0.1, 0.2, 0.3, 0.4, 0.5, 0.6]] * 3,
        "reachability": [True, True, False],
        "reachableCount": 2,
        "totalPoints": 3,
        "reachabilityPercent": 66.7,
    }
    return svc


@pytest.fixture
def default_config():
    return PipelineConfig(
        geometry_path="test_part.stl",
        slicing_params={"layerHeight": 2.0},
    )


@pytest.mark.unit
class TestPipelineConfig:
    def test_defaults(self):
        config = PipelineConfig(geometry_path="test.stl")
        assert config.geometry_path == "test.stl"
        assert config.robot_name == "abb_irb6700"
        assert config.slicing_params == {}
        assert config.tcp_offset is None
        assert config.part_position is None

    def test_custom_params(self):
        config = PipelineConfig(
            geometry_path="custom.stl",
            slicing_params={"layerHeight": 3.0},
            robot_name="kuka_kr6",
            tcp_offset=[0, 0, 0.15, 0, 0, 0],
            part_position=[100, 200, 0],
        )
        assert config.robot_name == "kuka_kr6"
        assert config.tcp_offset == [0, 0, 0.15, 0, 0, 0]


@pytest.mark.unit
class TestPipelineExecution:
    def test_full_pipeline_success(
        self,
        mock_toolpath_service,
        mock_simulation_service,
        mock_robot_service,
        default_config,
    ):
        """Full pipeline: slice -> simulate -> IK all succeed."""
        pipeline = Pipeline(
            toolpath_service=mock_toolpath_service,
            robot_service=mock_robot_service,
            simulation_service=mock_simulation_service,
        )
        result = pipeline.execute(default_config)

        assert result.success is True
        assert result.toolpath_data is not None
        assert result.toolpath_data["id"] == "tp_001"
        assert result.simulation_data is not None
        assert result.trajectory_data is not None
        assert result.trajectory_data["reachableCount"] == 2
        assert result.step_completed == "ik_solve"
        assert len(result.steps) == 3
        assert all(s.success for s in result.steps)
        assert "slicing" in result.timings
        assert "simulation" in result.timings
        assert "ik_solve" in result.timings

    def test_slicing_only(self, mock_toolpath_service, default_config):
        """Pipeline with no simulation or robot service — slicing only."""
        pipeline = Pipeline(toolpath_service=mock_toolpath_service)
        result = pipeline.execute(default_config)

        assert result.success is True
        assert result.toolpath_data is not None
        assert result.simulation_data is None
        assert result.trajectory_data is None
        assert result.step_completed == "slicing"
        assert len(result.steps) == 1

    def test_slicing_failure_stops_pipeline(self, default_config):
        """If slicing fails, pipeline stops immediately."""
        svc = MagicMock()
        svc.generate_toolpath.side_effect = RuntimeError("ORNL Slicer 2 not found")

        pipeline = Pipeline(toolpath_service=svc)
        result = pipeline.execute(default_config)

        assert result.success is False
        assert result.toolpath_data is None
        assert len(result.errors) == 1
        assert "Slicing failed" in result.errors[0]
        assert result.step_completed == ""

    def test_simulation_failure_continues(
        self, mock_toolpath_service, default_config
    ):
        """If simulation fails, pipeline continues — still returns toolpath."""
        sim_svc = MagicMock()
        sim_svc.create_simulation.side_effect = RuntimeError("PyBullet error")

        pipeline = Pipeline(
            toolpath_service=mock_toolpath_service,
            simulation_service=sim_svc,
        )
        result = pipeline.execute(default_config)

        assert result.success is True
        assert result.toolpath_data is not None
        assert result.simulation_data is None
        assert "Simulation setup failed" in result.errors[0]
        assert result.step_completed == "slicing"

    def test_ik_failure_continues(
        self,
        mock_toolpath_service,
        mock_simulation_service,
        default_config,
    ):
        """If IK fails, pipeline continues — still returns toolpath + sim."""
        robot_svc = MagicMock()
        robot_svc.solve_toolpath_ik.side_effect = RuntimeError("IK solver timeout")

        pipeline = Pipeline(
            toolpath_service=mock_toolpath_service,
            robot_service=robot_svc,
            simulation_service=mock_simulation_service,
        )
        result = pipeline.execute(default_config)

        assert result.success is True
        assert result.toolpath_data is not None
        assert result.simulation_data is not None
        assert result.trajectory_data is None
        assert "IK solve failed" in result.errors[0]
        assert result.step_completed == "simulation"

    def test_progress_callback(
        self,
        mock_toolpath_service,
        mock_simulation_service,
        mock_robot_service,
        default_config,
    ):
        """Progress callback is called for each step."""
        calls = []
        callback = lambda step, pct: calls.append((step, pct))

        pipeline = Pipeline(
            toolpath_service=mock_toolpath_service,
            robot_service=mock_robot_service,
            simulation_service=mock_simulation_service,
            progress_callback=callback,
        )
        pipeline.execute(default_config)

        step_names = [c[0] for c in calls]
        assert "slicing" in step_names
        assert "simulation" in step_names
        assert "ik_solve" in step_names
        # Each step should have 0.0 start and 1.0 end
        slicing_calls = [(s, p) for s, p in calls if s == "slicing"]
        assert slicing_calls[0][1] == 0.0
        assert slicing_calls[1][1] == 1.0

    def test_timings_populated(
        self, mock_toolpath_service, default_config
    ):
        """Timings dict contains duration for completed steps."""
        pipeline = Pipeline(toolpath_service=mock_toolpath_service)
        result = pipeline.execute(default_config)

        assert "slicing" in result.timings
        assert result.timings["slicing"] >= 0.0

    def test_step_results_have_duration(
        self,
        mock_toolpath_service,
        mock_simulation_service,
        mock_robot_service,
        default_config,
    ):
        """Each StepResult has a duration_s field."""
        pipeline = Pipeline(
            toolpath_service=mock_toolpath_service,
            robot_service=mock_robot_service,
            simulation_service=mock_simulation_service,
        )
        result = pipeline.execute(default_config)

        for step in result.steps:
            assert step.duration_s >= 0.0
            assert isinstance(step.name, str)
            assert isinstance(step.success, bool)
