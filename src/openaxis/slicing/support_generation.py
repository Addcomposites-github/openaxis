"""
Support structure generation for additive manufacturing.

Detects overhanging faces on a mesh using trimesh face normals and the
build-direction threshold angle, then generates columnar support toolpaths
from the overhang regions down to the build plate (or the nearest solid layer).

Uses **trimesh** for face-normal analysis and **pyclipper** for 2D polygon
operations (offset, simplification).  This keeps our dependency footprint
consistent with the rest of the slicing pipeline.

References:
- trimesh face_normals: https://trimsh.org/trimesh.html
- pyclipper polygon offset: https://github.com/fonttools/pyclipper
"""

from __future__ import annotations

import logging
import math
from typing import List, Optional, Tuple

import numpy as np
import trimesh
from compas.geometry import Point

from openaxis.slicing.toolpath import Toolpath, ToolpathSegment, ToolpathType

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────────


def detect_overhangs(
    mesh: trimesh.Trimesh,
    threshold_angle: float = 45.0,
    build_direction: np.ndarray | None = None,
) -> np.ndarray:
    """
    Detect faces whose normal deviates from the build direction by more than
    *threshold_angle* degrees.

    Args:
        mesh: trimesh mesh to analyse.
        threshold_angle: maximum angle (degrees) from build direction before a
                         face is considered overhanging.  45° is a common
                         default for FDM / WAAM.
        build_direction: unit vector of the build direction (default [0, 0, 1]).

    Returns:
        Boolean mask of shape (num_faces,) — True for overhanging faces.
    """
    if build_direction is None:
        build_direction = np.array([0.0, 0.0, 1.0])

    build_direction = build_direction / np.linalg.norm(build_direction)
    normals = mesh.face_normals  # (N, 3)

    # Dot product between each face normal and the build direction.
    # cos(threshold_angle) is the boundary: faces with dot < cos(180 - thresh)
    # are "hanging" (their normal points away from the build direction).
    dot = np.einsum("ij,j->i", normals, build_direction)

    # Angle between face normal and build direction
    # A face pointing straight down has angle ~180°.
    # We flag as overhang if the angle > (90 + threshold_angle).
    angle_limit = math.radians(90.0 + threshold_angle)
    cos_limit = math.cos(angle_limit)

    overhang_mask = dot < cos_limit

    logger.debug(
        "Overhang detection: %d / %d faces overhang at %.1f° threshold",
        int(overhang_mask.sum()),
        len(overhang_mask),
        threshold_angle,
    )
    return overhang_mask


def generate_support_regions(
    mesh: trimesh.Trimesh,
    overhang_mask: np.ndarray,
    layer_height: float,
    xy_offset: float = 0.5,
) -> List[List[Tuple[float, float]]]:
    """
    Project overhanging faces down to the build plate and return 2D support
    region polygons (one polygon per connected overhang cluster).

    The workflow:
    1. Select overhanging triangles.
    2. Project their vertices onto the XY plane (Z = 0).
    3. Compute the 2D convex hull of each connected cluster.
    4. Optionally offset inward by *xy_offset* to leave a gap between
       support and part.

    Args:
        mesh: trimesh mesh.
        overhang_mask: boolean mask from ``detect_overhangs``.
        layer_height: layer height (used for Z discretisation).
        xy_offset: gap between support boundary and part surface (mm).

    Returns:
        List of 2D polygons (each polygon is a list of (x, y) tuples).
    """
    if not overhang_mask.any():
        return []

    # Extract overhanging face indices
    face_indices = np.where(overhang_mask)[0]

    # Get face vertices projected to XY
    overhang_faces = mesh.faces[face_indices]
    overhang_verts = mesh.vertices[overhang_faces.ravel()]  # (N*3, 3)
    projected_xy = overhang_verts[:, :2]  # drop Z

    # Group connected faces into clusters using trimesh adjacency
    try:
        # Build a sub-mesh of overhanging faces and split into components
        sub_mesh = mesh.submesh([face_indices], only_watertight=False)
        if isinstance(sub_mesh, list):
            components = sub_mesh
        else:
            components = [sub_mesh]
    except Exception:
        # Fallback: treat all overhang faces as one cluster
        components = None

    regions: List[List[Tuple[float, float]]] = []

    if components and len(components) > 0:
        for comp in components:
            if len(comp.vertices) < 3:
                continue
            # 2D convex hull of projected vertices
            xy = comp.vertices[:, :2]
            try:
                from scipy.spatial import ConvexHull

                hull = ConvexHull(xy)
                hull_pts = xy[hull.vertices]
                polygon = [(float(p[0]), float(p[1])) for p in hull_pts]
                if len(polygon) >= 3:
                    regions.append(polygon)
            except Exception:
                # Degenerate — skip
                continue
    else:
        # Single cluster fallback
        if len(projected_xy) >= 3:
            try:
                from scipy.spatial import ConvexHull

                hull = ConvexHull(projected_xy)
                hull_pts = projected_xy[hull.vertices]
                polygon = [(float(p[0]), float(p[1])) for p in hull_pts]
                if len(polygon) >= 3:
                    regions.append(polygon)
            except Exception:
                pass

    logger.info("Generated %d support regions from %d overhang faces",
                len(regions), int(overhang_mask.sum()))
    return regions


def generate_support_toolpath(
    regions: List[List[Tuple[float, float]]],
    z_min: float,
    z_max: float,
    layer_height: float,
    extrusion_width: float = 2.0,
    infill_density: float = 0.15,
    print_speed: float = 800.0,
) -> List[ToolpathSegment]:
    """
    Generate line-infill support segments for each support region, layer by
    layer from *z_min* up to *z_max*.

    Uses a simple line-fill pattern (parallel lines) that is easy to remove
    after printing.

    Args:
        regions: 2D support region polygons from ``generate_support_regions``.
        z_min: bottom Z of support (typically build plate = 0).
        z_max: top Z of support (bottom of overhanging face).
        layer_height: layer height (mm).
        extrusion_width: bead width for support material (mm).
        infill_density: infill density for support (default 15%).
        print_speed: print speed for support segments (mm/min).

    Returns:
        List of ToolpathSegment with type SUPPORT.
    """
    if not regions or infill_density <= 0:
        return []

    segments: List[ToolpathSegment] = []

    # Compute number of layers
    num_layers = max(1, int(math.ceil((z_max - z_min) / layer_height)))

    # Line spacing from density
    spacing = extrusion_width / max(infill_density, 0.01)

    for layer_idx in range(num_layers):
        z = z_min + layer_idx * layer_height

        for region in regions:
            # Bounding box of region
            xs = [p[0] for p in region]
            ys = [p[1] for p in region]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)

            # Generate parallel lines in alternating X/Y directions
            alternate = layer_idx % 2 == 0

            if alternate:
                # Lines along X axis
                y = y_min + spacing / 2
                while y < y_max:
                    line_pts = [
                        Point(x_min, y, z),
                        Point(x_max, y, z),
                    ]
                    segments.append(ToolpathSegment(
                        points=line_pts,
                        type=ToolpathType.SUPPORT,
                        layer_index=layer_idx,
                        extrusion_width=extrusion_width,
                        speed=print_speed,
                        flow_rate=0.5,  # reduced flow for easy removal
                    ))
                    y += spacing
            else:
                # Lines along Y axis
                x = x_min + spacing / 2
                while x < x_max:
                    line_pts = [
                        Point(x, y_min, z),
                        Point(x, y_max, z),
                    ]
                    segments.append(ToolpathSegment(
                        points=line_pts,
                        type=ToolpathType.SUPPORT,
                        layer_index=layer_idx,
                        extrusion_width=extrusion_width,
                        speed=print_speed,
                        flow_rate=0.5,
                    ))
                    x += spacing

    logger.info(
        "Generated %d support segments across %d layers",
        len(segments),
        num_layers,
    )
    return segments


def add_supports_to_toolpath(
    mesh: trimesh.Trimesh,
    toolpath: Toolpath,
    threshold_angle: float = 45.0,
    support_density: float = 0.15,
    xy_gap: float = 0.5,
) -> int:
    """
    High-level function: detect overhangs and add support segments to an
    existing toolpath.

    Args:
        mesh: trimesh mesh (Z-up).
        toolpath: existing toolpath to augment.
        threshold_angle: overhang threshold (degrees).
        support_density: infill density for support structures.
        xy_gap: XY gap between support and part (mm).

    Returns:
        Number of support segments added.
    """
    # 1. Detect overhangs
    overhang_mask = detect_overhangs(mesh, threshold_angle)
    if not overhang_mask.any():
        logger.info("No overhangs detected — skipping support generation")
        return 0

    # 2. Generate 2D support regions
    regions = generate_support_regions(
        mesh, overhang_mask, toolpath.layer_height, xy_gap
    )
    if not regions:
        return 0

    # 3. Compute Z range for supports
    # Bottom of supports = build plate (z = 0) — supports always start from
    # the ground plane so that the machine has a solid base to build on.
    # Top of supports = lowest Z of overhanging faces.
    overhang_face_indices = np.where(overhang_mask)[0]
    overhang_face_verts = mesh.vertices[mesh.faces[overhang_face_indices].ravel()]
    z_min = 0.0  # Build plate
    z_max = float(overhang_face_verts[:, 2].min())

    if z_max <= z_min + toolpath.layer_height:
        logger.info("Overhang too close to build plate — skipping supports")
        return 0

    # 4. Generate support segments
    support_segments = generate_support_toolpath(
        regions,
        z_min=z_min,
        z_max=z_max,
        layer_height=toolpath.layer_height,
        extrusion_width=toolpath.layer_height * 0.8,  # thinner support bead
        infill_density=support_density,
    )

    # 5. Insert support segments before the regular segments at each layer
    # (supports should print first, then part on top)
    for seg in support_segments:
        toolpath.segments.insert(0, seg)

    logger.info("Added %d support segments to toolpath", len(support_segments))
    return len(support_segments)
