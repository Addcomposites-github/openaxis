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
        print(f"Loading tool T{self.params.tool_offset} (Ø{self.params.tool_diameter}mm)...")
        print(f"Starting spindle at {self.params.spindle_speed:.0f} RPM...")

        if self.params.coolant_enabled:
            print("Coolant ON")

    def post_process(self) -> None:
        """
        Post-process operations.

        Includes:
        - Spindle stop
        - Coolant off
        - Tool change to safe tool
        """
        print("Stopping spindle...")

        if self.params.coolant_enabled:
            print("Coolant OFF")

        print("Returning to tool change position...")

    def calculate_material_removal_rate(self) -> float:
        """
        Calculate material removal rate (MRR).

        Returns:
            MRR in mm³/min
        """
        # MRR = depth_of_cut * stepover * feed_rate
        mrr = (
            self.params.depth_of_cut * self.params.stepover * self.params.feed_rate
        )
        return mrr

    def calculate_cutting_force(self, material_hardness: float = 200.0) -> float:
        """
        Estimate cutting force.

        Args:
            material_hardness: Material hardness (HB)

        Returns:
            Estimated cutting force in Newtons
        """
        # Simplified model: Force proportional to chip cross-section and hardness
        chip_area = self.params.depth_of_cut * self.params.stepover  # mm²
        specific_cutting_force = material_hardness * 3.0  # N/mm²

        force = chip_area * specific_cutting_force
        return force

    def get_machining_parameters(self, segment_type: ToolpathType) -> dict:
        """
        Get process parameters for a segment type.

        Args:
            segment_type: Type of toolpath segment

        Returns:
            Dictionary of machining parameters
        """
        if self.params.strategy == MillingStrategy.ROUGHING:
            # Roughing: high MRR
            return {
                "spindle_rpm": self.params.spindle_speed,
                "feed_rate": self.params.feed_rate,
                "depth_of_cut": self.params.depth_of_cut,
                "stepover": self.params.stepover,
            }
        elif self.params.strategy == MillingStrategy.FINISHING:
            # Finishing: high speed, low DOC
            return {
                "spindle_rpm": self.params.spindle_speed * 1.2,
                "feed_rate": self.params.feed_rate * 0.8,
                "depth_of_cut": self.params.depth_of_cut * 0.3,
                "stepover": self.params.stepover * 0.5,
            }
        else:  # Adaptive or Contour
            return {
                "spindle_rpm": self.params.spindle_speed,
                "feed_rate": self.params.feed_rate * 0.9,
                "depth_of_cut": self.params.depth_of_cut * 0.7,
                "stepover": self.params.stepover * 0.7,
            }

    def requires_tool_change(self) -> bool:
        """
        Check if tool change is required.

        Returns:
            True if tool change needed
        """
        # In a full system, would check:
        # - Tool wear
        # - Tool life
        # - Different operation requirements
        return False

    def calculate_optimal_spindle_speed(
        self, material: str = "aluminum", surface_speed: float = 200.0
    ) -> float:
        """
        Calculate optimal spindle speed for material.

        Args:
            material: Material being cut
            surface_speed: Desired surface speed (m/min)

        Returns:
            Optimal spindle RPM
        """
        # RPM = (Surface Speed * 1000) / (π * Tool Diameter)
        diameter_m = self.params.tool_diameter / 1000.0
        rpm = (surface_speed * 1000) / (np.pi * diameter_m)

        return rpm
