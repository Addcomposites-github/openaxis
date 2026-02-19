"""
Infill pattern generation.

DELETED: All 8 custom infill pattern implementations removed.
This includes: grid, triangles, triangle_grid, radial, offset,
hexgrid, medial (was fake — 2 hardcoded lines, NOT a real medial axis),
and zigzag.

Infill generation is now handled by compas_slicer's built-in
print organization and path planning.

Previously this module contained custom shapely/pyclipper code
that was not from any research paper or proven algorithm.
The 'medial' pattern was particularly egregious — it claimed to
be medial-axis infill but was just 2 perpendicular lines through
the centroid, not a Voronoi skeleton.
"""

from typing import List, Tuple


def generate_infill(
    polygon: List[Tuple[float, float]],
    pattern: str = "grid",
    spacing: float = 5.0,
    layer: int = 0,
) -> List[List[Tuple[float, float]]]:
    """Infill generation — now handled by compas_slicer."""
    raise NotImplementedError(
        "Custom infill pattern generation deleted. "
        "Use compas_slicer for infill generation. "
        "The previous implementation had no research citations and the "
        "'medial' pattern was fake (2 hardcoded perpendicular lines)."
    )
