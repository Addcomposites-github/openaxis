"""
Slicing module - Toolpath generation for additive and subtractive manufacturing.

This module provides slicing and toolpath generation capabilities for various
manufacturing processes including WAAM, pellet extrusion, and milling.
"""

from openaxis.slicing.planar_slicer import PlanarSlicer
from openaxis.slicing.toolpath import Toolpath, ToolpathSegment, ToolpathType
from openaxis.slicing.gcode import GCodeGenerator, GCodeConfig

__all__ = [
    "PlanarSlicer",
    "Toolpath",
    "ToolpathSegment",
    "ToolpathType",
    "GCodeGenerator",
    "GCodeConfig",
]
