"""
Pipeline liveness and structural tests.

These tests verify that the full pipeline (slicer → simulation → IK) runs
end-to-end using the mock ORNL Slicer 2 fixture from conftest.py, produces
non-empty, structurally valid output, and that error paths fail loudly.

WHAT THESE TESTS VERIFY:
  - The pipeline runs without crashing (liveness)
  - Output structures are non-empty and have finite coordinates (structural)
  - Waypoint times are monotonically increasing (timing logic)
  - Error paths return failures, not silent empty success (honesty)
  - FK-IK roundtrip via the coordinate oracle (correctness — the one grounded check)

WHAT THESE TESTS DO NOT VERIFY:
  - Whether sliced coordinates match the geometry of the input part.
    That requires a human-verified ORNL Slicer 2 fixture (see tests/fixtures/README.md).
  - Whether the simulation physically represents reality.
    (The "simulation" is trajectory replay — see FORENSIC_AUDIT_REPORT.md)

The mock_ornl_slicer fixture from conftest.py patches the ORNL subprocess to return
a 2-layer 10×10mm square G-code. This lets CI run without the ORNL binary installed.

API notes (verified against actual source):
  - ORNLSlicer().slice(stl_path) → Toolpath object with .segments, .to_dict()
  - SimulationService().create_simulation(toolpath_dict) → summary dict;
    .get_trajectory(sim_id) → {"waypoints": [...], "totalTime": ..., ...}
  - PostProcessorService().export(toolpath_dict, format_name="gcode") → {"content": ..., ...}
  - Pipeline(toolpath_service) — toolpath_service is required
"""

import math
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tests.verification.coordinate_oracle import (
    verify_ik_solution,
    slicer_to_robot_frame,
    TCP_Z_OFFSET_M,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stl(tmp_path: Path) -> str:
    """Write a minimal valid STL file (content ignored by mock slicer)."""
    stl = tmp_path / "test.stl"
    stl.write_text("solid test\nendsolid test\n")
    return str(stl)


def _toolpath_to_dict(toolpath) -> dict:
    """Convert a Toolpath object to the dict format SimulationService expects.

    Toolpath.segments contains ToolpathSegment objects with COMPAS Point instances.
    SimulationService.create_simulation() expects:
        {"segments": [{"points": [[x,y,z], ...], "speed": float, "type": str, "layer": int}],
         "totalLayers": int}

    The Toolpath class does not implement to_dict() — this is the explicit conversion.
    """
    segments = []
    for seg in toolpath.segments:
        # seg.points are COMPAS Point objects with .x, .y, .z attributes
        points = [[p.x, p.y, p.z] for p in seg.points]
        # seg.type is a ToolpathType enum — .value gives the string name
        seg_type = seg.type.value if hasattr(seg.type, "value") else str(seg.type)
        segments.append({
            "points": points,
            "speed": seg.speed,
            "type": seg_type,
            "layer": seg.layer_index,
        })
    return {
        "segments": segments,
        "totalLayers": toolpath.total_layers,
    }


def _slice_to_dict(mock_ornl_slicer, tmp_path: Path) -> dict:
    """Slice the dummy STL and return the toolpath as a SimulationService-compatible dict."""
    from openaxis.slicing.ornl_slicer import ORNLSlicer
    toolpath = ORNLSlicer().slice(_make_stl(tmp_path))
    return _toolpath_to_dict(toolpath)


# ---------------------------------------------------------------------------
# Test Case 1: Slicer produces valid toolpath
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestSlicerLiveness:
    """Verify the mock slicer pipeline runs and returns structurally valid output."""

    def test_slice_returns_toolpath(self, mock_ornl_slicer, tmp_path):
        """Slicing returns a Toolpath object with at least one segment."""
        from openaxis.slicing.ornl_slicer import ORNLSlicer
        from openaxis.slicing.toolpath import Toolpath

        stl = _make_stl(tmp_path)
        toolpath = ORNLSlicer().slice(stl)

        assert isinstance(toolpath, Toolpath), "Expected a Toolpath object"
        assert len(toolpath.segments) > 0, "Toolpath has no segments"

    def test_all_coordinates_are_finite(self, mock_ornl_slicer, tmp_path):
        """Every coordinate in the toolpath must be a finite float (no NaN/Inf)."""
        from openaxis.slicing.ornl_slicer import ORNLSlicer

        stl = _make_stl(tmp_path)
        toolpath = ORNLSlicer().slice(stl)

        for seg in toolpath.segments:
            for pt in seg.points:
                assert math.isfinite(pt.x), f"Non-finite X in segment: {pt.x}"
                assert math.isfinite(pt.y), f"Non-finite Y in segment: {pt.y}"
                assert math.isfinite(pt.z), f"Non-finite Z in segment: {pt.z}"

    def test_all_z_values_non_negative(self, mock_ornl_slicer, tmp_path):
        """All Z coordinates must be >= 0 — layers are at or above the build plate.

        The first point of a perimeter may be exactly z=0.0 (layer 0 start),
        which is valid (it is on the build plate surface, not below it).
        """
        from openaxis.slicing.ornl_slicer import ORNLSlicer

        stl = _make_stl(tmp_path)
        toolpath = ORNLSlicer().slice(stl)

        for seg in toolpath.segments:
            for pt in seg.points:
                assert pt.z >= 0, f"Z coordinate < 0 in sliced toolpath: z={pt.z}"

    def test_toolpath_has_multiple_layers(self, mock_ornl_slicer, tmp_path):
        """Toolpath must have at least 2 layers (the mock G-code has exactly 2)."""
        from openaxis.slicing.ornl_slicer import ORNLSlicer

        stl = _make_stl(tmp_path)
        toolpath = ORNLSlicer().slice(stl)

        # Mock G-code has BEGINNING LAYER: 0 and BEGINNING LAYER: 1
        assert toolpath.total_layers >= 2, (
            f"Expected at least 2 layers, got {toolpath.total_layers}"
        )


# ---------------------------------------------------------------------------
# Test Case 2: SimulationService produces valid waypoints
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestSimulationServiceLiveness:
    """Verify waypoint generation is structurally valid.

    SimulationService lives in backend.simulation_service (not openaxis.simulation.service).
    It takes a toolpath dict, not a Toolpath object.
    """

    def _get_waypoints(self, mock_ornl_slicer, tmp_path) -> list:
        """Slice STL, create simulation, return the waypoint list."""
        from backend.simulation_service import SimulationService

        toolpath_dict = _slice_to_dict(mock_ornl_slicer, tmp_path)
        svc = SimulationService()
        sim_summary = svc.create_simulation(toolpath_dict)
        sim_id = sim_summary["id"]
        trajectory = svc.get_trajectory(sim_id)
        return trajectory["waypoints"]

    def test_waypoints_are_non_empty(self, mock_ornl_slicer, tmp_path):
        """SimulationService produces at least one waypoint."""
        waypoints = self._get_waypoints(mock_ornl_slicer, tmp_path)
        assert len(waypoints) > 0, "No waypoints generated from toolpath"

    def test_waypoint_times_monotonically_increasing(self, mock_ornl_slicer, tmp_path):
        """Time must never go backwards — simulation must be causal."""
        waypoints = self._get_waypoints(mock_ornl_slicer, tmp_path)
        times = [w["time"] for w in waypoints]
        for i in range(1, len(times)):
            assert times[i] >= times[i - 1], (
                f"Time went backwards at index {i}: {times[i-1]:.3f}s → {times[i]:.3f}s"
            )

    def test_total_time_is_positive(self, mock_ornl_slicer, tmp_path):
        """Total trajectory duration must be > 0 seconds."""
        waypoints = self._get_waypoints(mock_ornl_slicer, tmp_path)
        total = waypoints[-1]["time"] if waypoints else 0
        assert total > 0, "Total trajectory time is 0 or negative"

    def test_all_waypoint_positions_are_finite(self, mock_ornl_slicer, tmp_path):
        """Every waypoint position coordinate must be finite."""
        waypoints = self._get_waypoints(mock_ornl_slicer, tmp_path)
        for i, w in enumerate(waypoints):
            for coord in w["position"]:
                assert math.isfinite(coord), (
                    f"Non-finite coordinate in waypoint {i}: {w['position']}"
                )


# ---------------------------------------------------------------------------
# Test Case 3: FK-IK roundtrip via oracle (the one grounded correctness check)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestFKIKRoundtripViaOracle:
    """
    Full pipeline IK verification using the coordinate oracle.

    The oracle independently computes FK from the same DH parameters used by
    robot_service.py, but via a separate code path. If robot_service.py's IK
    returns wrong joint angles, the oracle's FK will compute a position that
    doesn't match the target and the test fails.

    This is the FK-IK roundtrip: FK(IK(target)) ≈ target.
    It is a mathematical identity — the one correctness check available
    without physics-verified fixtures.
    """

    def test_ik_roundtrip_for_mock_waypoints(self, mock_ornl_slicer, tmp_path):
        """
        Slice → simulate → convert to robot frame → solve IK → verify via oracle FK.

        Uses the mock slicer's 10×10mm square, offset to a position in front of the
        robot so all waypoints are reachable.
        """
        pytest.importorskip("roboticstoolbox", reason="roboticstoolbox-python not installed")

        from openaxis.slicing.ornl_slicer import ORNLSlicer
        from backend.simulation_service import SimulationService
        from backend.robot_service import RobotService

        stl = _make_stl(tmp_path)
        toolpath = ORNLSlicer().slice(stl)
        toolpath_dict = _toolpath_to_dict(toolpath)

        svc_sim = SimulationService()
        sim_summary = svc_sim.create_simulation(toolpath_dict)
        trajectory = svc_sim.get_trajectory(sim_summary["id"])
        waypoints = trajectory["waypoints"]

        # Convert waypoints to robot frame:
        # Build plate 1.5m in front of the robot at robot base height.
        build_plate_scene_m = (1.5, 0.0, 0.0)
        robot_scene_m = (0.0, 0.0, 0.0)

        robot_targets = []
        for w in waypoints:
            pos_mm = tuple(w["position"])  # (x_mm, y_mm, z_mm) from slicer
            robot_targets.append(
                slicer_to_robot_frame(pos_mm, build_plate_scene_m, robot_scene_m)
            )

        # Solve IK for all waypoints
        svc = RobotService()
        if svc._rtb_robot is None:
            pytest.skip("roboticstoolbox DHRobot not available")

        ik_result = svc.solve_toolpath_ik(
            waypoints=[[rx, ry, rz] for rx, ry, rz in robot_targets],
            tcp_offset=[0.0, 0.0, TCP_Z_OFFSET_M],
        )

        trajectory_joints = ik_result.get("trajectory", [])
        reachability = ik_result.get("reachability", [])
        pct = ik_result.get("reachabilityPercent", 0)

        assert pct >= 90.0, (
            f"Expected ≥90% reachability for in-workspace targets, got {pct:.1f}%"
        )

        # Verify each reachable point with the oracle
        errors_mm = []
        for i, (target, joints, reachable) in enumerate(
            zip(robot_targets, trajectory_joints, reachability)
        ):
            if not reachable:
                continue

            check = verify_ik_solution(
                joint_angles_rad=joints,
                target_robot_frame_m=target,
                tolerance_m=0.002,
                tcp_z_m=TCP_Z_OFFSET_M,
            )
            errors_mm.append(check["error_mm"])

            assert check["within_tolerance"], (
                f"Waypoint {i}: oracle FK shows IK error {check['error_mm']:.2f}mm > 2mm.\n"
                f"  Target:      {[f'{v:.4f}' for v in check['target_m']]} m\n"
                f"  FK position: {[f'{v:.4f}' for v in check['fk_position_m']]} m"
            )

        assert len(errors_mm) > 0, "No reachable waypoints found — IK solver may not be working"

    def test_ik_joint_angles_not_all_zeros(self, mock_ornl_slicer, tmp_path):
        """
        IK must return non-zero joint angles.

        All-zero joint angles indicate the solver is stubbed (returns a default)
        rather than actually computing a solution.
        """
        pytest.importorskip("roboticstoolbox", reason="roboticstoolbox-python not installed")

        from openaxis.slicing.ornl_slicer import ORNLSlicer
        from backend.simulation_service import SimulationService
        from backend.robot_service import RobotService

        stl = _make_stl(tmp_path)
        toolpath = ORNLSlicer().slice(stl)
        toolpath_dict = _toolpath_to_dict(toolpath)

        svc_sim = SimulationService()
        sim_summary = svc_sim.create_simulation(toolpath_dict)
        trajectory = svc_sim.get_trajectory(sim_summary["id"])
        waypoints = trajectory["waypoints"][:5]

        build_plate_scene_m = (1.5, 0.0, 0.0)
        robot_targets = [
            slicer_to_robot_frame(tuple(w["position"]), build_plate_scene_m)
            for w in waypoints
        ]

        svc = RobotService()
        if svc._rtb_robot is None:
            pytest.skip("roboticstoolbox DHRobot not available")

        result = svc.solve_toolpath_ik(
            waypoints=[[rx, ry, rz] for rx, ry, rz in robot_targets],
            tcp_offset=[0.0, 0.0, TCP_Z_OFFSET_M],
        )

        for i, (joints, reachable) in enumerate(
            zip(result.get("trajectory", []), result.get("reachability", []))
        ):
            if not reachable:
                continue
            has_nonzero = any(abs(j) > 1e-4 for j in joints)
            assert has_nonzero, (
                f"Waypoint {i}: all joint angles are zero — IK solver is returning "
                f"default/stub values rather than a real solution. Joints: {joints}"
            )


# ---------------------------------------------------------------------------
# Test Case 4: Post-processor exports contain movement commands
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestExportLiveness:
    """Verify exporters produce non-empty output with real movement commands.

    PostProcessorService.export(toolpath_dict, format_name="gcode")
    returns {"content": str, "extension": str, ...}
    """

    def _get_toolpath_dict(self, mock_ornl_slicer, tmp_path) -> dict:
        from openaxis.slicing.ornl_slicer import ORNLSlicer
        toolpath = ORNLSlicer().slice(_make_stl(tmp_path))
        return _toolpath_to_dict(toolpath)

    def test_gcode_has_movement_commands(self, mock_ornl_slicer, tmp_path):
        """G-code export must contain G0 or G1 movement commands."""
        toolpath_dict = self._get_toolpath_dict(mock_ornl_slicer, tmp_path)

        from backend.postprocessor_service import PostProcessorService
        svc = PostProcessorService()
        result = svc.export(toolpath_dict, format_name="gcode")

        content = result.get("content", "")
        assert content and len(content) > 0, "G-code output is empty"
        lines = content.splitlines()
        movement_lines = [l for l in lines if l.strip().startswith(("G0", "G1", "G01", "G00"))]
        assert len(movement_lines) > 0, (
            f"G-code has no movement commands. First 10 lines:\n" +
            "\n".join(lines[:10])
        )

    def test_gcode_no_placeholder_text(self, mock_ornl_slicer, tmp_path):
        """G-code must not contain TODO or NotImplemented — it must be real output."""
        toolpath_dict = self._get_toolpath_dict(mock_ornl_slicer, tmp_path)

        from backend.postprocessor_service import PostProcessorService
        result = PostProcessorService().export(toolpath_dict, format_name="gcode")
        content = result.get("content", "")

        assert "TODO" not in content, "G-code contains 'TODO' placeholder"
        assert "NotImplemented" not in content, "G-code contains 'NotImplemented' placeholder"


# ---------------------------------------------------------------------------
# Test Case 5: Error paths are honest (fail loudly, not silently)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestErrorPathsAreHonest:
    """
    Verify that failures return clear errors, not silent empty success.

    An endpoint that returns HTTP 200 with an empty result when a service
    is unavailable is worse than useless — it hides the real problem.
    """

    def test_nonexistent_stl_fails_clearly(self):
        """Slicing a non-existent file must raise an exception, not return empty.

        ORNLSlicer raises FileNotFoundError — either because the binary is not
        installed (raised in __init__) or because the input file does not exist.
        There is no custom ORNLSlicerNotFoundError class — FileNotFoundError is
        the documented exception type.
        """
        from openaxis.slicing.ornl_slicer import ORNLSlicer
        import os

        if os.environ.get("ORNL_SLICER2_PATH") or ORNLSlicer.is_available():
            # Real binary is installed — test that a bad file path raises
            slicer = ORNLSlicer()
            with pytest.raises(Exception) as exc_info:
                slicer.slice("/nonexistent/path/model.stl")
            assert exc_info.value is not None, "Expected an exception for bad file path"
        else:
            # Binary not installed — instantiation should raise FileNotFoundError
            with pytest.raises(FileNotFoundError):
                ORNLSlicer().slice("/any/path.stl")

    def test_nonplanar_strategy_raises_not_implemented(self):
        """
        Non-planar slicers must raise NotImplementedError, not return empty data.

        This confirms the UI is honest — selecting a non-planar strategy will
        fail clearly at the backend rather than silently producing nothing.
        """
        from openaxis.slicing.angled_slicer import AngledSlicer
        from openaxis.slicing.radial_slicer import RadialSlicer

        for SlicerClass in (AngledSlicer, RadialSlicer):
            slicer = SlicerClass()
            with pytest.raises(NotImplementedError) as exc_info:
                slicer.slice("/any/path.stl")
            assert exc_info.value is not None

    def test_pipeline_requires_toolpath_service(self):
        """
        Pipeline must not accept zero-argument construction — it requires a
        toolpath_service. This test verifies the constructor is honest about
        its dependencies rather than silently accepting None and producing empty output.

        Pipeline(toolpath_service=...) is the real API.
        """
        from openaxis.pipeline import Pipeline

        # Calling Pipeline() with no arguments must raise TypeError (required arg missing)
        with pytest.raises(TypeError, match="toolpath_service"):
            Pipeline()
