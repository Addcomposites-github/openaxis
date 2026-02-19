"""
External axes support for robotic systems.

This module provides support for external axes including:
- Positioners (turntables, tilt-rotate tables)
- Linear tracks (rail-mounted robots)
- Coordinated motion between robot and external axes
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import numpy as np
from compas.geometry import Frame, Transformation


class ExternalAxisType(Enum):
    """Types of external axes."""

    ROTARY = "rotary"  # Single rotation axis (turntable)
    LINEAR = "linear"  # Linear track
    TILT_ROTATE = "tilt_rotate"  # 2-axis positioner
    CUSTOM = "custom"


@dataclass
class ExternalAxis:
    """
    Represents an external axis (positioner or linear track).

    Attributes:
        name: Axis name/identifier
        axis_type: Type of external axis
        min_limit: Minimum position (degrees or mm)
        max_limit: Maximum position (degrees or mm)
        max_velocity: Maximum velocity (deg/s or mm/s)
        max_acceleration: Maximum acceleration
        home_position: Home position value
    """

    name: str
    axis_type: ExternalAxisType
    min_limit: float
    max_limit: float
    max_velocity: float = 90.0  # deg/s or mm/s
    max_acceleration: float = 180.0
    home_position: float = 0.0


@dataclass
class PositionerConfig:
    """
    Configuration for a positioner (turntable or tilt-rotate).

    Attributes:
        axes: List of external axes (1 for turntable, 2 for tilt-rotate)
        base_frame: Positioner base frame relative to world
        tool_mounting_frame: Frame where part is mounted
    """

    axes: List[ExternalAxis]
    base_frame: Frame
    tool_mounting_frame: Frame


class ExternalAxesController:
    """
    Coordinates motion between robot and external axes.

    This controller handles:
    - Computing external axis positions for a given robot pose
    - Synchronizing robot and positioner motion
    - Optimizing axis usage for reachability
    """

    def __init__(self, positioner: Optional[PositionerConfig] = None):
        """
        Initialize external axes controller.

        Args:
            positioner: Positioner configuration (if present)
        """
        self.positioner = positioner

    def compute_positioner_angles(
        self, target_frame: Frame, prefer_rotation: bool = True
    ) -> Optional[List[float]]:
        """
        Compute positioner angles to orient the part.

        .. warning::
            **NON-FUNCTIONAL STUB** — Always returns ``[0.0]`` for rotary axes.
            No actual transformation computation is performed. A real
            implementation would solve for the axis angles that align the
            workpiece ``target_frame`` with the robot's reachable workspace.

        Args:
            target_frame: Desired part orientation
            prefer_rotation: Prefer using rotation over robot reorientation

        Returns:
            List of axis values, or None if not achievable
        """
        if not self.positioner:
            return None

        raise NotImplementedError(
            "External axis computation not yet implemented. "
            "Requires compas_fab coordinated motion planning with external axes. "
            "See: https://gramaziokohler.github.io/compas_fab/"
        )

    def is_within_limits(self, axis_values: List[float]) -> bool:
        """
        Check if axis values are within limits.

        Args:
            axis_values: Values for each axis

        Returns:
            True if all values are within limits
        """
        if not self.positioner:
            return True

        for value, axis in zip(axis_values, self.positioner.axes):
            if value < axis.min_limit or value > axis.max_limit:
                return False

        return True

    def get_workpiece_frame(self, axis_values: List[float]) -> Frame:
        """
        Get workpiece frame given external axis positions.

        Args:
            axis_values: Current axis positions

        Returns:
            Workpiece frame in world coordinates
        """
        if not self.positioner or not axis_values:
            return self.positioner.tool_mounting_frame if self.positioner else Frame.worldXY()

        # Start with tool mounting frame
        frame = self.positioner.tool_mounting_frame

        # Apply transformations for each axis
        for value, axis in zip(axis_values, self.positioner.axes):
            if axis.axis_type == ExternalAxisType.ROTARY:
                # Rotation around Z-axis (typical for turntable)
                rotation = Transformation.from_axis_and_angle(
                    axis=[0, 0, 1],
                    angle=np.radians(value),
                    point=frame.point,
                )
                frame = frame.transformed(rotation)

            elif axis.axis_type == ExternalAxisType.LINEAR:
                # Translation along X-axis (typical for linear track)
                translation = Transformation.from_translation([value, 0, 0])
                frame = frame.transformed(translation)

        return frame

    def optimize_axis_position(
        self,
        robot_base_frame: Frame,
        target_frames: List[Frame],
    ) -> Optional[List[float]]:
        """
        Optimize external axis position to maximize robot reachability.

        .. warning::
            **NON-FUNCTIONAL STUB** — Always returns the midpoint of each
            axis's range. No actual reachability analysis is performed.
            A real implementation would evaluate IK feasibility across
            ``target_frames`` for candidate axis positions and choose the
            configuration that maximises the number of reachable targets.

        Args:
            robot_base_frame: Robot base frame
            target_frames: List of target frames the robot needs to reach

        Returns:
            Optimal axis positions, or None if no solution
        """
        if not self.positioner:
            return None

        raise NotImplementedError(
            "External axis optimization not yet implemented. "
            "Requires IK feasibility analysis across target frames for "
            "candidate axis positions. Needs compas_fab IK backend first."
        )


def create_turntable(
    diameter: float = 1000.0,
    max_rotation: float = 360.0,
    position: tuple = (0, 0, 0),
) -> PositionerConfig:
    """
    Create a simple turntable positioner configuration.

    Args:
        diameter: Table diameter (mm)
        max_rotation: Maximum rotation range (degrees)
        position: Turntable position (x, y, z) in mm

    Returns:
        Positioner configuration
    """
    rotary_axis = ExternalAxis(
        name="turntable",
        axis_type=ExternalAxisType.ROTARY,
        min_limit=-max_rotation / 2,
        max_limit=max_rotation / 2,
        max_velocity=30.0,  # deg/s
        max_acceleration=60.0,
        home_position=0.0,
    )

    base_frame = Frame(position, [1, 0, 0], [0, 1, 0])
    tool_mounting_frame = Frame([0, 0, 0], [1, 0, 0], [0, 1, 0])

    return PositionerConfig(
        axes=[rotary_axis],
        base_frame=base_frame,
        tool_mounting_frame=tool_mounting_frame,
    )


def create_linear_track(
    length: float = 3000.0,
    position: tuple = (0, 0, 0),
) -> PositionerConfig:
    """
    Create a linear track configuration.

    Args:
        length: Track length (mm)
        position: Track start position (x, y, z)

    Returns:
        Positioner configuration
    """
    linear_axis = ExternalAxis(
        name="linear_track",
        axis_type=ExternalAxisType.LINEAR,
        min_limit=0.0,
        max_limit=length,
        max_velocity=500.0,  # mm/s
        max_acceleration=1000.0,
        home_position=length / 2,  # Middle of track
    )

    base_frame = Frame(position, [1, 0, 0], [0, 1, 0])
    tool_mounting_frame = Frame([0, 0, 0], [1, 0, 0], [0, 1, 0])

    return PositionerConfig(
        axes=[linear_axis],
        base_frame=base_frame,
        tool_mounting_frame=tool_mounting_frame,
    )
