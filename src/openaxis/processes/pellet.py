"""
Pellet extrusion process plugin.

This module implements pellet-based extrusion for thermoplastic materials.
Common for large-format FDM printing and composite manufacturing.
"""

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from compas.geometry import Frame, Point, Vector
from compas_robots import Configuration

from openaxis.processes.base import ProcessParameters, ProcessPlugin, ProcessType
from openaxis.slicing.toolpath import Toolpath, ToolpathType


@dataclass
class PelletExtrusionParameters(ProcessParameters):
    """
    Parameters for pellet extrusion process.

    Attributes:
        nozzle_diameter: Extrusion nozzle diameter (mm)
        layer_height: Layer height (mm)
        extrusion_temperature: Material temperature (°C)
        bed_temperature: Build plate temperature (°C)
        extrusion_rate: Material flow rate (mm³/s)
        print_speed: Printing speed (mm/s)
        travel_speed: Non-printing move speed (mm/s)
        retraction_distance: Filament retraction distance (mm)
        retraction_speed: Retraction speed (mm/s)
        z_hop: Z-hop height for travel moves (mm)
        cooling_fan_speed: Cooling fan speed (0-100%)
    """

    nozzle_diameter: float = 2.0  # Larger for pellet extrusion
    layer_height: float = 1.0
    extrusion_temperature: float = 220.0
    bed_temperature: float = 60.0
    extrusion_rate: float = 10.0
    print_speed: float = 30.0  # Slower for large extrusion
    travel_speed: float = 100.0
    retraction_distance: float = 5.0
    retraction_speed: float = 40.0
    z_hop: float = 1.0
    cooling_fan_speed: float = 50.0

    def __post_init__(self):
        """Set default process type."""
        self.process_type = ProcessType.ADDITIVE
        if not self.process_name:
            self.process_name = "PelletExtrusion"


class PelletExtrusionProcess(ProcessPlugin):
    """
    Pellet extrusion manufacturing process.

    Implements toolpath-to-robot conversion for pellet-based
    additive manufacturing.
    """

    def __init__(self, parameters: Optional[PelletExtrusionParameters] = None):
        """
        Initialize pellet extrusion process.

        Args:
            parameters: Process parameters (uses defaults if None)
        """
        if parameters is None:
            parameters = PelletExtrusionParameters()

        super().__init__(parameters)
        self.params: PelletExtrusionParameters = parameters

    def validate_parameters(self) -> bool:
        """
        Validate process parameters.

        Returns:
            True if parameters are valid
        """
        # Check temperature ranges
        if not (150 <= self.params.extrusion_temperature <= 400):
            return False

        if not (0 <= self.params.bed_temperature <= 150):
            return False

        # Check geometric parameters
        if self.params.nozzle_diameter <= 0:
            return False

        if self.params.layer_height <= 0:
            return False

        if self.params.layer_height > self.params.nozzle_diameter:
            # Layer height typically should be < nozzle diameter
            return False

        # Check speeds
        if self.params.print_speed <= 0 or self.params.travel_speed <= 0:
            return False

        return True

    def generate_robot_program(
        self,
        toolpath: Toolpath,
    ) -> List[Configuration]:
        """
        Convert toolpath to robot configurations.

        This is a placeholder - actual implementation would use
        IK solver to convert Cartesian positions to joint configurations.

        Args:
            toolpath: Manufacturing toolpath

        Returns:
            List of robot configurations
        """
        # TODO: Integrate with IK solver
        # For now, return empty list
        # In full implementation:
        # 1. For each toolpath segment
        # 2. Get tool frames from segment points
        # 3. Solve IK for each frame
        # 4. Add process-specific parameters (extrusion, speed, etc.)

        configurations = []
        return configurations

    def get_process_frame(self, position: tuple) -> Frame:
        """
        Get the tool frame for pellet extrusion at a position.

        The tool frame has:
        - Origin at the nozzle tip
        - Z-axis pointing down (extrusion direction)
        - X-axis tangent to the path

        Args:
            position: (x, y, z) position in mm

        Returns:
            Tool frame
        """
        # Create frame with Z pointing down
        origin = Point(*position)
        # Z-axis points down for extrusion
        z_axis = Vector(0, 0, -1)
        # X-axis points forward (will be adjusted based on path direction)
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

        # Warmup time
        total_time += 60.0 * 5  # 5 minutes for heating

        # Process each segment
        for segment in toolpath.segments:
            length = segment.get_length()

            if segment.type == ToolpathType.TRAVEL:
                # Travel move
                time = length / self.params.travel_speed
            else:
                # Printing move
                time = length / segment.speed

            total_time += time

        # Cooldown time
        total_time += 60.0 * 10  # 10 minutes for cooling

        return total_time

    def pre_process(self) -> None:
        """
        Pre-process operations for pellet extrusion.

        Includes:
        - Heating nozzle to extrusion temperature
        - Heating bed to bed temperature
        - Priming extruder
        """
        print(f"Heating nozzle to {self.params.extrusion_temperature}°C...")
        print(f"Heating bed to {self.params.bed_temperature}°C...")
        print("Priming extruder...")

    def post_process(self) -> None:
        """
        Post-process operations.

        Includes:
        - Cooling nozzle
        - Cooling bed
        - Retracting material
        """
        print("Retracting material...")
        print("Cooling nozzle...")
        print("Cooling bed...")

    def calculate_extrusion_amount(self, distance: float, width: float) -> float:
        """
        Calculate extrusion amount for a given distance.

        Args:
            distance: Movement distance (mm)
            width: Extrusion width (mm)

        Returns:
            Extrusion amount in mm³
        """
        # Volume = cross-sectional area * length
        # Assuming roughly rectangular cross-section
        area = width * self.params.layer_height
        volume = area * distance

        return volume

    def get_print_parameters(self, segment_type: ToolpathType) -> dict:
        """
        Get process parameters for a segment type.

        Args:
            segment_type: Type of toolpath segment

        Returns:
            Dictionary of process parameters
        """
        if segment_type == ToolpathType.PERIMETER:
            return {
                "speed": self.params.print_speed * 0.8,  # Slower for perimeters
                "extrusion_rate": self.params.extrusion_rate,
                "cooling": self.params.cooling_fan_speed,
            }
        elif segment_type == ToolpathType.INFILL:
            return {
                "speed": self.params.print_speed * 1.2,  # Faster for infill
                "extrusion_rate": self.params.extrusion_rate * 1.1,
                "cooling": self.params.cooling_fan_speed * 0.8,
            }
        else:  # Travel
            return {
                "speed": self.params.travel_speed,
                "extrusion_rate": 0.0,
                "cooling": self.params.cooling_fan_speed,
            }
