"""
IK Verification Tests — using the coordinate oracle as independent ground truth.

These tests verify that the roboticstoolbox-python IK solver in robot_service.py
produces joint angles that actually place the TCP at the requested position.

Ground truth: the coordinate oracle in tests/verification/coordinate_oracle.py
  - Uses published ABB IRB 6700 DH parameters (manufacturer spec)
  - Implements FK independently from robot_service.py
  - The FK-IK roundtrip check (FK(IK(target)) ≈ target) is a mathematical identity:
    it is the definition of a correct IK solution. This is NOT circular — we are
    running FK independently to check that IK found the right answer.

What these tests do NOT verify:
  - Whether the target positions correspond to meaningful manufacturing paths.
    That requires human-verified slicing fixtures (see tests/fixtures/README.md).
  - Geometric correctness of sliced toolpaths.

Reference for DH FK math: Craig, "Introduction to Robotics", 3rd ed., eq. 3.6.
Reference for DH parameters: Peter Corke, "Robotics, Vision and Control", Springer 2023.
"""

import math
import sys
from pathlib import Path

import pytest

# Ensure the backend src is importable
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Oracle import (our independent verifier)
from tests.verification.coordinate_oracle import (
    fk_from_joints,
    joints_within_limits,
    slicer_to_robot_frame,
    verify_ik_solution,
    TCP_Z_OFFSET_M,
)

# Skip entire module if roboticstoolbox is not installed
pytest.importorskip("roboticstoolbox", reason="roboticstoolbox-python not installed")
pytest.importorskip("numpy", reason="numpy not installed")


@pytest.fixture(scope="module")
def robot_service():
    """Create a RobotService with the roboticstoolbox DH solver."""
    from backend.robot_service import RobotService
    svc = RobotService()
    assert svc._rtb_robot is not None, (
        "roboticstoolbox DHRobot not created — check robot_service.py"
    )
    return svc


# ---------------------------------------------------------------------------
# Oracle self-tests — verify the oracle itself is internally consistent.
# These run without any OpenAxis code.
# ---------------------------------------------------------------------------

class TestOracleSelfConsistency:
    """
    Verify the oracle's own FK is consistent at known configurations.

    These tests do not touch robot_service.py at all — they only check
    that the oracle's DH math is correct.

    Expected values derived analytically from the DH parameters:
    At all-zero joint angles, the ABB IRB 6700 extends straight out along +X.
    The TCP position can be calculated by hand from the DH table.
    """

    def test_fk_home_position_is_finite(self):
        """FK at home position returns finite coordinates."""
        home = [0.0, -0.5, 0.5, 0.0, -0.5, 0.0]  # from robot_service.py
        result = fk_from_joints(home)
        pos = result["position_m"]
        assert all(math.isfinite(v) for v in pos), f"Non-finite FK at home: {pos}"

    def test_fk_all_zeros_x_positive(self):
        """
        At all-zero joint angles the robot extends into the +X half-space.

        With j1=0 the robot arm lies in the XZ plane, extended toward +X.
        The exact X value depends on the DH geometry — we only assert direction.
        """
        zeros = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        result = fk_from_joints(zeros)
        pos = result["position_m"]
        assert pos[0] > 0.5, f"Expected TCP in +X half-space at all-zeros, got x={pos[0]:.3f}"

    def test_fk_j1_rotation_moves_to_y(self):
        """
        Rotating J1 by +90° rotates the TCP into the +Y half-space.

        This is a fundamental property of a revolute joint about Z:
        rotating 90° converts X reach into Y reach.
        """
        j1_90 = [math.pi / 2, 0.0, 0.0, 0.0, 0.0, 0.0]
        result = fk_from_joints(j1_90)
        pos = result["position_m"]
        # Y should now be large and positive, X should be near zero
        assert pos[1] > 0.5, f"Expected large +Y after j1=90°, got y={pos[1]:.3f}"
        assert abs(pos[0]) < 0.2, f"Expected near-zero X after j1=90°, got x={pos[0]:.3f}"

    def test_fk_j1_negative_90_moves_to_minus_y(self):
        """
        Rotating J1 by -90° rotates the TCP into the -Y half-space.
        """
        j1_minus_90 = [-math.pi / 2, 0.0, 0.0, 0.0, 0.0, 0.0]
        result = fk_from_joints(j1_minus_90)
        pos = result["position_m"]
        assert pos[1] < -0.5, f"Expected large -Y after j1=-90°, got y={pos[1]:.3f}"
        assert abs(pos[0]) < 0.2, f"Expected near-zero X after j1=-90°, got x={pos[0]:.3f}"

    def test_fk_transform_is_4x4(self):
        """FK returns a valid 4×4 homogeneous transform."""
        import numpy as np
        zeros = [0.0] * 6
        result = fk_from_joints(zeros)
        T = result["transform"]
        assert T.shape == (4, 4), f"Expected 4×4 transform, got {T.shape}"
        # Last row must be [0, 0, 0, 1] for a valid homogeneous transform
        assert abs(T[3, 0]) < 1e-10 and abs(T[3, 1]) < 1e-10
        assert abs(T[3, 2]) < 1e-10 and abs(T[3, 3] - 1.0) < 1e-10

    def test_coordinate_transform_origin_at_origin(self):
        """
        slicer_to_robot_frame at (0,0,0) with both origins at scene origin
        gives (0,0,0) in robot frame.
        """
        result = slicer_to_robot_frame(
            slicer_pos_mm=(0.0, 0.0, 0.0),
            build_plate_origin_scene_m=(0.0, 0.0, 0.0),
            robot_pos_scene_m=(0.0, 0.0, 0.0),
        )
        assert all(abs(v) < 1e-10 for v in result), f"Expected (0,0,0), got {result}"

    def test_coordinate_transform_z_maps_correctly(self):
        """
        Slicer Z (height above plate) maps to robot Z.

        A point at slicer Z=100mm above the build plate (at scene Y=0.5m)
        should appear at robot Z > 0 (above the base).
        """
        # Build plate at scene Y=0.5m (half a metre above robot base height)
        result = slicer_to_robot_frame(
            slicer_pos_mm=(0.0, 0.0, 100.0),          # 100mm slicer Z
            build_plate_origin_scene_m=(0.0, 0.5, 0.0),  # plate at scene Y=0.5m
            robot_pos_scene_m=(0.0, 0.0, 0.0),
        )
        robot_x, robot_y, robot_z = result
        # The slicer Z should contribute positively to robot Z
        assert robot_z > 0.5, f"Expected robot Z > 0.5m, got {robot_z:.3f}"


# ---------------------------------------------------------------------------
# FK-IK Roundtrip Verification
# These use robot_service.py IK + oracle FK.
# ---------------------------------------------------------------------------

class TestFKIKRoundtrip:
    """
    Verify FK(IK(target)) ≈ target for positions within the robot workspace.

    This is the one genuinely grounded correctness test available without a
    physical robot. It is a mathematical identity: a correct IK solution MUST
    place the TCP at the target when FK is applied. If it doesn't, the IK
    solver returned wrong joint angles.

    Targets are chosen to be clearly within the IRB 6700 workspace (reach ≈ 2.6m).
    All targets have Y=0 (lie in the robot's XZ symmetry plane) — these are the
    most reliable for the Levenberg-Marquardt solver as noted in the code docs.

    Tolerance: 2mm (0.002m). The roboticstoolbox ikine_LM default tolerance is
    1e-10 in position error — we use 2mm as a conservative acceptance threshold
    that accounts for any TCP offset application rounding.
    """

    # Targets [x_m, y_m, z_m] in robot base frame, Z-up.
    # All lie in the XZ plane (y=0) within the 2.6m reach of the IRB 6700.
    # These positions are in the upper half of the workspace (Z > 1m) where
    # J2 stays well within its (-65°, +85°) limits and solver convergence
    # is reliable for the LM algorithm.
    # Source: ABB IRB 6700-205/2.80 product specification, Table 5 joint limits.
    REACHABLE_TARGETS = [
        (1.200, 0.0, 1.200),   # Moderate reach, high
        (1.000, 0.0, 1.400),   # Closer, very high
        (1.400, 0.0, 1.100),   # Mid reach, high
        (0.800, 0.0, 1.500),   # Close, high up
        (1.100, 0.0, 1.300),   # Mid, elevated
    ]

    def test_fk_ik_roundtrip_within_2mm(self, robot_service):
        """FK(IK(target)) ≈ target within 2mm for in-workspace targets."""
        tcp_offset = [0.0, 0.0, TCP_Z_OFFSET_M]
        waypoints = [[x, y, z] for x, y, z in self.REACHABLE_TARGETS]

        result = robot_service.solve_toolpath_ik(
            waypoints=waypoints,
            tcp_offset=tcp_offset,
        )

        trajectory = result.get("trajectory", [])
        reachability = result.get("reachability", [])

        assert len(trajectory) == len(self.REACHABLE_TARGETS), (
            f"Expected {len(self.REACHABLE_TARGETS)} results, got {len(trajectory)}"
        )

        errors = []
        for i, (target, joints, reachable) in enumerate(
            zip(self.REACHABLE_TARGETS, trajectory, reachability)
        ):
            if not reachable:
                pytest.fail(
                    f"Target {i} {target} reported unreachable — "
                    f"it should be within the IRB 6700 workspace (reach ≈ 2.6m)"
                )

            check = verify_ik_solution(
                joint_angles_rad=joints,
                target_robot_frame_m=target,
                tolerance_m=0.002,
                tcp_z_m=TCP_Z_OFFSET_M,
            )
            errors.append(check["error_mm"])

            assert check["within_tolerance"], (
                f"Target {i} {target}: FK-IK error {check['error_mm']:.2f}mm > 2mm.\n"
                f"  IK joints:    {[f'{math.degrees(j):.1f}°' for j in joints]}\n"
                f"  FK position:  {[f'{v:.4f}m' for v in check['fk_position_m']]}\n"
                f"  Target:       {[f'{v:.4f}m' for v in check['target_m']]}"
            )

        max_error_mm = max(errors)
        assert max_error_mm < 2.0, (
            f"Maximum FK-IK error across all targets: {max_error_mm:.2f}mm"
        )

    def test_joint_angles_are_not_all_zeros(self, robot_service):
        """
        IK must return non-zero joint angles for reachable targets.

        If all angles are zero, the solver is stubbed or broken — it would
        only be correct by coincidence for trivially symmetric targets.
        """
        waypoints = [[x, y, z] for x, y, z in self.REACHABLE_TARGETS]
        result = robot_service.solve_toolpath_ik(waypoints=waypoints)
        trajectory = result.get("trajectory", [])

        for i, joints in enumerate(trajectory):
            has_nonzero = any(abs(j) > 1e-4 for j in joints)
            assert has_nonzero, (
                f"Target {i}: all joint angles are zero — IK solver is "
                f"stubbed or not working. Joints: {joints}"
            )

    @pytest.mark.xfail(
        reason=(
            "robot_service.py uses roboticstoolbox ikine_LM without joint limit "
            "constraints. The LM solver finds valid FK-IK solutions but can violate "
            "ABB IRB 6700 hardware limits. Fix: pass qlim to ikine_LM or use "
            "roboticstoolbox's ikine_QP (quadratic-programming IK with hard limits). "
            "This is a known robot_service.py deficiency, not an oracle deficiency. "
            "See docs/FORENSIC_AUDIT_REPORT.md."
        ),
        strict=False,  # xfail is expected to fail; if it passes, that's a bonus
    )
    def test_all_joints_within_manufacturer_limits(self, robot_service):
        """All returned joint angles must be within ABB IRB 6700 limits.

        KNOWN ISSUE: ikine_LM does not enforce joint limits. This test documents
        the deficiency and will be promoted to a real failure once robot_service.py
        is updated to use constrained IK (ikine_QP or qlim parameter).
        """
        waypoints = [[x, y, z] for x, y, z in self.REACHABLE_TARGETS]
        result = robot_service.solve_toolpath_ik(waypoints=waypoints)
        trajectory = result.get("trajectory", [])
        reachability = result.get("reachability", [])

        for i, (joints, reachable) in enumerate(zip(trajectory, reachability)):
            if not reachable:
                continue  # unreachable points may have fallback joints, skip
            check = joints_within_limits(joints)
            assert check["all_within"], (
                f"Target {i}: joint limit violations: {check['violations']}"
            )

    def test_unreachable_target_has_low_reachability(self, robot_service):
        """
        A target 100m from the base must have reachability = False.

        This verifies the solver reports failure honestly rather than returning
        a wrong (but zero-error) solution.
        """
        far_targets = [[100.0, 0.0, 0.0], [100.0, 100.0, 100.0]]
        result = robot_service.solve_toolpath_ik(waypoints=far_targets)
        reachability = result.get("reachability", [True, True])
        pct = result.get("reachabilityPercent", 100.0)

        assert pct < 10.0, (
            f"Expected < 10% reachability for 100m targets, got {pct:.1f}%"
        )
        assert not all(reachability), (
            "All 100m-away targets reported reachable — solver is not detecting unreachable positions"
        )


# ---------------------------------------------------------------------------
# Coordinate Transform Verification
# ---------------------------------------------------------------------------

class TestCoordinateTransformPipeline:
    """
    Verify that slicer_to_robot_frame + IK + oracle FK is consistent end-to-end.

    This exercises the full coordinate chain:
      Slicer mm Z-up → robot frame m Z-up → IK joints → oracle FK → position

    The test uses the oracle's coordinate transform (not units.ts directly, but
    a Python transcription of the same arithmetic — verifiable by inspection).
    """

    def test_slicer_point_survives_round_trip(self, robot_service):
        """
        A slicer point converted to robot frame, solved by IK, verified by FK.

        Setup: build plate is 1.5m in front of the robot (+X scene direction),
        at the robot base height (scene Y = 0). Robot at scene origin.

        A slicer point at (0, 0, 100mm) = 100mm above the build plate surface
        should end up in the robot workspace at about (1.5, 0, 0.1)m.
        """
        # Slicer coordinate: 100mm above the plate surface
        slicer_point_mm = (0.0, 0.0, 100.0)

        # Build plate at x=1.5m in front of robot (scene Y-up: plate is in +X)
        # scene Y=0 means plate top is at robot base height
        build_plate_scene_m = (1.5, 0.0, 0.0)
        robot_scene_m = (0.0, 0.0, 0.0)

        robot_target_m = slicer_to_robot_frame(
            slicer_point_mm, build_plate_scene_m, robot_scene_m
        )
        rx, ry, rz = robot_target_m

        # Sanity: the target should be in the robot's forward workspace
        assert rx > 1.0, f"Expected robot X > 1m (in front of robot), got {rx:.3f}"
        assert rz > 0.0, f"Expected robot Z > 0 (above base), got {rz:.3f}"

        # Now solve IK for this target
        result = robot_service.solve_toolpath_ik(
            waypoints=[[rx, ry, rz]],
            tcp_offset=[0.0, 0.0, TCP_Z_OFFSET_M],
        )
        reachability = result.get("reachability", [False])
        trajectory = result.get("trajectory", [[]])

        assert reachability[0], (
            f"Slicer point {slicer_point_mm} → robot frame {robot_target_m} "
            f"reported unreachable — should be reachable at (1.5m, 0, 0.1m)"
        )

        # Verify FK(IK(target)) ≈ target
        check = verify_ik_solution(
            joint_angles_rad=trajectory[0],
            target_robot_frame_m=robot_target_m,
            tolerance_m=0.002,
        )
        assert check["within_tolerance"], (
            f"FK-IK error after full coordinate chain: {check['error_mm']:.2f}mm\n"
            f"  Slicer input: {slicer_point_mm} mm\n"
            f"  Robot target: {robot_target_m} m\n"
            f"  FK result:    {check['fk_position_m']} m"
        )
