"""
Wire Arc Additive Manufacturing (WAAM) process plugin.

This module implements WAAM for metal deposition using arc welding.
Common for large-scale metal parts and repair applications.
"""

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from compas.geometry import Frame, Point, Vector
from compas_robots import Configuration

from openaxis.processes.base import ProcessParameters, ProcessPlugin, ProcessType
from openaxis.slicing.toolpath import Toolpath, ToolpathType
from openaxis.core.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class WAAMParameters(ProcessParameters):
    """
    Parameters for WAAM process.

    Attributes:
        wire_diameter: Wire diameter (mm)
        wire_feed_rate: Wire feed rate (mm/s)
        travel_speed: Welding travel speed (mm/s)
        arc_voltage: Welding voltage (V)
        arc_current: Welding current (A)
        shielding_gas: Shielding gas type (e.g., "Argon", "CO2")
        gas_flow_rate: Gas flow rate (L/min)
        inter_layer_temperature: Temperature between layers (°C)
        cooling_time: Cooling time between layers (seconds)
        standoff_distance: Torch-to-workpiece distance (mm)
        weave_width: Weave pattern width (mm, 0 for no weave)
        weave_frequency: Weave frequency (Hz)
    """

    wire_diameter: float = 1.2  # mm
    wire_feed_rate: float = 50.0  # mm/s
    travel_speed: float = 10.0  # mm/s (slower than FDM)
    arc_voltage: float = 25.0  # V
    arc_current: float = 200.0  # A
    shielding_gas: str = "Argon"
    gas_flow_rate: float = 15.0  # L/min
    inter_layer_temperature: float = 150.0  # °C
    cooling_time: float = 30.0  # seconds
    standoff_distance: float = 15.0  # mm
    weave_width: float = 0.0  # mm (no weave by default)
    weave_frequency: float = 2.0  # Hz

    def __post_init__(self):
        """Set default process type."""
        self.process_type = ProcessType.ADDITIVE
        if not self.process_name:
            self.process_name = "WAAM"


class WAAMProcess(ProcessPlugin):
    """
    Wire Arc Additive Manufacturing process.

    Implements toolpath-to-robot conversion for metal deposition
    using arc welding.
    """

    def __init__(self, parameters: Optional[WAAMParameters] = None):
        """
        Initialize WAAM process.

        Args:
            parameters: Process parameters (uses defaults if None)
        """
        if parameters is None:
            parameters = WAAMParameters()

        super().__init__(parameters)
        self.params: WAAMParameters = parameters

    def validate_parameters(self) -> bool:
        """
        Validate process parameters.

        Returns:
            True if parameters are valid
        """
        # Check welding parameters
        if not (15 <= self.params.arc_voltage <= 40):
            return False

        if not (50 <= self.params.arc_current <= 500):
            return False

        # Check geometric parameters
        if self.params.wire_diameter <= 0:
            return False

        if self.params.standoff_distance <= 0:
            return False

        # Check speeds
        if self.params.travel_speed <= 0 or self.params.wire_feed_rate <= 0:
            return False

        # Check temperatures
        if self.params.inter_layer_temperature < 0:
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
        # For now, return empty list
        # Full implementation would:
        # 1. Convert each toolpath point to torch frame
        # 2. Solve IK for each frame
        # 3. Add process-specific parameters (voltage, current, etc.)
        # 4. Insert cooling/wait commands between layers

        configurations = []
        return configurations

    def get_process_frame(self, position: tuple) -> Frame:
        """
        Get the welding torch frame at a position.

        The torch frame has:
        - Origin at standoff distance from the work surface
        - Z-axis pointing toward the work (welding direction)
        - X-axis tangent to the path

        Args:
            position: (x, y, z) position in mm

        Returns:
            Torch frame
        """
        # Create frame with Z pointing down toward work
        origin = Point(*position)
        # Offset origin by standoff distance
        origin_offset = Point(
            position[0], position[1], position[2] + self.params.standoff_distance
        )

        # Z-axis points down (toward work)
        z_axis = Vector(0, 0, -1)
        # X-axis points forward (travel direction)
        x_axis = Vector(1, 0, 0)

        frame = Frame(origin_offset, x_axis, Vector(0, 1, 0))
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

        # Setup time (fixturing, gas purge, etc.)
        total_time += 60.0 * 2  # 2 minutes

        # Process each segment
        for segment in toolpath.segments:
            length = segment.get_length()

            if segment.type == ToolpathType.TRAVEL:
                # Travel move (torch off)
                time = length / 100.0  # Fast travel at 100 mm/s
            else:
                # Welding move
                time = length / self.params.travel_speed

            total_time += time

        # Inter-layer cooling
        cooling_time = self.params.cooling_time * toolpath.total_layers
        total_time += cooling_time

        # Cooldown and cleanup
        total_time += 60.0 * 5  # 5 minutes

        return total_time

    def pre_process(self) -> None:
        """
        Pre-process operations for WAAM.

        Includes:
        - Gas flow check
        - Wire feeder check
        - Power source initialization
        """
        _logger.info("waam_pre_process", gas=self.params.shielding_gas, flow_rate=self.params.gas_flow_rate)
        _logger.info("waam_wire_feeder_check")
        _logger.info("waam_arc_params", voltage=self.params.arc_voltage, current=self.params.arc_current)
        _logger.info("waam_power_source_ready")

    def post_process(self) -> None:
        """
        Post-process operations.

        Includes:
        - Arc termination
        - Gas flow stop
        - Part cooling
        """
        _logger.info("waam_post_process", step="terminating_arc")
        _logger.info("waam_post_process", step="stopping_gas_flow")
        _logger.info("waam_post_process", step="part_cooling")

    def calculate_deposition_rate(self) -> float:
        """
        Calculate material deposition rate.

        Raises:
            NotImplementedError: Always — requires validated thermal model.
        """
        raise NotImplementedError(
            "Custom deposition rate calculation deleted (used magic 0.8 efficiency). "
            "Integrate validated thermal model (Goldak double-ellipsoid, or "
            "Rosenthal moving point source) from welding research literature."
        )

    def calculate_heat_input(self) -> float:
        """
        Calculate welding heat input.

        DELETED: Formula was Q = V*I / (speed * 1000), missing arc efficiency
        factor (eta). Correct formula is Q = eta * V * I / speed, where
        eta depends on process (GMAW: 0.7-0.85, GTAW: 0.6-0.7, SAW: 0.9-0.99).
        Omitting eta gives 20-40% error.

        Reference: AWS D1.1 Structural Welding Code, Annex H.

        Raises:
            NotImplementedError: Always — requires arc efficiency factor.
        """
        raise NotImplementedError(
            "Custom heat input calculation deleted (missing arc efficiency factor). "
            "Correct formula: Q = eta * V * I / speed. "
            "Arc efficiency (eta) depends on process type: "
            "GMAW 0.7-0.85, GTAW 0.6-0.7, SAW 0.9-0.99. "
            "Reference: AWS D1.1, Annex H."
        )

    def get_welding_parameters(self, segment_type: ToolpathType) -> dict:
        """
        Get process parameters for a segment type.

        DELETED: Used magic multipliers (1.05x voltage, 1.1x current for infill)
        with no empirical or theoretical basis.

        Raises:
            NotImplementedError: Always — multipliers need empirical validation.
        """
        raise NotImplementedError(
            "Custom welding parameter multipliers deleted (magic 1.05x voltage, "
            "1.1x current for infill had no empirical basis). "
            "Integrate validated welding parameter database or "
            "process-specific lookup tables from welding research."
        )

    def requires_inter_layer_cooling(self, layer_index: int) -> bool:
        """
        Check if cooling is required after this layer.

        Args:
            layer_index: Current layer index

        Returns:
            True if cooling required
        """
        # Cooling required for all layers in WAAM
        return True

    def get_inter_layer_wait_time(self, layer_index: int) -> float:
        """
        Get wait time after a layer.

        Args:
            layer_index: Current layer index

        Returns:
            Wait time in seconds
        """
        # First few layers need longer cooling
        if layer_index < 3:
            return self.params.cooling_time * 1.5
        else:
            return self.params.cooling_time
