"""
Mesh boolean and repair operations for OpenAxis geometry pipeline.

Provides:
- Boolean union, subtract, intersect (via trimesh / manifold)
- Mesh repair (hole filling, self-intersection removal, normal fixing)
- Mesh offset (uniform shell offset)

All operations accept and return COMPAS Mesh objects, converting
internally to trimesh for the heavy lifting.
"""

import logging
from typing import List, Optional, Tuple

import numpy as np
import trimesh
from compas.datastructures import Mesh as CompasMesh

from openaxis.core.geometry import GeometryConverter
from openaxis.core.exceptions import GeometryError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Boolean operations
# ---------------------------------------------------------------------------

def boolean_union(mesh_a: CompasMesh, mesh_b: CompasMesh) -> CompasMesh:
    """
    Boolean union of two meshes (A ∪ B).

    Args:
        mesh_a: First operand (COMPAS Mesh).
        mesh_b: Second operand (COMPAS Mesh).

    Returns:
        Result mesh (COMPAS Mesh).

    Raises:
        GeometryError: If the boolean operation fails.
    """
    return _boolean_op(mesh_a, mesh_b, "union")


def boolean_subtract(mesh_a: CompasMesh, mesh_b: CompasMesh) -> CompasMesh:
    """
    Boolean subtraction (A − B).

    Args:
        mesh_a: Base mesh.
        mesh_b: Mesh to subtract from *mesh_a*.

    Returns:
        Result mesh (COMPAS Mesh).
    """
    return _boolean_op(mesh_a, mesh_b, "difference")


def boolean_intersect(mesh_a: CompasMesh, mesh_b: CompasMesh) -> CompasMesh:
    """
    Boolean intersection (A ∩ B).

    Args:
        mesh_a: First operand.
        mesh_b: Second operand.

    Returns:
        Intersection mesh (COMPAS Mesh).
    """
    return _boolean_op(mesh_a, mesh_b, "intersection")

def _boolean_op(mesh_a: CompasMesh, mesh_b: CompasMesh, operation: str) -> CompasMesh:
    """Internal dispatcher for boolean operations."""
    try:
        ta = GeometryConverter.compas_to_trimesh(mesh_a)
        tb = GeometryConverter.compas_to_trimesh(mesh_b)

        logger.info(
            "Boolean %s: A(%d verts, %d faces) op B(%d verts, %d faces)",
            operation, len(ta.vertices), len(ta.faces),
            len(tb.vertices), len(tb.faces),
        )

        result = trimesh.boolean.boolean_manifold([ta, tb], operation)

        if result is None or not hasattr(result, "vertices") or len(result.vertices) == 0:
            raise GeometryError(f"Boolean {operation} produced empty result")

        logger.info(
            "Boolean %s result: %d verts, %d faces",
            operation, len(result.vertices), len(result.faces),
        )
        return GeometryConverter.trimesh_to_compas(result)

    except GeometryError:
        raise
    except Exception as e:
        raise GeometryError(f"Boolean {operation} failed: {e}") from e


# ---------------------------------------------------------------------------
# Mesh repair
# ---------------------------------------------------------------------------

def repair_mesh(
    mesh: CompasMesh,
    fill_holes: bool = True,
    fix_normals: bool = True,
    fix_winding: bool = True,
    remove_degenerate: bool = True,
) -> Tuple[CompasMesh, dict]:
    """
    Repair a mesh by filling holes, fixing normals, removing degenerate faces.

    Args:
        mesh: Input COMPAS Mesh.
        fill_holes: Whether to fill boundary holes.
        fix_normals: Whether to fix face normal consistency.
        fix_winding: Whether to fix face winding order.
        remove_degenerate: Whether to remove zero-area or collapsed faces.

    Returns:
        Tuple of (repaired COMPAS Mesh, repair report dict).
    """
    try:
        tmesh = GeometryConverter.compas_to_trimesh(mesh)

        report = {
            "original_vertices": len(tmesh.vertices),
            "original_faces": len(tmesh.faces),
            "was_watertight": tmesh.is_watertight,
            "holes_filled": 0,
            "normals_fixed": False,
            "degenerate_removed": 0,
        }

        # Fill holes
        if fill_holes:
            hole_count_before = len(tmesh.faces)
            trimesh.repair.fill_holes(tmesh)
            report["holes_filled"] = len(tmesh.faces) - hole_count_before

        # Fix normals
        if fix_normals:
            if not tmesh.is_watertight:
                # Try to make watertight first
                trimesh.repair.fix_inversion(tmesh)
            trimesh.repair.fix_normals(tmesh)
            report["normals_fixed"] = True

        # Fix winding
        if fix_winding:
            trimesh.repair.fix_winding(tmesh)

        # Remove degenerate faces
        if remove_degenerate:
            mask = tmesh.nondegenerate_faces()
            if not mask.all():
                removed = int(np.sum(~mask))
                tmesh.update_faces(mask)
                tmesh.remove_unreferenced_vertices()
                report["degenerate_removed"] = removed

        report["result_vertices"] = len(tmesh.vertices)
        report["result_faces"] = len(tmesh.faces)
        report["is_watertight"] = tmesh.is_watertight
        report["is_volume"] = tmesh.is_volume

        logger.info(
            "Mesh repair: %d→%d verts, %d→%d faces, watertight=%s",
            report["original_vertices"], report["result_vertices"],
            report["original_faces"], report["result_faces"],
            report["is_watertight"],
        )

        return GeometryConverter.trimesh_to_compas(tmesh), report

    except Exception as e:
        raise GeometryError(f"Mesh repair failed: {e}") from e


# ---------------------------------------------------------------------------
# Mesh analysis
# ---------------------------------------------------------------------------

def analyze_mesh(mesh: CompasMesh) -> dict:
    """
    Analyze mesh quality and return a diagnostic report.

    Returns dict with: vertex_count, face_count, is_watertight, is_volume,
    euler_number, bounds, volume, surface_area, etc.
    """
    try:
        tmesh = GeometryConverter.compas_to_trimesh(mesh)
        bounds = tmesh.bounds.tolist()  # [[xmin,ymin,zmin],[xmax,ymax,zmax]]
        size = (tmesh.bounds[1] - tmesh.bounds[0]).tolist()

        return {
            "vertex_count": len(tmesh.vertices),
            "face_count": len(tmesh.faces),
            "edge_count": len(tmesh.edges),
            "is_watertight": bool(tmesh.is_watertight),
            "is_volume": bool(tmesh.is_volume),
            "euler_number": int(tmesh.euler_number),
            "bounds_min": bounds[0],
            "bounds_max": bounds[1],
            "size": size,
            "volume": float(tmesh.volume) if tmesh.is_volume else None,
            "surface_area": float(tmesh.area),
            "center_mass": tmesh.center_mass.tolist() if tmesh.is_volume else None,
        }
    except Exception as e:
        raise GeometryError(f"Mesh analysis failed: {e}") from e


# ---------------------------------------------------------------------------
# Mesh offset (uniform shell)
# ---------------------------------------------------------------------------

def offset_mesh(mesh: CompasMesh, distance: float) -> CompasMesh:
    """
    Create a uniformly offset shell of the mesh.

    Moves every vertex along its normal by *distance* millimetres.
    Positive values expand the mesh; negative values shrink it.

    Args:
        mesh: Input COMPAS Mesh.
        distance: Offset distance in mm (positive = outward).

    Returns:
        Offset COMPAS Mesh.

    Raises:
        GeometryError: If offset fails.
    """
    try:
        tmesh = GeometryConverter.compas_to_trimesh(mesh)

        # Compute per-vertex normals
        normals = tmesh.vertex_normals

        if normals is None or len(normals) != len(tmesh.vertices):
            raise GeometryError("Cannot compute vertex normals for offset")

        # Offset vertices
        new_vertices = tmesh.vertices + normals * distance

        result = trimesh.Trimesh(vertices=new_vertices, faces=tmesh.faces.copy())

        # Fix any inversions caused by negative offset
        if distance < 0:
            trimesh.repair.fix_inversion(result)
            trimesh.repair.fix_normals(result)

        logger.info(
            "Mesh offset: distance=%.2f mm, %d verts, %d faces",
            distance, len(result.vertices), len(result.faces),
        )

        return GeometryConverter.trimesh_to_compas(result)

    except GeometryError:
        raise
    except Exception as e:
        raise GeometryError(f"Mesh offset failed: {e}") from e
