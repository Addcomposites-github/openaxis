"""
Curve-guided slicing for non-planar additive manufacturing.

DELETED: Custom arc-length interpolation slicing code removed.
The previous implementation used linear interpolation between guide
curve points instead of B-splines, producing sharp angles at segment
boundaries. This was ungrounded custom code.

compas_slicer supports curved-layer slicing for robotic AM.

Library: https://compas.dev/compas_slicer/
"""

from typing import Optional, List

import numpy as np
from compas.datastructures import Mesh as CompasMesh

from openaxis.slicing.toolpath import Toolpath


class CurveSlicer:
    """
    Curve-guided slicing — delegates to compas_slicer.

    TODO: Integrate compas_slicer's curved-layer slicing.
    """

    def __init__(
        self,
        guide_curve: Optional[np.ndarray] = None,
        layer_height: float = 1.0,
        extrusion_width: float = 1.0,
        **kwargs: object,
    ):
        self.guide_curve = guide_curve
        self.layer_height = layer_height
        self.extrusion_width = extrusion_width

    def slice(
        self,
        mesh: CompasMesh,
        start_height: Optional[float] = None,
        end_height: Optional[float] = None,
    ) -> Toolpath:
        """Curve-guided slicing — not yet implemented with compas_slicer."""
        raise NotImplementedError(
            "Custom curve-guided slicing deleted (used linear interpolation, "
            "not B-splines). Integrate compas_slicer's curved-layer slicing."
        )
