"""
Inverse kinematics solvers for robotic manipulators.

This module provides IK solutions using numerical optimization,
building on the forward kinematics from compas_fab.
"""

from typing import List, Optional, Tuple

import numpy as np
from compas.geometry import Frame, Transformation
from compas_robots import Configuration, RobotModel
from scipy.optimize import minimize, differential_evolution

from openaxis.core.exceptions import RobotError


class IKSolver:
    """
    Inverse kinematics solver using numerical optimization.

    This solver uses scipy's optimization methods to find joint configurations
    that achieve a desired end-effector pose.
    """

    def __init__(
        self,
        robot: RobotModel,
        group: Optional[str] = None,
        method: str = "SLSQP",
    ):
        """
        Initialize IK solver.

        Args:
            robot: Robot model from compas_robots
            group: Planning group name (default: use all joints)
            method: Optimization method ('SLSQP', 'differential_evolution', 'trust-constr')
        """
        self.robot = robot
        self.group = group
        self.method = method

        # Get joint information
        if group:
            # TODO: Get joints for specific group
            self.joints = [j for j in robot.iter_joints() if j.is_configurable()]
        else:
            self.joints = [j for j in robot.iter_joints() if j.is_configurable()]

        self.joint_names = [j.name for j in self.joints]
        self.n_joints = len(self.joints)

        # Extract joint limits
        self.joint_limits = []
        for joint in self.joints:
            if joint.limit:
                lower = joint.limit.lower if joint.limit.lower is not None else -np.pi
                upper = joint.limit.upper if joint.limit.upper is not None else np.pi
                self.joint_limits.append((lower, upper))
            else:
                # Default limits for revolute joints
                self.joint_limits.append((-np.pi, np.pi))

    def solve(
        self,
        target_frame: Frame,
        link_name: Optional[str] = None,
        initial_guess: Optional[List[float]] = None,
        max_iterations: int = 100,
        tolerance: float = 1e-4,
    ) -> Optional[Configuration]:
        """
        Solve inverse kinematics for a target end-effector frame.

        Args:
            target_frame: Desired end-effector pose
            link_name: Target link name (default: end-effector)
            initial_guess: Initial joint configuration
            max_iterations: Maximum optimization iterations
            tolerance: Position/orientation tolerance

        Returns:
            Configuration if solution found, None otherwise
        """
        if link_name is None:
            # Use last link
            links = list(self.robot.iter_links())
            link_name = links[-1].name if links else None

        if link_name is None:
            raise RobotError("No target link specified and robot has no links")

        # Initial guess (zeros or provided)
        if initial_guess is None:
            x0 = np.zeros(self.n_joints)
        else:
            x0 = np.array(initial_guess[: self.n_joints])

        # Objective function: distance to target
        def objective(joint_values):
            # Compute forward kinematics
            config = Configuration.from_revolute_values(joint_values, self.joint_names)

            try:
                # Get end-effector frame
                current_frame = self.robot.forward_kinematics(config, link_name=link_name)

                # Compute position error
                pos_error = np.linalg.norm(
                    np.array(target_frame.point) - np.array(current_frame.point)
                )

                # Compute orientation error (using rotation matrices)
                R_target = np.array(target_frame.to_transformation().matrix[:3, :3])
                R_current = np.array(current_frame.to_transformation().matrix[:3, :3])
                R_error = R_target.T @ R_current
                # Rotation error as trace of difference from identity
                orient_error = np.arccos(np.clip((np.trace(R_error) - 1) / 2, -1, 1))

                # Combined error (weighted)
                error = pos_error + 0.1 * orient_error
                return error

            except Exception:
                # FK failed, return large error
                return 1e6

        # Solve using selected method
        if self.method == "differential_evolution":
            # Global optimization (slower but more robust)
            result = differential_evolution(
                objective,
                bounds=self.joint_limits,
                maxiter=max_iterations,
                atol=tolerance,
                seed=42,
            )
        else:
            # Local optimization (faster)
            result = minimize(
                objective,
                x0,
                method=self.method,
                bounds=self.joint_limits,
                options={"maxiter": max_iterations},
            )

        # Check if solution is good enough
        if result.fun < tolerance * 10:  # Allow some slack
            solution = Configuration.from_revolute_values(
                result.x.tolist(), self.joint_names
            )
            return solution
        else:
            return None

    def solve_multiple(
        self,
        target_frame: Frame,
        link_name: Optional[str] = None,
        n_solutions: int = 5,
        max_iterations: int = 50,
    ) -> List[Configuration]:
        """
        Find multiple IK solutions using different initial guesses.

        Args:
            target_frame: Desired end-effector pose
            link_name: Target link name
            n_solutions: Number of solutions to attempt
            max_iterations: Max iterations per attempt

        Returns:
            List of valid configurations
        """
        solutions = []

        for i in range(n_solutions):
            # Random initial guess within joint limits
            initial_guess = []
            for lower, upper in self.joint_limits:
                initial_guess.append(np.random.uniform(lower, upper))

            # Try to solve
            solution = self.solve(
                target_frame,
                link_name=link_name,
                initial_guess=initial_guess,
                max_iterations=max_iterations,
            )

            if solution is not None:
                # Check if this is a new solution (not duplicate)
                is_duplicate = False
                for existing in solutions:
                    diff = np.array(solution.joint_values) - np.array(
                        existing.joint_values
                    )
                    if np.linalg.norm(diff) < 0.01:  # Very similar
                        is_duplicate = True
                        break

                if not is_duplicate:
                    solutions.append(solution)

        return solutions


class JacobianIKSolver:
    """
    Jacobian-based IK solver using damped least squares.

    This is typically faster than optimization-based methods but may
    get stuck in local minima.
    """

    def __init__(
        self,
        robot: RobotModel,
        group: Optional[str] = None,
        damping: float = 0.01,
    ):
        """
        Initialize Jacobian IK solver.

        Args:
            robot: Robot model
            group: Planning group name
            damping: Damping factor for stability (0.01-0.1)
        """
        self.robot = robot
        self.group = group
        self.damping = damping

        # Get joints
        if group:
            self.joints = [j for j in robot.iter_joints() if j.is_configurable()]
        else:
            self.joints = [j for j in robot.iter_joints() if j.is_configurable()]

        self.joint_names = [j.name for j in self.joints]
        self.n_joints = len(self.joints)

    def compute_jacobian(
        self, configuration: Configuration, link_name: str
    ) -> np.ndarray:
        """
        Compute numerical Jacobian matrix.

        Args:
            configuration: Current joint configuration
            link_name: Target link

        Returns:
            6xN Jacobian matrix (position + orientation)
        """
        jacobian = np.zeros((6, self.n_joints))
        delta = 1e-6

        # Get current end-effector frame
        current_frame = self.robot.forward_kinematics(configuration, link_name=link_name)
        current_pos = np.array(current_frame.point)

        # Numerical differentiation
        for i in range(self.n_joints):
            # Perturb joint i
            perturbed_values = list(configuration.joint_values)
            perturbed_values[i] += delta
            perturbed_config = Configuration.from_revolute_values(
                perturbed_values, self.joint_names
            )

            # Compute perturbed frame
            perturbed_frame = self.robot.forward_kinematics(
                perturbed_config, link_name=link_name
            )
            perturbed_pos = np.array(perturbed_frame.point)

            # Position derivative
            jacobian[:3, i] = (perturbed_pos - current_pos) / delta

            # Orientation derivative (simplified - axis-angle)
            # For now, use position only for stability
            jacobian[3:, i] = 0

        return jacobian

    def solve(
        self,
        target_frame: Frame,
        link_name: Optional[str] = None,
        initial_guess: Optional[List[float]] = None,
        max_iterations: int = 100,
        tolerance: float = 1e-3,
    ) -> Optional[Configuration]:
        """
        Solve IK using Jacobian method.

        Args:
            target_frame: Desired end-effector pose
            link_name: Target link name
            initial_guess: Initial configuration
            max_iterations: Maximum iterations
            tolerance: Convergence tolerance

        Returns:
            Configuration if converged, None otherwise
        """
        if link_name is None:
            links = list(self.robot.iter_links())
            link_name = links[-1].name if links else None

        # Initial configuration
        if initial_guess is None:
            q = np.zeros(self.n_joints)
        else:
            q = np.array(initial_guess[: self.n_joints])

        target_pos = np.array(target_frame.point)

        # Iterative solving
        for iteration in range(max_iterations):
            # Current configuration
            config = Configuration.from_revolute_values(q.tolist(), self.joint_names)

            # Forward kinematics
            current_frame = self.robot.forward_kinematics(config, link_name=link_name)
            current_pos = np.array(current_frame.point)

            # Error
            error = target_pos - current_pos
            error_norm = np.linalg.norm(error)

            if error_norm < tolerance:
                # Converged!
                return config

            # Compute Jacobian
            J = self.compute_jacobian(config, link_name)

            # Use only position part (first 3 rows)
            J_pos = J[:3, :]

            # Damped least squares
            JJT = J_pos @ J_pos.T + self.damping * np.eye(3)
            dq = J_pos.T @ np.linalg.solve(JJT, error)

            # Update joint values
            q = q + dq

        # Did not converge
        return None
