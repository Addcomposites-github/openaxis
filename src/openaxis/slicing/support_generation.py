"""
Support structure generation for additive manufacturing.

DELETED: Custom support detection and generation code removed.
While the overhang detection used trimesh face normals (valid approach),
the support region clustering and toolpath generation were custom
code without research citations.

TODO: Integrate support generation from compas_slicer, or implement
based on cited research:
- Jiang, J. et al. (2018) "Support structures for additive manufacturing:
  A review" — comprehensive survey of support strategies
- Vanek, J. et al. (2014) "Clever support: Efficient support structure
  generation for digital fabrication" — tree support algorithms

Stubs remain for backward compatibility of imports only.
"""

from typing import List, Optional

import numpy as np

from openaxis.slicing.toolpath import Toolpath


def detect_overhangs(
    mesh: object,
    threshold_angle: float = 45.0,
    build_direction: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Overhang detection — not yet implemented with research backing."""
    raise NotImplementedError(
        "Custom overhang detection deleted. "
        "Use compas_slicer for support generation."
    )


def generate_support_regions(
    mesh: object,
    overhang_faces: np.ndarray,
) -> list:
    """Support region generation — not yet implemented."""
    raise NotImplementedError(
        "Custom support region generation deleted. "
        "Use compas_slicer for support generation."
    )


def generate_support_toolpath(
    regions: list,
    layer_height: float = 1.0,
    extrusion_width: float = 1.0,
    support_density: float = 0.15,
) -> list:
    """Support toolpath generation — not yet implemented."""
    raise NotImplementedError(
        "Custom support toolpath generation deleted. "
        "Use compas_slicer for support generation."
    )


def add_supports_to_toolpath(
    mesh: object,
    toolpath: Toolpath,
    threshold_angle: float = 45.0,
    support_density: float = 0.15,
) -> int:
    """Add supports to toolpath — not yet implemented."""
    raise NotImplementedError(
        "Custom support generation deleted. "
        "Use compas_slicer for support generation."
    )
