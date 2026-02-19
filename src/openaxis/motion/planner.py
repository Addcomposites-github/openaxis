"""
Motion planning for robotic manipulators.

This module provides path planning capabilities. CartesianPlanner and
JointPlanner are retained as data-flow wrappers that will delegate to
compas_fab planning backends once IK is integrated.

DELETED: TrajectoryOptimizer.smooth_trajectory() — averaged joint angles
across a moving window. Joint angle averaging breaks at wrap boundaries
(170deg -> -170deg averages to 0deg). This is mathematically wrong and
dangerous for real robots.

DELETED: TrajectoryOptimizer.time_parameterize() — divided distance by
max_velocity without considering acceleration limits, jerk, or dynamics.

TODO: Replace trajectory optimization with ruckig or topp-ra library.
- ruckig: Time-optimal trajectory generation with jerk limits
- topp-ra: Time-Optimal Path Parameterization based on Reachability Analysis

Library references:
- compas_fab: https://gramaziokohler.github.io/compas_fab/
- ruckig: https://github.com/pantor/ruckig
- topp-ra: https://github.com/hungpham2511/toppra
"""

from typing import List, Optional, Tuple

import numpy as np
from compas.geometry import Frame, Point, Vector
from compas_robots import Configuration, RobotModel

from openaxis.core.exceptions import RobotError
from openaxis.motion.kinematics import IKSolver


class CartesianPlanner:
    """
    Plans Cartesian (straight-line) paths in workspace.

    Generates a sequence of frames along a straight line from start to goal,
    then solves IK for each waypoint.

    NOTE: This planner depends on IKSolver.solve() which is currently
    not implemented (pending compas_fab integration). Calling plan_linear()
    or plan_circular() will raise NotImplementedError from the IK solver.
    """

    def __init__(self, robot: RobotModel, ik_solver: Optional[IKSolver] = None):
        """
        Initialize Cartesian planner.

        Args:
            robot: Robot model
            ik_solver: IK solver (creates default if None)
        """
        self.robot = robot
        self.ik_solver = ik_solver or IKSolver(robot)

    def plan_linear(
        self,
        start_frame: Frame,
        goal_frame: Frame,
        resolution: float = 0.01,
        link_name: Optional[str] = None,
    ) -> Optional[List[Configuration]]:
        """
        Plan a straight-line Cartesian path.

        NOTE: Will raise NotImplementedError until IK solver is integrated
        with compas_fab backend.

        Args:
            start_frame: Starting end-effector pose
            goal_frame: Goal end-effector pose
            resolution: Step size in meters
            link_name: Target link name

        Returns:
            List of configurations along the path, or None if IK fails
        """
        # Import here to avoid import at module level for an unimplemented feature
        from scipy.spatial.transform import Rotation, Slerp

        # Compute path length
        start_pos = np.array(start_frame.point)
        goal_pos = np.array(goal_frame.point)
        distance = np.linalg.norm(goal_pos - start_pos)

        # Number of waypoints
        n_waypoints = max(int(distance / resolution), 2)

        # Build SLERP interpolator for orientation
        R_start = np.array(start_frame.to_transformation().matrix)[:3, :3]
        R_goal = np.array(goal_frame.to_transformation().matrix)[:3, :3]
        key_rotations = Rotation.from_matrix([R_start, R_goal])
        slerp = Slerp([0.0, 1.0], key_rotations)

        # Interpolate frames
        frames = []
        for i in range(n_waypoints + 1):
            t = i / n_waypoints

            # Linear position interpolation
            pos = start_pos + t * (goal_pos - start_pos)

            # SLERP orientation interpolation (scipy.spatial.transform)
            R_interp = slerp(t).as_matrix()
            xaxis = Vector(*R_interp[:, 0])
            yaxis = Vector(*R_interp[:, 1])
            frame = Frame(Point(*pos), xaxis, yaxis)
            frames.append(frame)

        # Solve IK for each waypoint (will raise NotImplementedError until
        # compas_fab backend is integrated)
        configurations = []
        prev_config = None

        for frame in frames:
            initial_guess = prev_config.joint_values if prev_config else None
            config = self.ik_solver.solve(
                frame, link_name=link_name, initial_guess=initial_guess
            )

            if config is None:
                return None

            configurations.append(config)
            prev_config = config

        return configurations

    def plan_circular(
        self,
        center: Point,
        radius: float,
        start_angle: float,
        end_angle: float,
        normal: Vector,
        resolution: float = 0.01,
        link_name: Optional[str] = None,
    ) -> Optional[List[Configuration]]:
        """
        Plan a circular arc path.

        NOTE: Will raise NotImplementedError until IK solver is integrated.

        Args:
            center: Center point of the circle
            radius: Circle radius
            start_angle: Starting angle (radians)
            end_angle: Ending angle (radians)
            normal: Normal vector to the plane of the circle
            resolution: Step size in meters
            link_name: Target link name

        Returns:
            List of configurations, or None if IK fails
        """
        # Arc length
        angle_span = end_angle - start_angle
        arc_length = abs(angle_span * radius)

        # Number of waypoints
        n_waypoints = max(int(arc_length / resolution), 2)

        # Generate waypoints along the arc
        angles = np.linspace(start_angle, end_angle, n_waypoints + 1)

        # Create perpendicular axes for the circle
        normal_arr = np.array(normal)
        normal_arr = normal_arr / np.linalg.norm(normal_arr)

        # Choose arbitrary perpendicular vector
        if abs(normal_arr[2]) < 0.9:
            perp1 = np.cross(normal_arr, [0, 0, 1])
        else:
            perp1 = np.cross(normal_arr, [1, 0, 0])
        perp1 = perp1 / np.linalg.norm(perp1)

        perp2 = np.cross(normal_arr, perp1)

        # Generate frames
        frames = []
        center_arr = np.array(center)

        for angle in angles:
            pos = center_arr + radius * (np.cos(angle) * perp1 + np.sin(angle) * perp2)
            tangent = -np.sin(angle) * perp1 + np.cos(angle) * perp2
            frame = Frame(Point(*pos), Vector(*tangent), Vector(*normal_arr))
            frames.append(frame)

        # Solve IK for each waypoint (will raise NotImplementedError)
        configurations = []
        prev_config = None

        for frame in frames:
            initial_guess = prev_config.joint_values if prev_config else None
            config = self.ik_solver.solve(
                frame, link_name=link_name, initial_guess=initial_guess
            )

            if config is None:
                return None

            configurations.append(config)
            prev_config = config

        return configurations


class JointPlanner:
    """
    Plans paths in joint space.

    This is simpler than Cartesian planning as it only requires interpolation
    between joint configurations without IK. Uses linear interpolation —
    no custom math, just numpy linspace between joint values.
    """

    def __init__(self, robot: RobotModel):
        """
        Initialize joint-space planner.

        Args:
            robot: Robot model
        """
        self.robot = robot

    def plan_joint_path(
        self,
        start_config: Configuration,
        goal_config: Configuration,
        resolution: float = 0.1,
    ) -> List[Configuration]:
        """
        Plan a joint-space path between two configurations.

        Args:
            start_config: Starting configuration
            goal_config: Goal configuration
            resolution: Step size in radians

        Returns:
            List of configurations along the path
        """
        start_values = np.array(start_config.joint_values)
        goal_values = np.array(goal_config.joint_values)

        diff = goal_values - start_values
        distance = np.linalg.norm(diff)
        n_waypoints = max(int(distance / resolution), 2)

        configurations = []
        for i in range(n_waypoints + 1):
            t = i / n_waypoints
            values = start_values + t * diff
            config = Configuration.from_revolute_values(
                values.tolist(), start_config.joint_names
            )
            configurations.append(config)

        return configurations

    def plan_multi_waypoint(
        self,
        waypoints: List[Configuration],
        resolution: float = 0.1,
    ) -> List[Configuration]:
        """
        Plan a path through multiple waypoints.

        Args:
            waypoints: List of configurations to pass through
            resolution: Step size in radians

        Returns:
            Complete path through all waypoints
        """
        if len(waypoints) < 2:
            return waypoints

        full_path = []
        for i in range(len(waypoints) - 1):
            segment = self.plan_joint_path(
                waypoints[i], waypoints[i + 1], resolution
            )
            if i > 0:
                segment = segment[1:]
            full_path.extend(segment)

        return full_path


class TrajectoryOptimizer:
    """
    Trajectory optimization — deleted.

    DELETED: smooth_trajectory() averaged joint angles across a moving window.
    Joint angle averaging breaks at wrap boundaries (170deg -> -170deg
    averages to 0deg instead of 180deg). This is mathematically wrong and
    dangerous for real robots.

    DELETED: time_parameterize() used distance/max_velocity without
    considering acceleration limits, jerk limits, or dynamic constraints.

    TODO: Integrate a proven trajectory optimization library:
    - ruckig: Time-optimal trajectory with jerk limits (pip install ruckig)
    - topp-ra: Time-Optimal Path Parameterization (pip install toppra)
    """

    @staticmethod
    def time_parameterize(
        configurations: List[Configuration],
        max_velocity: float = 1.0,
        max_acceleration: float = 2.0,
    ) -> List[Tuple[Configuration, float]]:
        """
        Compute time stamps for each configuration.

        Not yet implemented with a proper time-optimal parameterization library.

        Raises:
            NotImplementedError: Always — pending ruckig or topp-ra integration.
        """
        raise NotImplementedError(
            "Custom time parameterization deleted (ignored acceleration limits). "
            "Integrate ruckig or topp-ra for time-optimal trajectory generation."
        )

    @staticmethod
    def smooth_trajectory(
        configurations: List[Configuration], window_size: int = 3
    ) -> List[Configuration]:
        """
        Smooth a trajectory.

        DELETED: Moving average smoothing breaks at joint wrap boundaries
        (170deg -> -170deg averages to 0deg). This is mathematically wrong.

        Raises:
            NotImplementedError: Always — pending ruckig or topp-ra integration.
        """
        raise NotImplementedError(
            "Custom trajectory smoothing deleted (joint angle averaging "
            "breaks at wrap boundaries: 170deg -> -170deg averages to 0deg). "
            "Integrate ruckig or topp-ra for proper trajectory smoothing "
            "that respects joint topology."
        )
