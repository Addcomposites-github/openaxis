"""
Slicing module - Toolpath generation for additive and subtractive manufacturing.

This module provides slicing and toolpath generation capabilities for various
manufacturing processes including WAAM, pellet extrusion, and milling.
"""

from openaxis.slicing.planar_slicer import PlanarSlicer
from openaxis.slicing.toolpath import Toolpath, ToolpathSegment, ToolpathType, InfillPattern
from openaxis.slicing.gcode import GCodeGenerator, GCodeConfig

# Sprint 5: Advanced slicing modules
from openaxis.slicing.contour_offset import compute_inner_walls, get_infill_boundary, offset_polygon
from openaxis.slicing.infill_patterns import generate_infill
from openaxis.slicing.seam_control import apply_seam
from openaxis.slicing.engage_disengage import add_engage_disengage, add_lead_in, add_lead_out

# Sprint 9: Support generation
from openaxis.slicing.support_generation import (
    detect_overhangs,
    generate_support_regions,
    generate_support_toolpath,
    add_supports_to_toolpath,
)

# Sprint 7: Additional slicing strategies + factory
from openaxis.slicing.angled_slicer import AngledSlicer
from openaxis.slicing.radial_slicer import RadialSlicer
from openaxis.slicing.curve_slicer import CurveSlicer
from openaxis.slicing.revolved_slicer import RevolvedSlicer
from openaxis.slicing.slicer_factory import get_slicer, SLICER_REGISTRY

__all__ = [
    "PlanarSlicer",
    "Toolpath",
    "ToolpathSegment",
    "ToolpathType",
    "InfillPattern",
    "GCodeGenerator",
    "GCodeConfig",
    # Sprint 5
    "compute_inner_walls",
    "get_infill_boundary",
    "offset_polygon",
    "generate_infill",
    "apply_seam",
    "add_engage_disengage",
    "add_lead_in",
    "add_lead_out",
    # Sprint 9
    "detect_overhangs",
    "generate_support_regions",
    "generate_support_toolpath",
    "add_supports_to_toolpath",
    # Sprint 7
    "AngledSlicer",
    "RadialSlicer",
    "CurveSlicer",
    "RevolvedSlicer",
    "get_slicer",
    "SLICER_REGISTRY",
]
