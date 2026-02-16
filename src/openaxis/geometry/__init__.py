"""
Geometry module — Mesh operations, analysis, and repair.

Provides boolean operations (union, subtract, intersect), mesh repair,
mesh analysis, and uniform mesh offset for manufacturing workflows.
"""

from openaxis.geometry.mesh_operations import (
    boolean_union,
    boolean_subtract,
    boolean_intersect,
    repair_mesh,
    analyze_mesh,
    offset_mesh,
)

__all__ = [
    "boolean_union",
    "boolean_subtract",
    "boolean_intersect",
    "repair_mesh",
    "analyze_mesh",
    "offset_mesh",
]
