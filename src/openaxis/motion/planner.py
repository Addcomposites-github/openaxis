"""
Motion planning for robotic manipulators.

This module provides path and trajectory planning capabilities including
Cartesian paths, joint-space interpolation, and trajectory optimization.
"""

from typing import List, Optional, Tuple

import numpy as np
from compas.geometry import Frame, Point, Vector
from compas_robots import Configuration, RobotModel
from scipy.spatial.transform import Rotation, Slerp

from openaxis.core.exceptions import RobotError
from openaxis.motion.kinematics import IKSolver


class CartesianPlanner:
    """
    Plans Cartesian (straight-line) paths in workspace.

    Generates a sequence of frames along a straight line from start to goal,
    then solves IK for each waypoint.
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

        Args:
            start_frame: Starting end-effector pose
            goal_frame: Goal end-effector pose
            resolution: Step size in meters
            link_name: Target link name

        Returns:
            List of configurations along the path, or None if IK fails
        """
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

        # Solve IK for each waypoint
        configurations = []
        prev_config = None

        for frame in frames:
            # Use previous solution as initial guess
            initial_guess = prev_config.joint_values if prev_config else None

            config = self.ik_solver.solve(
                frame, link_name=link_name, initial_guess=initial_guess
            )

            if config is None:
                # IK failed
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
        normal = np.array(normal)
        normal = normal / np.linalg.norm(normal)

        # Choose arbitrary perpendicular vector
        if abs(normal[2]) < 0.9:
            perp1 = np.cross(normal, [0, 0, 1])
        else:
            perp1 = np.cross(normal, [1, 0, 0])
        perp1 = perp1 / np.linalg.norm(perp1)

        perp2 = np.cross(normal, perp1)

        # Generate frames
        frames = []
        center_arr = np.array(center)

        for angle in angles:
            # Position on circle
            pos = center_arr + radius * (np.cos(angle) * perp1 + np.sin(angle) * perp2)

            # Frame with Z pointing towards center
            tangent = -np.sin(angle) * perp1 + np.cos(angle) * perp2
            frame = Frame(Point(*pos), Vector(*tangent), Vector(*normal))
            frames.append(frame)

        # Solve IK for each waypoint
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
    between joint configurations without IK.
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

        # Compute distance
        diff = goal_values - start_values
        distance = np.linalg.norm(diff)

        # Number of waypoints
        n_waypoints = max(int(distance / resolution), 2)

        # Interpolate
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

        # Plan between each pair of waypoints
        full_path = []
        for i in range(len(waypoints) - 1):
            segment = self.plan_joint_path(
                waypoints[i], waypoints[i + 1], resolution
            )
            # Avoid duplicating waypoints
            if i > 0:
                segment = segment[1:]
            full_path.extend(segment)

        return full_path


class TrajectoryOptimizer:
    """
    Optimizes trajectories for time and smoothness.

    This module applies post-processing to trajectories to make them
    smoother and more efficient.
    """

    @staticmethod
    def time_parameterize(
        configurations: List[Configuration],
        max_velocity: float = 1.0,
        max_acceleration: float = 2.0,
    ) -> List[Tuple[Configuration, float]]:
        """
        Compute time stamps for each configuration.

        Args:
            configurations: Path configurations
            max_velocity: Maximum joint velocity (rad/s)
            max_acceleration: Maximum joint acceleration (rad/s²)

        Returns:
            List of (configuration, time) tuples
        """
        if len(configurations) < 2:
            return [(cfg, 0.0) for cfg in configurations]

        # Compute segment durations
        timestamps = [0.0]

        for i in range(1, len(configurations)):
            prev_values = np.array(configurations[i - 1].joint_values)
            curr_values = np.array(configurations[i].joint_values)

            # Distance in joint space
            distance = np.linalg.norm(curr_values - prev_values)

            # Simple time calculation (could be improved with acceleration limits)
            time = distance / max_velocity
            timestamps.append(timestamps[-1] + time)

        return list(zip(configurations, timestamps))

    @staticmethod
    def smooth_trajectory(
        configurations: List[Configuration], window_size: int = 3
    ) -> List[Configuration]:
        """
        Smooth a trajectory using moving average.

        Args:
            configurations: Input trajectory
            window_size: Smoothing window size (must be odd)

        Returns:
            Smoothed trajectory
        """
        if len(configurations) < window_size:
            return configurations

        # Convert to numpy array
        values = np.array([cfg.joint_values for cfg in configurations])

        # Apply moving average
        smoothed = np.copy(values)
        half_window = window_size // 2

        for i in range(half_window, len(values) - half_window):
            smoothed[i] = np.mean(
                values[i - half_window : i + half_window + 1], axis=0
            )

        # Convert back to configurations
        joint_names = configurations[0].joint_names
        smoothed_configs = [
            Configuration.from_revolute_values(vals.tolist(), joint_names)
            for vals in smoothed
        ]

        return smoothed_configs
