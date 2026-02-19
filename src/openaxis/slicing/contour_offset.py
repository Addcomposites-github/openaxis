"""
Contour offset for wall generation.

DELETED: Custom pyclipper-based polygon offset code removed.
This functionality is now handled by compas_slicer's built-in
wall generation. These stubs remain for backward compatibility
of imports only.

TODO: If fine-grained wall control is needed beyond what compas_slicer
provides, integrate pyclipper through compas_slicer's post-processing
pipeline, not as custom code.
"""

from typing import List, Optional, Tuple


def offset_polygon(
    polygon: List[Tuple[float, float]],
    offset_distance: float,
) -> List[List[Tuple[float, float]]]:
    """Polygon offset — now handled by compas_slicer."""
    raise NotImplementedError(
        "Custom polygon offset deleted. Use compas_slicer for wall generation. "
        "If standalone offset is needed, use pyclipper directly with validated parameters."
    )


def compute_inner_walls(
    contour: List[Tuple[float, float]],
    wall_count: int = 1,
    wall_width: float = 1.0,
) -> List[List[Tuple[float, float]]]:
    """Inner wall computation — now handled by compas_slicer."""
    raise NotImplementedError(
        "Custom inner wall computation deleted. Use compas_slicer for wall generation."
    )


def get_infill_boundary(
    contour: List[Tuple[float, float]],
    wall_count: int = 2,
    wall_width: float = 1.0,
) -> Optional[List[Tuple[float, float]]]:
    """Infill boundary computation — now handled by compas_slicer."""
    raise NotImplementedError(
        "Custom infill boundary computation deleted. Use compas_slicer for infill."
    )
