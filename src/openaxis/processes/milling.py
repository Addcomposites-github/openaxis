"""
Milling (subtractive machining) process plugin.

This module implements CNC milling for material removal and
surface finishing operations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import numpy as np
from compas.geometry import Frame, Point, Vector
from compas_robots import Configuration

from openaxis.processes.base import ProcessParameters, ProcessPlugin, ProcessType
from openaxis.slicing.toolpath import Toolpath, ToolpathType
from openaxis.core.logging import get_logger

_logger = get_logger(__name__)


class MillingStrategy(Enum):
    """Milling strategies."""

    ROUGHING = "roughing"  # High material removal
    FINISHING = "finishing"  # Surface quality
    ADAPTIVE = "adaptive"  # Load-controlled
    CONTOUR = "contour"  # Follow contours


class ToolType(Enum):
    """Milling tool types."""

    FLAT_END = "flat_end"  # Flat end mill
    BALL_END = "ball_end"  # Ball end mill
    BULL_NOSE = "bull_nose"  # Radius end mill
    FACE_MILL = "face_mill"  # Face milling cutter
    DRILL = "drill"  # Drill bit


@dataclass
class MillingParameters(ProcessParameters):
    """
    Parameters for milling process.

    Attributes:
        tool_diameter: Tool diameter (mm)
        tool_type: Type of cutting tool
        spindle_speed: Spindle RPM
        feed_rate: Feed rate (mm/min)
        plunge_rate: Plunge feed rate (mm/min)
        depth_of_cut: Depth per pass (mm)
        stepover: Stepover distance (mm or % of tool diameter)
        strategy: Milling strategy
        climb_milling: True for climb milling, False for conventional
        coolant_enabled: Whether coolant is used
        tool_length: Tool length from spindle (mm)
        tool_offset: Tool offset number
    """

    tool_diameter: float = 10.0  # mm
    tool_type: ToolType = ToolType.FLAT_END
    spindle_speed: float = 12000.0  # RPM
    feed_rate: float = 1000.0  # mm/min
    plunge_rate: float = 300.0  # mm/min
    depth_of_cut: float = 1.0  # mm
    stepover: float = 0.5  # mm or fraction
    strategy: MillingStrategy = MillingStrategy.ROUGHING
    climb_milling: bool = True
    coolant_enabled: bool = True
    tool_length: float = 100.0  # mm
    tool_offset: int = 1

    def __post_init__(self):
        """Set default process type."""
        self.process_type = ProcessType.SUBTRACTIVE
        if not self.process_name:
            self.process_name = "Milling"


class MillingProcess(ProcessPlugin):
    """
    CNC milling process for material removal.

    Implements toolpath-to-robot conversion for subtractive
    machining operations.
    """

    def __init__(self, parameters: Optional[MillingParameters] = None):
        """
        Initialize milling process.

        Args:
            parameters: Process parameters (uses defaults if None)
        """
        if parameters is None:
            parameters = MillingParameters()

        super().__init__(parameters)
        self.params: MillingParameters = parameters

    def validate_parameters(self) -> bool:
        """
        Validate process parameters.

        Returns:
            True if parameters are valid
        """
        # Check spindle speed
        if not (0 < self.params.spindle_speed <= 30000):
            return False

        # Check feed rates
        if self.params.feed_rate <= 0 or self.params.plunge_rate <= 0:
            return False

        # Check geometric parameters
        if self.params.tool_diameter <= 0:
            return False

        if self.params.depth_of_cut <= 0:
            return False

        if self.params.depth_of_cut > self.params.tool_diameter:
            # DOC typically should be less than tool diameter
            return False

        return True

    def generate_robot_program(
        self,
        toolpath: Toolpath,
    ) -> List[Configuration]:
        """
        Convert toolpath to robot configurations.

        Args:
            toolpath: Manufacturing toolpath

        Returns:
            List of robot configurations
        """
        # TODO: Integrate with IK solver
        # Full implementation would:
        # 1. Convert toolpath to tool center point frames
        # 2. Apply tool length offset
        # 3. Solve IK for each frame
        # 4. Add spindle control commands
        # 5. Insert tool changes if needed

        configurations = []
        return configurations

    def get_process_frame(self, position: tuple) -> Frame:
        """
        Get the tool frame for milling at a position.

        The tool frame has:
        - Origin at the tool center point (TCP)
        - Z-axis along the tool axis (pointing toward spindle)
        - X-axis perpendicular to Z

        Args:
            position: (x, y, z) position in mm

        Returns:
            Tool frame
        """
        # Create frame with Z pointing up (tool axis)
        origin = Point(*position)

        # Z-axis points up along tool axis
        z_axis = Vector(0, 0, 1)
        # X-axis perpendicular
        x_axis = Vector(1, 0, 0)

        frame = Frame(origin, x_axis, Vector(0, 1, 0))
        return frame

    def estimate_cycle_time(self, toolpath: Toolpath) -> float:
        """
        Estimate total cycle time.

        Args:
            toolpath: Manufacturing toolpath

        Returns:
            Estimated time in seconds
        """
        total_time = 0.0

        # Tool change and spindle start
        total_time += 30.0  # 30 seconds

        # Process each segment
        for segment in toolpath.segments:
            length = segment.get_length()

            if segment.type == ToolpathType.TRAVEL:
                # Rapid move (G0)
                time = length / 5000.0  # Rapid at 5000 mm/min
            else:
                # Cutting move
                feed = self.params.feed_rate / 60.0  # Convert to mm/s
                time = length / feed

            total_time += time

        # Spindle stop and tool change
        total_time += 30.0

        return total_time

    def pre_process(self) -> None:
        """
        Pre-process operations for milling.

        Includes:
        - Tool change
        - Spindle start
        - Coolant on
        """
        _logger.info("milling_pre_process", tool_offset=self.params.tool_offset, tool_diameter=self.params.tool_diameter)
        _logger.info("milling_spindle_start", rpm=self.params.spindle_speed)

        if self.params.coolant_enabled:
            _logger.info("milling_coolant", state="on")

    def post_process(self) -> None:
        """
        Post-process operations.

        Includes:
        - Spindle stop
        - Coolant off
        - Tool change to safe tool
        """
        _logger.info("milling_spindle_stop")

        if self.params.coolant_enabled:
            _logger.info("milling_coolant", state="off")

        _logger.info("milling_return_to_tool_change")

    def calculate_material_removal_rate(self) -> float:
        """
        Calculate material removal rate (MRR).

        Raises:
            NotImplementedError: Always — requires validated cutting model.
        """
        raise NotImplementedError(
            "Custom MRR calculation deleted. "
            "Integrate validated cutting force model from machining handbook "
            "(e.g., Altintas 'Manufacturing Automation' or Machining Data Handbook)."
        )

    def calculate_cutting_force(self, material_hardness: float = 200.0) -> float:
        """
        Estimate cutting force.

        DELETED: Used unvalidated model (hardness * 3.0 N/mm²).
        Real specific cutting force (Kc1.1) varies by material, tool geometry,
        and cutting conditions. Published values should be used from:
        - Altintas, Y. (2012) "Manufacturing Automation", Chapter 2
        - Sandvik Coromant Machining Formulas handbook

        Raises:
            NotImplementedError: Always — requires validated cutting force model.
        """
        raise NotImplementedError(
            "Custom cutting force deleted (used unvalidated hardness * 3.0 model). "
            "Use specific cutting force (Kc1.1) from material databases: "
            "Altintas 'Manufacturing Automation' Ch.2 or Sandvik Coromant handbook."
        )

    def get_machining_parameters(self, segment_type: ToolpathType) -> dict:
        """
        Get process parameters for a segment type.

        DELETED: Used magic multipliers (1.2x RPM for finishing, 0.8x feed)
        with no empirical basis.

        Raises:
            NotImplementedError: Always — multipliers need empirical validation.
        """
        raise NotImplementedError(
            "Custom machining parameter multipliers deleted (magic 1.2x, 0.8x "
            "values had no empirical basis). Integrate material-specific "
            "cutting data from machining handbook or CAM system."
        )

    def requires_tool_change(self) -> bool:
        """
        Check if tool change is required.

        Returns:
            True if tool change needed
        """
        # In a full system, would check tool wear, tool life, operation requirements
        return False

    def calculate_optimal_spindle_speed(
        self, material: str = "aluminum", surface_speed: float = 200.0
    ) -> float:
        """
        Calculate optimal spindle speed for material.

        DELETED: The formula RPM = Vc * 1000 / (pi * D) is standard
        (from any machining handbook) BUT the 'material' parameter was
        ignored — surface_speed was always the caller's input.
        Without a material-specific surface speed database, this is misleading.

        Raises:
            NotImplementedError: Always — needs material database.
        """
        raise NotImplementedError(
            "Custom spindle speed calculation deleted (ignored material parameter, "
            "used caller-supplied surface speed directly). Integrate material-specific "
            "surface speed database from machining handbook."
        )
