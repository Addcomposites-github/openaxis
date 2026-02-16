"""
Contour Offset — Polygon offset for inner wall generation.

Provides polygon inset operations for generating:
- Outer wall (original contour)
- Inner walls (1 or more offset contours)
- Infill boundary (innermost offset)

Uses **pyclipper** (Python bindings for Angus Johnson's Clipper library)
for robust, production-grade polygon offsetting that correctly handles
concave polygons, self-intersections, and degenerate cases.

References:
- pyclipper: https://github.com/fonttools/pyclipper
- Clipper library: http://www.angusj.com/delphi/clipper.php
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import pyclipper

logger = logging.getLogger(__name__)

Point2D = Tuple[float, float]
Polygon = List[Point2D]

# pyclipper uses integer coordinates for precision.
# We scale floating-point mm coordinates by this factor.
_CLIPPER_SCALE = 1000  # 1 mm  → 1000 clipper units  → 0.001 mm resolution


def _to_clipper(polygon: Polygon) -> List[Tuple[int, int]]:
    """Scale floating-point polygon to pyclipper integer coordinates."""
    return [(int(round(x * _CLIPPER_SCALE)), int(round(y * _CLIPPER_SCALE)))
            for x, y in polygon]


def _from_clipper(path: list) -> Polygon:
    """Scale pyclipper integer coordinates back to floating-point mm."""
    return [(x / _CLIPPER_SCALE, y / _CLIPPER_SCALE) for x, y in path]


def _polygon_area_signed(polygon: Polygon) -> float:
    """Compute signed area (positive = CCW, negative = CW)."""
    area = 0.0
    n = len(polygon)
    for i in range(n):
        j = (i + 1) % n
        area += polygon[i][0] * polygon[j][1]
        area -= polygon[j][0] * polygon[i][1]
    return area / 2.0


def _ensure_ccw(polygon: Polygon) -> Polygon:
    """Ensure polygon is counter-clockwise."""
    if _polygon_area_signed(polygon) < 0:
        return list(reversed(polygon))
    return list(polygon)


def offset_polygon(polygon: Polygon, distance: float) -> Optional[Polygon]:
    """
    Offset a polygon inward by the given distance using pyclipper.

    Handles concave polygons, sharp corners, and degenerate cases correctly
    via the Clipper library's Minkowski-sum-based offset algorithm.

    Parameters:
        polygon: Polygon as list of (x, y) points (any winding).
        distance: Offset distance in mm (positive = inward).

    Returns:
        Offset polygon, or None if the polygon collapsed.
    """
    if len(polygon) < 3:
        return None
    if distance <= 0:
        return list(polygon)

    poly = _ensure_ccw(polygon)
    scaled = _to_clipper(poly)

    pco = pyclipper.PyclipperOffset()
    pco.AddPath(scaled, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)

    # Negative offset = inward for CCW polygon in Clipper convention
    result = pco.Execute(-int(round(distance * _CLIPPER_SCALE)))

    if not result:
        return None

    # Return the largest polygon (by area) if multiple result paths
    best = max(result, key=lambda p: abs(pyclipper.Area(p)))
    out = _from_clipper(best)

    if len(out) < 3:
        return None

    return out


def compute_inner_walls(
    contour: Polygon,
    wall_count: int,
    wall_width: float,
) -> List[Polygon]:
    """
    Compute inner wall contours by repeated polygon offset using pyclipper.

    Each wall is offset inward by ``wall_width`` from the previous contour.
    If the polygon collapses (area too small), remaining walls are skipped.

    Parameters:
        contour: Outer wall polygon.
        wall_count: Number of inner walls to generate.
        wall_width: Width of each wall (mm), used as offset distance.

    Returns:
        List of offset polygons (outer to inner).
        The first element is the original contour (CCW).
    """
    walls: List[Polygon] = [_ensure_ccw(contour)]

    current = walls[0]
    for _i in range(wall_count):
        offset = offset_polygon(current, wall_width)
        if offset is None:
            break
        walls.append(offset)
        current = offset

    return walls


def get_infill_boundary(
    contour: Polygon,
    wall_count: int,
    wall_width: float,
) -> Optional[Polygon]:
    """
    Get the innermost contour to use as infill boundary.

    Parameters:
        contour: Outer wall polygon.
        wall_count: Number of walls.
        wall_width: Wall width (mm).

    Returns:
        The innermost offset polygon, or None if collapsed.
    """
    walls = compute_inner_walls(contour, wall_count, wall_width)
    if len(walls) > 1:
        return walls[-1]
    return walls[0] if walls else None
