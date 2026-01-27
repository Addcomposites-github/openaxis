"""
Base classes for manufacturing process plugins.

This module defines the plugin architecture for different manufacturing
processes (WAAM, pellet extrusion, milling, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from compas.geometry import Frame
from compas_robots import Configuration

from openaxis.slicing.toolpath import Toolpath


class ProcessType(Enum):
    """Types of manufacturing processes."""

    ADDITIVE = "additive"  # Material deposition
    SUBTRACTIVE = "subtractive"  # Material removal
    HYBRID = "hybrid"  # Both additive and subtractive


@dataclass
class ProcessParameters:
    """
    Base class for process-specific parameters.

    Each process plugin should define its own parameters class
    inheriting from this base.
    """

    process_name: str
    process_type: ProcessType
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProcessPlugin(ABC):
    """
    Abstract base class for manufacturing process plugins.

    Each specific process (WAAM, pellet extrusion, milling, etc.)
    should implement this interface.
    """

    def __init__(self, parameters: ProcessParameters):
        """
        Initialize process plugin.

        Args:
            parameters: Process-specific parameters
        """
        self.parameters = parameters

    @abstractmethod
    def validate_parameters(self) -> bool:
        """
        Validate process parameters.

        Returns:
            True if parameters are valid, False otherwise
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def get_process_frame(self, position: tuple) -> Frame:
        """
        Get the tool frame for a given position.

        Args:
            position: (x, y, z) position

        Returns:
            Tool frame at that position
        """
        pass

    @abstractmethod
    def estimate_cycle_time(self, toolpath: Toolpath) -> float:
        """
        Estimate total cycle time for the process.

        Args:
            toolpath: Manufacturing toolpath

        Returns:
            Estimated time in seconds
        """
        pass

    def pre_process(self) -> None:
        """
        Pre-process operations (e.g., homing, warmup).

        Override in subclasses if needed.
        """
        pass

    def post_process(self) -> None:
        """
        Post-process operations (e.g., cooling, cleanup).

        Override in subclasses if needed.
        """
        pass

    def __str__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}({self.parameters.process_name})"
