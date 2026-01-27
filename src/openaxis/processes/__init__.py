"""
Manufacturing process plugins.

This module provides process-specific implementations for different
manufacturing methods including additive, subtractive, and hybrid processes.
"""

from openaxis.processes.base import ProcessParameters, ProcessPlugin, ProcessType
from openaxis.processes.milling import (
    MillingParameters,
    MillingProcess,
    MillingStrategy,
    ToolType,
)
from openaxis.processes.pellet import PelletExtrusionParameters, PelletExtrusionProcess
from openaxis.processes.waam import WAAMParameters, WAAMProcess

__all__ = [
    "ProcessType",
    "ProcessParameters",
    "ProcessPlugin",
    # Pellet Extrusion
    "PelletExtrusionParameters",
    "PelletExtrusionProcess",
    # WAAM
    "WAAMParameters",
    "WAAMProcess",
    # Milling
    "MillingParameters",
    "MillingProcess",
    "MillingStrategy",
    "ToolType",
]
