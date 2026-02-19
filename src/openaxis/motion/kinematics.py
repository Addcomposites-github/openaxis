"""
Inverse kinematics solvers for robotic manipulators.

Uses compas_fab's PyBulletClient backend for numerical IK solving.
PyBullet provides damped least-squares IK via the calculateInverseKinematics
API, which handles full 6-DOF (position + orientation).

Library: https://gramaziokohler.github.io/compas_fab/
PyBullet IK: https://pybullet.org/wordpress/ (calculateInverseKinematics)

DELETED in Feb 2026 audit:
- Custom scipy.optimize IK solver (custom substitution for MoveIt2 IK)
- Numerical Jacobian IK solver (hardcoded jacobian[3:, i] = 0, position-only)

See docs/UNGROUNDED_CODE.md for full deletion registry.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

import numpy as np
from compas.geometry import Frame
from compas_robots import Configuration, RobotModel

logger = logging.getLogger(__name__)


class IKSolver:
    """
    Inverse kinematics solver using compas_fab PyBulletClient backend.

    Wraps compas_fab's PyBulletClient.inverse_kinematics() which uses
    PyBullet's calculateInverseKinematics (damped least-squares IK).

    Usage::

        solver = IKSolver(robot_model, urdf_path="config/urdf/abb_irb6700.urdf")
        solution = solver.solve(target_frame)
        if solution is not None:
            print(f"Joint angles: {solution.joint_values}")
        solver.close()

    Or as a context manager::

        with IKSolver(robot_model, urdf_path="path/to/robot.urdf") as solver:
            solution = solver.solve(target_frame)
    """

    def __init__(
        self,
        robot: RobotModel,
        urdf_path: Optional[str] = None,
        group: Optional[str] = None,
        tool_frame: str = "link_6",
    ):
        """
        Initialize IK solver with compas_fab PyBulletClient backend.

        Args:
            robot: Robot model from compas_robots (used for joint info).
                   If None and urdf_path is provided, the model will be
                   loaded automatically from the URDF file.
            urdf_path: Path to URDF file. Required for IK solving.
                       PyBullet loads the robot from this file.
            group: Planning group name (default: use all configurable joints)
            tool_frame: Name of the end-effector link for IK solving.
                        Default 'link_6' works reliably with PyBullet IK.
                        Note: 'tool0' may fail with PyBullet IK for robots
                        with fixed-joint tool frames (rotated frames confuse
                        the numerical solver).
        """
        self.group = group
        self.tool_frame = tool_frame

        # If no robot model provided but we have a URDF, load the model
        if robot is None and urdf_path is not None:
            robot = RobotModel.from_urdf_file(urdf_path)

        self.robot = robot

        # Get joint information from the robot model
        self.joints = [j for j in robot.iter_joints() if j.is_configurable()]
        self.joint_names = [j.name for j in self.joints]
        self.n_joints = len(self.joints)

        # PyBullet client and loaded robot (lazy or immediate init)
        self._client = None
        self._pybullet_robot = None
        self._urdf_path = None

        if urdf_path is not None:
            self._init_pybullet(urdf_path)

    def _init_pybullet(self, urdf_path: str) -> None:
        """
        Initialize PyBullet backend by loading the robot URDF.

        Args:
            urdf_path: Path to URDF file.

        Raises:
            FileNotFoundError: If URDF file does not exist.
            RuntimeError: If PyBullet initialization fails.
        """
        from compas_fab.backends import PyBulletClient

        urdf_path = str(Path(urdf_path).resolve())
        if not os.path.exists(urdf_path):
            raise FileNotFoundError(f"URDF file not found: {urdf_path}")

        self._urdf_path = urdf_path

        try:
            self._client = PyBulletClient(connection_type="direct")
            self._client.__enter__()
            self._pybullet_robot = self._client.load_robot(urdf_path)

            logger.info(
                "IK solver initialized with PyBullet backend. "
                "Robot: %s, joints: %s, end-effector: %s",
                self._pybullet_robot.name,
                self._pybullet_robot.get_configurable_joint_names(),
                self.tool_frame,
            )
        except Exception as e:
            self.close()
            raise RuntimeError(
                f"Failed to initialize PyBullet IK backend: {e}"
            ) from e

    def _ensure_backend(self) -> None:
        """Ensure PyBullet backend is initialized."""
        if self._client is None or self._pybullet_robot is None:
            raise RuntimeError(
                "IK solver not initialized with a URDF path. "
                "Pass urdf_path to __init__() or call _init_pybullet()."
            )

    def solve(
        self,
        target_frame: Frame,
        link_name: Optional[str] = None,
        initial_guess: Optional[List[float]] = None,
        max_iterations: int = 100,
        tolerance: float = 1e-3,
        orientation_weight: float = 0.1,
    ) -> Optional[Configuration]:
        """
        Solve inverse kinematics for a target end-effector frame.

        Uses compas_fab PyBulletClient.inverse_kinematics() which delegates
        to PyBullet's calculateInverseKinematics (damped least-squares).

        Args:
            target_frame: Desired end-effector pose as a COMPAS Frame.
            link_name: Target link name. Defaults to self.tool_frame.
            initial_guess: Initial joint configuration (seed). Better seeds
                           produce more reliable solutions. If None, uses
                           the current robot configuration in PyBullet.
            max_iterations: Ignored (kept for API compatibility).
            tolerance: Position tolerance in meters for solution validation.
            orientation_weight: Ignored (kept for API compatibility).

        Returns:
            Configuration if a valid solution is found, None if IK fails
            or the solution exceeds the position tolerance.
        """
        self._ensure_backend()

        ee_link = link_name or self.tool_frame
        pybullet_joint_names = self._pybullet_robot.get_configurable_joint_names()

        # Build seed configuration
        if initial_guess is not None:
            seed_values = list(initial_guess)
            # Pad or truncate to match expected number of joints
            if len(seed_values) < len(pybullet_joint_names):
                seed_values.extend(
                    [0.0] * (len(pybullet_joint_names) - len(seed_values))
                )
            seed_values = seed_values[: len(pybullet_joint_names)]
        else:
            seed_values = [0.0] * len(pybullet_joint_names)

        seed = Configuration.from_revolute_values(seed_values, pybullet_joint_names)

        # Call compas_fab IK (returns a generator)
        try:
            ik_generator = self._client.inverse_kinematics(
                self._pybullet_robot,
                target_frame,
                start_configuration=seed,
                options={"link": ee_link},
            )
            result = next(ik_generator, None)
        except StopIteration:
            return None
        except Exception as e:
            logger.warning("IK solver error: %s", e)
            return None

        if result is None:
            return None

        # Unpack result: (joint_values_tuple, joint_names_list)
        # PyBullet may return extra values for mimic joints
        ik_values_raw, ik_names = result
        n_configurable = len(ik_names)
        ik_values = list(ik_values_raw[:n_configurable])

        # Validate solution by computing FK and checking position error
        ik_config = Configuration.from_revolute_values(ik_values, ik_names)
        try:
            fk_frame = self._pybullet_robot.forward_kinematics(
                ik_config, options={"link": ee_link}
            )
            pos_error = np.linalg.norm(
                np.array(fk_frame.point) - np.array(target_frame.point)
            )

            if pos_error > tolerance:
                logger.debug(
                    "IK solution rejected: position error %.4f m > tolerance %.4f m",
                    pos_error,
                    tolerance,
                )
                return None
        except Exception as e:
            logger.warning("FK validation failed: %s", e)
            # Return the solution anyway if FK validation fails
            pass

        # Map back to the original robot model's joint names
        config = Configuration.from_revolute_values(
            ik_values[: self.n_joints], self.joint_names[: len(ik_values)]
        )
        return config

    def solve_multiple(
        self,
        target_frame: Frame,
        link_name: Optional[str] = None,
        n_solutions: int = 8,
        max_iterations: int = 50,
        home_position: Optional[List[float]] = None,
    ) -> List[Configuration]:
        """
        Find multiple IK solutions by trying different random seeds.

        PyBullet's numerical IK converges to different solutions depending
        on the initial seed configuration. This method tries multiple random
        seeds within joint limits to find diverse solutions.

        Args:
            target_frame: Desired end-effector pose
            link_name: Target link name
            n_solutions: Maximum number of solutions to attempt finding
            max_iterations: Ignored (kept for API compatibility)
            home_position: Optional home joint configuration (radians) to use
                           as the first IK seed. Provides predictable solutions
                           for sim-to-reality workflows.

        Returns:
            List of valid configurations (may be fewer than n_solutions)
        """
        self._ensure_backend()

        solutions = []
        seen_positions = []  # Track position hashes to avoid duplicates

        # Get joint limits for random seed generation
        joint_limits = []
        for joint in self.joints:
            if joint.limit:
                joint_limits.append((joint.limit.lower, joint.limit.upper))
            else:
                joint_limits.append((-np.pi, np.pi))

        # Try home position seed first (if provided), then zero seed
        first_seed = home_position if home_position else None
        result = self.solve(target_frame, link_name=link_name, initial_guess=first_seed)
        if result is not None:
            solutions.append(result)
            seen_positions.append(tuple(round(v, 3) for v in result.joint_values))

        # Try random seeds
        rng = np.random.default_rng(42)
        attempts = n_solutions * 4  # Allow extra attempts

        for _ in range(attempts):
            if len(solutions) >= n_solutions:
                break

            # Random seed within joint limits
            seed = [
                float(rng.uniform(lo, hi))
                for lo, hi in joint_limits
            ]

            result = self.solve(
                target_frame, link_name=link_name, initial_guess=seed
            )
            if result is None:
                continue

            # Check if this is a distinct solution
            rounded = tuple(round(v, 3) for v in result.joint_values)
            is_duplicate = False
            for existing in seen_positions:
                if all(abs(a - b) < 0.05 for a, b in zip(rounded, existing)):
                    is_duplicate = True
                    break

            if not is_duplicate:
                solutions.append(result)
                seen_positions.append(rounded)

        return solutions

    def close(self) -> None:
        """Disconnect PyBullet client and release resources."""
        if self._client is not None:
            try:
                self._client.__exit__(None, None, None)
            except Exception:
                pass
            self._client = None
            self._pybullet_robot = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

    def __del__(self):
        """Destructor — clean up PyBullet connection."""
        self.close()
