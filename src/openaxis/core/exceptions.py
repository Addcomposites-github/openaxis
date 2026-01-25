"""
Custom exceptions for OpenAxis.

All OpenAxis exceptions inherit from OpenAxisError for easy catching.
"""

from typing import Any


class OpenAxisError(Exception):
    """Base exception for all OpenAxis errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class ConfigurationError(OpenAxisError):
    """Raised when configuration is invalid or missing."""

    pass


class HardwareError(OpenAxisError):
    """Raised when hardware communication fails."""

    def __init__(
        self,
        message: str,
        device: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.device = device


class MotionPlanningError(OpenAxisError):
    """Raised when motion planning fails."""

    pass


class CollisionError(MotionPlanningError):
    """Raised when a collision is detected."""

    pass


class ReachabilityError(MotionPlanningError):
    """Raised when target is unreachable."""

    pass


class SingularityError(MotionPlanningError):
    """Raised when robot approaches singularity."""

    pass


class SlicingError(OpenAxisError):
    """Raised when slicing/toolpath generation fails."""

    pass


class ProcessError(OpenAxisError):
    """Raised when manufacturing process encounters an error."""

    def __init__(
        self,
        message: str,
        process_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.process_type = process_type


class SimulationError(OpenAxisError):
    """Raised when simulation fails."""

    pass


class PluginError(OpenAxisError):
    """Raised when plugin loading or execution fails."""

    def __init__(
        self,
        message: str,
        plugin_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.plugin_name = plugin_name
