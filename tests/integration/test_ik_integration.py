"""
Integration tests for IK solver using compas_fab PyBulletClient backend.

These tests verify that the IKSolver correctly integrates with PyBullet
to solve inverse kinematics for the ABB IRB 6700 robot using the real
URDF model and mesh files.

Library under test: compas_fab.backends.PyBulletClient
"""

import os
from pathlib import Path

import numpy as np
import pytest
from compas.geometry import Frame, Point, Vector
from compas_robots import Configuration, RobotModel

from openaxis.core.robot import RobotLoader
from openaxis.motion.kinematics import IKSolver

# Resolve URDF path relative to the project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
URDF_PATH = str(PROJECT_ROOT / "config" / "urdf" / "abb_irb6700.urdf")

# Skip all tests in this module if URDF doesn't exist
pytestmark = pytest.mark.skipif(
    not os.path.exists(URDF_PATH),
    reason=f"URDF not found at {URDF_PATH}",
)


@pytest.fixture(scope="module")
def robot_model():
    """Load the ABB IRB 6700 robot model from URDF."""
    return RobotLoader.load_from_urdf(URDF_PATH)


@pytest.fixture(scope="module")
def ik_solver(robot_model):
    """Create an IKSolver with PyBullet backend (module-scoped for speed)."""
    solver = IKSolver(robot_model, urdf_path=URDF_PATH)
    yield solver
    solver.close()


class TestIKSolverInit:
    """Test IKSolver initialization and lifecycle."""

    def test_init_with_valid_urdf(self, robot_model):
        """IKSolver initializes with a valid URDF path."""
        solver = IKSolver(robot_model, urdf_path=URDF_PATH)
        assert solver._client is not None
        assert solver._pybullet_robot is not None
        assert solver.n_joints == 6
        assert solver.joint_names == [
            "joint_1", "joint_2", "joint_3",
            "joint_4", "joint_5", "joint_6",
        ]
        solver.close()

    def test_init_without_urdf(self, robot_model):
        """IKSolver without URDF path creates a stub (no backend)."""
        solver = IKSolver(robot_model)
        assert solver._client is None
        assert solver._pybullet_robot is None

        # solve() should raise RuntimeError
        target = Frame.worldXY()
        with pytest.raises(RuntimeError, match="not initialized"):
            solver.solve(target)

    def test_init_with_invalid_urdf(self, robot_model):
        """IKSolver with non-existent URDF raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="not found"):
            IKSolver(robot_model, urdf_path="/nonexistent/path/robot.urdf")

    def test_context_manager(self, robot_model):
        """IKSolver works as a context manager."""
        with IKSolver(robot_model, urdf_path=URDF_PATH) as solver:
            assert solver._client is not None
            # Solve a simple IK to verify it's working
            target = _fk_at_config(solver, [0.0] * 6)
            result = solver.solve(target)
            assert result is not None

        # After context exit, client should be cleaned up
        assert solver._client is None


class TestFKIKRoundtrip:
    """Test forward kinematics -> inverse kinematics roundtrip accuracy."""

    @pytest.mark.parametrize(
        "joint_values",
        [
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # Home position
            [0.5, 0.3, -0.5, 0.0, 0.5, 0.0],  # Moderate angles
            [-0.8, 0.5, -1.0, 1.0, -0.5, 0.5],  # Various quadrants
            [1.0, -0.5, 0.5, 2.0, 1.0, -1.0],  # Large wrist angles
            [0.0, 1.0, -2.0, 0.0, 0.0, 0.0],  # Extended arm
        ],
        ids=["home", "moderate", "multi_quadrant", "large_wrist", "extended"],
    )
    def test_fk_ik_roundtrip_with_seed(self, ik_solver, joint_values):
        """FK(config) -> IK(frame, seed=config) should roundtrip with <1mm error."""
        target_frame = _fk_at_config(ik_solver, joint_values)

        # Use the original config as seed (best case)
        result = ik_solver.solve(target_frame, initial_guess=joint_values)
        assert result is not None, f"IK failed for config {joint_values}"

        # Verify by FK of the IK result
        result_frame = _fk_at_config(ik_solver, list(result.joint_values))
        pos_error = np.linalg.norm(
            np.array(result_frame.point) - np.array(target_frame.point)
        )

        assert pos_error < 0.001, (
            f"FK-IK roundtrip error {pos_error * 1000:.4f} mm > 1 mm "
            f"for config {joint_values}"
        )

    @pytest.mark.parametrize(
        "joint_values",
        [
            [0.5, 0.3, -0.5, 0.0, 0.5, 0.0],
            [-0.8, 0.5, -1.0, 1.0, -0.5, 0.5],
            [1.0, -0.5, 0.5, 2.0, 1.0, -1.0],
        ],
        ids=["case_a", "case_b", "case_c"],
    )
    def test_fk_ik_roundtrip_zero_seed(self, ik_solver, joint_values):
        """FK(config) -> IK(frame, seed=zeros) should still converge to <2mm."""
        target_frame = _fk_at_config(ik_solver, joint_values)

        # Use zero seed (harder case for numerical IK)
        result = ik_solver.solve(target_frame, initial_guess=[0.0] * 6)
        assert result is not None, (
            f"IK with zero seed failed for target at "
            f"({target_frame.point.x:.3f}, {target_frame.point.y:.3f}, "
            f"{target_frame.point.z:.3f})"
        )

        # Verify with looser tolerance for zero-seed
        result_frame = _fk_at_config(ik_solver, list(result.joint_values))
        pos_error = np.linalg.norm(
            np.array(result_frame.point) - np.array(target_frame.point)
        )

        assert pos_error < 0.002, (
            f"FK-IK roundtrip (zero seed) error {pos_error * 1000:.4f} mm > 2 mm"
        )

    def test_ik_returns_correct_joint_names(self, ik_solver):
        """IK solution should have the correct joint names."""
        target = _fk_at_config(ik_solver, [0.0] * 6)
        result = ik_solver.solve(target)

        assert result is not None
        assert len(result.joint_values) == 6
        assert result.joint_names == [
            "joint_1", "joint_2", "joint_3",
            "joint_4", "joint_5", "joint_6",
        ]


class TestIKEdgeCases:
    """Test IK solver edge cases and failure handling."""

    def test_unreachable_target_returns_none(self, ik_solver):
        """IK for a target far outside workspace should return None."""
        # Point 20 meters away — well outside IRB 6700 workspace (2.6m reach)
        unreachable_frame = Frame(
            Point(20.0, 20.0, 20.0),
            Vector(1, 0, 0),
            Vector(0, 1, 0),
        )
        result = ik_solver.solve(unreachable_frame)
        assert result is None

    def test_solve_with_tolerance(self, ik_solver):
        """IK respects the position tolerance parameter."""
        target = _fk_at_config(ik_solver, [0.0] * 6)

        # Very tight tolerance should still pass for same-seed roundtrip
        result_tight = ik_solver.solve(
            target, initial_guess=[0.0] * 6, tolerance=1e-6
        )
        assert result_tight is not None

    def test_default_seed(self, ik_solver):
        """IK without explicit seed should use zero seed by default."""
        target = _fk_at_config(ik_solver, [0.0] * 6)
        result = ik_solver.solve(target)
        assert result is not None


class TestSolveMultiple:
    """Test finding multiple IK solutions."""

    def test_finds_multiple_solutions(self, ik_solver):
        """solve_multiple should find multiple distinct solutions."""
        target = _fk_at_config(ik_solver, [0.0] * 6)
        solutions = ik_solver.solve_multiple(target, n_solutions=4)

        assert len(solutions) >= 1, "Should find at least 1 solution"

        # If multiple solutions found, verify they're distinct
        if len(solutions) > 1:
            for i in range(len(solutions)):
                for j in range(i + 1, len(solutions)):
                    diff = np.max(
                        np.abs(
                            np.array(solutions[i].joint_values)
                            - np.array(solutions[j].joint_values)
                        )
                    )
                    assert diff > 0.01, (
                        f"Solutions {i} and {j} are not distinct "
                        f"(max diff = {diff:.4f} rad)"
                    )

    def test_all_solutions_are_valid(self, ik_solver):
        """All solutions from solve_multiple should be valid IK solutions."""
        target = _fk_at_config(ik_solver, [0.5, 0.3, -0.5, 0.0, 0.5, 0.0])
        solutions = ik_solver.solve_multiple(target, n_solutions=4)

        for i, sol in enumerate(solutions):
            result_frame = _fk_at_config(ik_solver, list(sol.joint_values))
            pos_error = np.linalg.norm(
                np.array(result_frame.point) - np.array(target.point)
            )
            assert pos_error < 0.001, (
                f"Solution {i} has position error {pos_error * 1000:.4f} mm"
            )


# ── Helper Functions ─────────────────────────────────────────────────────────


def _fk_at_config(solver: IKSolver, joint_values: list) -> Frame:
    """Compute FK for a joint configuration using the solver's PyBullet robot."""
    pybullet_jn = solver._pybullet_robot.get_configurable_joint_names()
    config = Configuration.from_revolute_values(joint_values, pybullet_jn)
    return solver._pybullet_robot.forward_kinematics(
        config, options={"link": solver.tool_frame}
    )
