"""
Revolved slicing for rotational parts with a positioner.

DELETED: Custom helical toolpath generation code removed.
While the Gram-Schmidt orthonormalization was mathematically correct,
the implementation had magic constants (0.9 threshold) and edge cases
that could fail silently.

TODO: Integrate compas_slicer for helical/revolved toolpaths, or
implement based on cited research for robotic deposition on rotary
positioners.

Library: https://compas.dev/compas_slicer/
"""

from typing import Optional

import numpy as np
from compas.datastructures import Mesh as CompasMesh

from openaxis.slicing.toolpath import Toolpath


class RevolvedSlicer:
    """
    Revolved slicing — delegates to compas_slicer.

    TODO: Integrate compas_slicer for helical/rotary toolpaths.
    """

    def __init__(
        self,
        axis_origin: Optional[np.ndarray] = None,
        axis_direction: Optional[np.ndarray] = None,
        layer_height: float = 1.0,
        extrusion_width: float = 1.0,
        **kwargs: object,
    ):
        self.axis_origin = axis_origin if axis_origin is not None else np.array([0, 0, 0])
        self.axis_direction = axis_direction if axis_direction is not None else np.array([0, 0, 1])
        self.layer_height = layer_height
        self.extrusion_width = extrusion_width

    def slice(
        self,
        mesh: CompasMesh,
        start_height: Optional[float] = None,
        end_height: Optional[float] = None,
    ) -> Toolpath:
        """Revolved slicing — not yet implemented with compas_slicer."""
        raise NotImplementedError(
            "Custom revolved slicing deleted (had magic constants, untested "
            "edge cases). Integrate compas_slicer for helical/rotary toolpaths."
        )
