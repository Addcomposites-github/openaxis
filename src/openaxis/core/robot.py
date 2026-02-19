"""
Robot model management for OpenAxis.

Handles robot model loading, URDF parsing, and kinematic chain setup
using COMPAS and compas_fab.
"""

from pathlib import Path
from typing import Any

from compas.geometry import Frame
from compas_fab.robots import Robot as FabRobot
from compas_robots import Configuration, RobotModel

from openaxis.core.config import RobotConfig
from openaxis.core.exceptions import RobotError


class RobotLoader:
    """
    Loads robot models from URDF and configuration files.

    Integrates with compas_fab for robot representation and kinematics.
    """

    @classmethod
    def load_from_urdf(cls, urdf_path: str | Path, **kwargs: Any) -> RobotModel:
        """
        Load robot model from URDF file.

        Args:
            urdf_path: Path to URDF file
            **kwargs: Additional arguments for RobotModel

        Returns:
            compas_fab RobotModel instance

        Raises:
            RobotError: If URDF loading fails
        """
        path = Path(urdf_path)

        if not path.exists():
            raise RobotError(f"URDF file not found: {path}")

        try:
            model = RobotModel.from_urdf_file(str(path))
            return model
        except Exception as e:
            raise RobotError(f"Failed to load URDF from {path}: {e}") from e

    @classmethod
    def load_from_config(cls, config: RobotConfig) -> "RobotInstance":
        """
        Load robot from OpenAxis configuration.

        Args:
            config: RobotConfig object

        Returns:
            RobotInstance with model and configuration

        Raises:
            RobotError: If loading fails
        """
        if not config.urdf_path:
            raise RobotError(
                f"Robot '{config.name}' has no URDF path specified in configuration"
            )

        try:
            model = cls.load_from_urdf(config.urdf_path)
            return RobotInstance(model=model, config=config)
        except Exception as e:
            raise RobotError(
                f"Failed to load robot '{config.name}' from config: {e}"
            ) from e


class RobotInstance:
    """
    Represents a robot instance with model and configuration.

    Combines compas_fab RobotModel with OpenAxis-specific configuration
    and utilities.
    """

    def __init__(self, model: RobotModel, config: RobotConfig) -> None:
        """
        Initialize robot instance.

        Args:
            model: compas_fab RobotModel
            config: OpenAxis RobotConfig
        """
        self.model = model
        self.config = config
        self._robot: FabRobot | None = None

    @property
    def robot(self) -> FabRobot:
        """
        Get compas_fab Robot instance (lazy initialization).

        Returns:
            compas_fab Robot instance
        """
        if self._robot is None:
            self._robot = FabRobot(self.model, semantics=None)
        return self._robot

    @property
    def name(self) -> str:
        """Robot name from configuration."""
        return self.config.name

    @property
    def manufacturer(self) -> str:
        """Robot manufacturer from configuration."""
        return self.config.manufacturer

    @property
    def base_frame(self) -> str:
        """Base frame name from configuration."""
        return self.config.base_frame

    @property
    def tool_frame(self) -> str:
        """Tool frame name from configuration."""
        return self.config.tool_frame

    def get_joint_names(self) -> list[str]:
        """
        Get list of joint names.

        Returns:
            List of joint names in kinematic chain
        """
        return [joint.name for joint in self.model.joints if joint.is_configurable()]

    def get_link_names(self) -> list[str]:
        """
        Get list of link names.

        Returns:
            List of link names
        """
        return [link.name for link in self.model.links]

    def get_joint_limits(self) -> dict[str, tuple[float, float]]:
        """
        Get joint limits from model and configuration.

        Returns:
            Dictionary mapping joint names to (min, max) tuples in radians

        Note:
            Configuration limits override URDF limits if specified
        """
        limits = {}

        # Get limits from URDF
        for joint in self.model.joints:
            if joint.is_configurable() and joint.limit:
                limits[joint.name] = (joint.limit.lower, joint.limit.upper)

        # Override with config limits if specified
        if self.config.joint_limits:
            for joint_name, config_limits in self.config.joint_limits.items():
                if joint_name in limits:
                    limits[joint_name] = (
                        config_limits.get("min", limits[joint_name][0]),
                        config_limits.get("max", limits[joint_name][1]),
                    )

        return limits

    def validate_configuration(self, joint_values: list[float]) -> bool:
        """
        Validate robot configuration against joint limits.

        Args:
            joint_values: List of joint values in radians

        Returns:
            True if configuration is valid, False otherwise
        """
        joint_names = self.get_joint_names()
        limits = self.get_joint_limits()

        if len(joint_values) != len(joint_names):
            return False

        for name, value in zip(joint_names, joint_values):
            if name in limits:
                min_limit, max_limit = limits[name]
                if not (min_limit <= value <= max_limit):
                    return False

        return True

    def __repr__(self) -> str:
        """String representation of robot instance."""
        return (
            f"RobotInstance(name='{self.name}', "
            f"manufacturer='{self.manufacturer}', "
            f"joints={len(self.get_joint_names())})"
        )


class KinematicsEngine:
    """
    Kinematics computation engine.

    Provides forward and inverse kinematics using compas_fab backends.
    """

    def __init__(self, robot: RobotInstance) -> None:
        """
        Initialize kinematics engine.

        Args:
            robot: RobotInstance to compute kinematics for
        """
        self.robot = robot

    def forward_kinematics(
        self,
        joint_values: list[float],
        link_name: str | None = None,
    ) -> Frame:
        """
        Compute forward kinematics.

        Args:
            joint_values: Joint configuration in radians
            link_name: Link to compute FK for (default: tool frame)

        Returns:
            Frame representing the pose of the specified link

        Raises:
            RobotError: If FK computation fails
        """
        if not self.robot.validate_configuration(joint_values):
            raise RobotError("Invalid joint configuration: out of limits")

        try:
            if link_name is None:
                link_name = self.robot.tool_frame

            # Create configuration
            joint_names = self.robot.get_joint_names()
            config = Configuration.from_revolute_values(joint_values, joint_names)

            # Compute FK
            frame = self.robot.robot.forward_kinematics(config, link_name=link_name)

            return frame

        except Exception as e:
            raise RobotError(f"Forward kinematics failed: {e}") from e

    def inverse_kinematics(
        self,
        target_frame: Frame,
        start_configuration: list[float] | None = None,
        group: str | None = None,
    ) -> list[float] | None:
        """
        Compute inverse kinematics using compas_fab PyBulletClient backend.

        Args:
            target_frame: Target pose as COMPAS Frame
            start_configuration: Starting joint configuration (seed)
            group: Planning group name (optional)

        Returns:
            Joint configuration achieving target pose, or None if not found

        Raises:
            RobotError: If IK computation fails or URDF path is not configured
        """
        from openaxis.motion.kinematics import IKSolver

        urdf_path = self.robot.config.urdf_path
        if not urdf_path:
            raise RobotError(
                "Cannot compute IK: robot config has no urdf_path. "
                "Set urdf_path in RobotConfig to enable IK solving."
            )

        try:
            with IKSolver(
                self.robot.model, urdf_path=urdf_path, tool_frame="link_6"
            ) as solver:
                config = solver.solve(
                    target_frame, initial_guess=start_configuration
                )
                if config is not None:
                    return list(config.joint_values)
                return None
        except Exception as e:
            raise RobotError(f"Inverse kinematics failed: {e}") from e

    def check_collision(self, joint_values: list[float]) -> bool:
        """
        Check for self-collision at given configuration (requires backend).

        Note:
            This is a placeholder for collision checking integration.

        Args:
            joint_values: Joint configuration to check

        Returns:
            True if collision detected, False otherwise

        Raises:
            NotImplementedError: If no backend is configured
        """
        # TODO: Integrate with collision checking backend in Phase 2
        raise NotImplementedError(
            "Collision checking requires backend integration. "
            "This will be implemented in Phase 2."
        )
