"""
Slicing module - Toolpath generation for additive and subtractive manufacturing.

This module provides slicing and toolpath generation capabilities:

Working integrations:
- MillingToolpathGenerator: OpenCAMLib-based 3-axis milling (waterline + drop-cutter)
- ORNLSlicer: ORNL Slicer 2 subprocess wrapper (requires binary installed)
- GCodeGenerator: Vendor-specific G-code output

Stub modules (raise NotImplementedError):
- AngledSlicer, RadialSlicer, CurveSlicer, RevolvedSlicer: Pending ORNL Slicer 2
- infill_patterns, contour_offset, seam_control, etc.: Pending ORNL Slicer 2
"""

from openaxis.slicing.planar_slicer import PlanarSlicer
from openaxis.slicing.toolpath import Toolpath, ToolpathSegment, ToolpathType, InfillPattern
from openaxis.slicing.gcode import GCodeGenerator, GCodeConfig
from openaxis.slicing.ornl_slicer import ORNLSlicer, ORNLSlicerConfig
from openaxis.slicing.milling_toolpath import MillingToolpathGenerator, CutterType

# Stub modules (raise NotImplementedError for ungrounded code)
from openaxis.slicing.contour_offset import compute_inner_walls, get_infill_boundary, offset_polygon
from openaxis.slicing.infill_patterns import generate_infill
from openaxis.slicing.seam_control import apply_seam
from openaxis.slicing.engage_disengage import add_engage_disengage, add_lead_in, add_lead_out

from openaxis.slicing.support_generation import (
    detect_overhangs,
    generate_support_regions,
    generate_support_toolpath,
    add_supports_to_toolpath,
)

from openaxis.slicing.angled_slicer import AngledSlicer
from openaxis.slicing.radial_slicer import RadialSlicer
from openaxis.slicing.curve_slicer import CurveSlicer
from openaxis.slicing.revolved_slicer import RevolvedSlicer
from openaxis.slicing.slicer_factory import get_slicer, SLICER_REGISTRY

__all__ = [
    # Working
    "PlanarSlicer",
    "ORNLSlicer",
    "ORNLSlicerConfig",
    "MillingToolpathGenerator",
    "CutterType",
    "Toolpath",
    "ToolpathSegment",
    "ToolpathType",
    "InfillPattern",
    "GCodeGenerator",
    "GCodeConfig",
    # Stubs (NotImplementedError)
    "compute_inner_walls",
    "get_infill_boundary",
    "offset_polygon",
    "generate_infill",
    "apply_seam",
    "add_engage_disengage",
    "add_lead_in",
    "add_lead_out",
    "detect_overhangs",
    "generate_support_regions",
    "generate_support_toolpath",
    "add_supports_to_toolpath",
    "AngledSlicer",
    "RadialSlicer",
    "CurveSlicer",
    "RevolvedSlicer",
    "get_slicer",
    "SLICER_REGISTRY",
]
