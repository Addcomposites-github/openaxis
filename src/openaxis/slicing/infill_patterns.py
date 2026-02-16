"""
Infill Pattern Generators — 8 infill strategies for toolpath filling.

Patterns:
1. grid       — Parallel lines at 0/90 alternating per layer
2. triangles  — 60 angle triangular infill
3. triangle_grid — Dense triangular grid (0/60/120)
4. radial     — Concentric rings from center outward
5. offset     — Inward contour offsets (concentric contours) via pyclipper
6. hexgrid    — Hexagonal honeycomb pattern
7. medial     — Medial axis-guided paths (simplified)
8. zigzag     — Connected zigzag (no travel between lines)

Line-polygon clipping uses **shapely** for robust intersection handling.
Concentric offset uses **pyclipper** for correct concave-polygon support.

References:
- shapely: https://shapely.readthedocs.io/
- pyclipper: https://github.com/fonttools/pyclipper
"""

from __future__ import annotations

import math
import logging
from typing import List, Tuple

import pyclipper
from shapely.geometry import LineString, Polygon as ShapelyPolygon

logger = logging.getLogger(__name__)

Point2D = Tuple[float, float]
Polyline = List[Point2D]
Polygon = List[Point2D]

# pyclipper integer scaling (must match contour_offset.py)
_CLIPPER_SCALE = 1000


# ---------------------------------------------------------------------------
# Core helpers (library-backed)
# ---------------------------------------------------------------------------


def _line_polygon_intersection(
    p1: Point2D, p2: Point2D, polygon: Polygon,
) -> List[Point2D]:
    """
    Find intersection points of a line segment with a polygon boundary.

    Uses shapely for robust geometric intersection that correctly handles
    edge cases (tangent lines, vertices, collinear edges, etc.).
    """
    if len(polygon) < 3:
        return []

    line = LineString([p1, p2])

    # Close the polygon ring if not already closed
    ring = list(polygon)
    if ring[0] != ring[-1]:
        ring.append(ring[0])

    try:
        poly = ShapelyPolygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)  # auto-fix invalid polygons
    except Exception:
        return []

    try:
        intersection = line.intersection(poly)
    except Exception:
        return []

    # Extract coordinate pairs from the intersection result
    intersections: List[Point2D] = []

    if intersection.is_empty:
        return []

    geom_type = intersection.geom_type

    if geom_type == "LineString":
        coords = list(intersection.coords)
        intersections.extend([(float(c[0]), float(c[1])) for c in coords])
    elif geom_type == "MultiLineString":
        for part in intersection.geoms:
            coords = list(part.coords)
            intersections.extend([(float(c[0]), float(c[1])) for c in coords])
    elif geom_type == "Point":
        intersections.append((float(intersection.x), float(intersection.y)))
    elif geom_type == "MultiPoint":
        for pt in intersection.geoms:
            intersections.append((float(pt.x), float(pt.y)))
    elif geom_type == "GeometryCollection":
        for geom in intersection.geoms:
            if geom.geom_type == "LineString":
                coords = list(geom.coords)
                intersections.extend([(float(c[0]), float(c[1])) for c in coords])
            elif geom.geom_type == "Point":
                intersections.append((float(geom.x), float(geom.y)))

    # Sort by distance from p1
    intersections.sort(key=lambda p: (p[0] - p1[0]) ** 2 + (p[1] - p1[1]) ** 2)
    return intersections


def _polygon_bounds(polygon: Polygon) -> Tuple[float, float, float, float]:
    """Get bounding box of polygon: (min_x, min_y, max_x, max_y)."""
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return (min(xs), min(ys), max(xs), max(ys))


def _polygon_center(polygon: Polygon) -> Point2D:
    """Get centroid of polygon."""
    n = len(polygon)
    if n == 0:
        return (0.0, 0.0)
    cx = sum(p[0] for p in polygon) / n
    cy = sum(p[1] for p in polygon) / n
    return (cx, cy)


def _parallel_lines(
    polygon: Polygon,
    angle_deg: float,
    spacing: float,
) -> List[Polyline]:
    """
    Generate parallel scan lines at given angle, clipped to polygon via shapely.
    Returns pairs of intersection points as line segments.
    """
    if spacing <= 0 or len(polygon) < 3:
        return []

    min_x, min_y, max_x, max_y = _polygon_bounds(polygon)
    diagonal = math.sqrt((max_x - min_x) ** 2 + (max_y - min_y) ** 2)
    cx, cy = _polygon_center(polygon)

    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    # Direction perpendicular to scan lines
    perp_x = -sin_a
    perp_y = cos_a

    # Build a shapely polygon once for all line tests
    ring = list(polygon)
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    try:
        spoly = ShapelyPolygon(ring)
        if not spoly.is_valid:
            spoly = spoly.buffer(0)
    except Exception:
        return []

    lines: List[Polyline] = []
    n_lines = int(diagonal / spacing) + 2

    for i in range(-n_lines, n_lines + 1):
        offset = i * spacing
        # Line through center + offset in perpendicular direction
        lx = cx + offset * perp_x
        ly = cy + offset * perp_y
        # Endpoints far enough to span polygon
        p1 = (lx - diagonal * cos_a, ly - diagonal * sin_a)
        p2 = (lx + diagonal * cos_a, ly + diagonal * sin_a)

        try:
            line = LineString([p1, p2])
            intersection = line.intersection(spoly)
        except Exception:
            continue

        if intersection.is_empty:
            continue

        # Extract line segments from intersection
        geom_type = intersection.geom_type
        if geom_type == "LineString":
            coords = list(intersection.coords)
            if len(coords) >= 2:
                seg = [(float(c[0]), float(c[1])) for c in coords]
                lines.append(seg)
        elif geom_type == "MultiLineString":
            for part in intersection.geoms:
                coords = list(part.coords)
                if len(coords) >= 2:
                    seg = [(float(c[0]), float(c[1])) for c in coords]
                    lines.append(seg)
        elif geom_type == "GeometryCollection":
            for geom in intersection.geoms:
                if geom.geom_type == "LineString":
                    coords = list(geom.coords)
                    if len(coords) >= 2:
                        seg = [(float(c[0]), float(c[1])) for c in coords]
                        lines.append(seg)

    return lines


# ---------------------------------------------------------------------------
# Pattern generators
# ---------------------------------------------------------------------------


def generate_grid(polygon: Polygon, spacing: float, layer: int = 0) -> List[Polyline]:
    """Grid infill: alternating 0/90 parallel lines per layer."""
    angle = 0.0 if layer % 2 == 0 else 90.0
    return _parallel_lines(polygon, angle, spacing)


def generate_triangles(polygon: Polygon, spacing: float, layer: int = 0) -> List[Polyline]:
    """Triangular infill: 60 angle rotation per layer (3 directions)."""
    angle = (layer % 3) * 60.0
    return _parallel_lines(polygon, angle, spacing)


def generate_triangle_grid(polygon: Polygon, spacing: float, layer: int = 0) -> List[Polyline]:
    """Dense triangular grid: all three directions (0, 60, 120) in one layer."""
    lines: List[Polyline] = []
    for angle in [0.0, 60.0, 120.0]:
        lines.extend(_parallel_lines(polygon, angle, spacing))
    return lines


def generate_radial(polygon: Polygon, spacing: float, **_: object) -> List[Polyline]:
    """Radial/concentric infill: rings from center outward."""
    cx, cy = _polygon_center(polygon)
    min_x, min_y, max_x, max_y = _polygon_bounds(polygon)
    max_radius = math.sqrt((max_x - min_x) ** 2 + (max_y - min_y) ** 2) / 2

    lines: List[Polyline] = []
    r = spacing
    while r < max_radius:
        # Generate circle points
        n_pts = max(12, int(2 * math.pi * r / spacing))
        circle: Polyline = []
        for i in range(n_pts + 1):
            theta = 2 * math.pi * i / n_pts
            circle.append((cx + r * math.cos(theta), cy + r * math.sin(theta)))
        lines.append(circle)
        r += spacing

    return lines


def generate_offset(polygon: Polygon, spacing: float, **_: object) -> List[Polyline]:
    """
    Offset infill: inward polygon offsets (concentric contours) via pyclipper.

    Unlike the old centroid-based radial shrink, this uses the Clipper library
    to produce geometrically correct inward offsets for any polygon shape,
    including concave and complex shapes.
    """
    if len(polygon) < 3 or spacing <= 0:
        return []

    lines: List[Polyline] = []
    max_iters = 200

    # Ensure CCW for consistent Clipper behaviour
    def _area_signed(poly: Polygon) -> float:
        area = 0.0
        n = len(poly)
        for i in range(n):
            j = (i + 1) % n
            area += poly[i][0] * poly[j][1]
            area -= poly[j][0] * poly[i][1]
        return area / 2.0

    current = list(polygon)
    if _area_signed(current) < 0:
        current = list(reversed(current))

    for _ in range(max_iters):
        if len(current) < 3:
            break

        scaled = [(int(round(x * _CLIPPER_SCALE)), int(round(y * _CLIPPER_SCALE)))
                  for x, y in current]

        pco = pyclipper.PyclipperOffset()
        pco.AddPath(scaled, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)
        result = pco.Execute(-int(round(spacing * _CLIPPER_SCALE)))

        if not result:
            break

        # Take the largest resulting polygon
        best = max(result, key=lambda p: abs(pyclipper.Area(p)))
        new_poly = [(x / _CLIPPER_SCALE, y / _CLIPPER_SCALE) for x, y in best]

        if len(new_poly) < 3:
            break

        # Close the loop for output
        lines.append(new_poly + [new_poly[0]])
        current = new_poly

    return lines


def generate_hexgrid(polygon: Polygon, spacing: float, **_: object) -> List[Polyline]:
    """Hexagonal honeycomb infill pattern."""
    if spacing <= 0 or len(polygon) < 3:
        return []

    min_x, min_y, max_x, max_y = _polygon_bounds(polygon)
    hex_h = spacing * math.sqrt(3) / 2

    lines: List[Polyline] = []
    row = 0
    y = min_y
    while y <= max_y:
        offset_x = (spacing / 2) if (row % 2 == 1) else 0
        x = min_x + offset_x
        while x <= max_x:
            # Draw hexagon
            hex_pts: Polyline = []
            for i in range(7):
                angle = math.radians(60 * i + 30)
                hx = x + (spacing / 2) * math.cos(angle)
                hy = y + (spacing / 2) * math.sin(angle)
                hex_pts.append((hx, hy))
            lines.append(hex_pts)
            x += spacing
        y += hex_h
        row += 1

    return lines


def generate_medial(polygon: Polygon, spacing: float, **_: object) -> List[Polyline]:
    """
    Medial axis-guided paths (simplified).
    Creates paths along a simplified medial axis approximation.
    """
    # Simplified: use offset contours + connecting paths along center line
    cx, cy = _polygon_center(polygon)
    min_x, min_y, max_x, max_y = _polygon_bounds(polygon)

    lines: List[Polyline] = []
    # Horizontal medial line
    lines.append([(min_x, cy), (max_x, cy)])
    # Vertical medial line
    lines.append([(cx, min_y), (cx, max_y)])

    # Add offset contours (now pyclipper-backed)
    lines.extend(generate_offset(polygon, spacing))

    return lines


def generate_zigzag(polygon: Polygon, spacing: float, layer: int = 0) -> List[Polyline]:
    """
    Zigzag infill: connected parallel lines (no travel between lines).
    Lines alternate direction to form a continuous zigzag path.
    """
    angle = 0.0 if layer % 2 == 0 else 90.0
    parallel = _parallel_lines(polygon, angle, spacing)

    if not parallel:
        return []

    # Connect alternating lines to form zigzag
    connected: Polyline = []
    for i, line in enumerate(parallel):
        if len(line) < 2:
            continue
        if i % 2 == 0:
            connected.extend(line)
        else:
            connected.extend(reversed(line))

    return [connected] if connected else []


# --- Pattern Registry ---

INFILL_PATTERNS = {
    'grid': generate_grid,
    'triangles': generate_triangles,
    'triangle_grid': generate_triangle_grid,
    'radial': generate_radial,
    'offset': generate_offset,
    'hexgrid': generate_hexgrid,
    'medial': generate_medial,
    'zigzag': generate_zigzag,
}


def generate_infill(
    polygon: Polygon,
    pattern: str,
    spacing: float,
    layer: int = 0,
) -> List[Polyline]:
    """
    Generate infill paths for a polygon using the specified pattern.

    Parameters:
        polygon: List of (x, y) points defining the boundary.
        pattern: Pattern name from INFILL_PATTERNS.
        spacing: Line spacing in mm.
        layer: Current layer index (used for alternating patterns).

    Returns:
        List of polylines (list of (x, y) points).
    """
    generator = INFILL_PATTERNS.get(pattern, generate_grid)
    return generator(polygon, spacing, layer=layer)
