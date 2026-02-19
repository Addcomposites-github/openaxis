"""
Radial slicing for cylindrical substrate toolpaths.

DELETED: Custom circle-generation slicing code removed.
While the parametric circle math was correct, this was custom code
that should be handled by compas_slicer or a cited algorithm.

Library: https://compas.dev/compas_slicer/
"""

from typing import Optional

from compas.datastructures import Mesh as CompasMesh

from openaxis.slicing.toolpath import Toolpath


class RadialSlicer:
    """
    Radial slicing — delegates to compas_slicer.

    TODO: Integrate compas_slicer for radial/cylindrical toolpaths.
    """

    def __init__(
        self,
        radius_start: float = 10.0,
        radius_end: float = 50.0,
        layer_height: float = 1.0,
        extrusion_width: float = 1.0,
        **kwargs: object,
    ):
        self.radius_start = radius_start
        self.radius_end = radius_end
        self.layer_height = layer_height
        self.extrusion_width = extrusion_width

    def slice(
        self,
        mesh: CompasMesh,
        start_height: Optional[float] = None,
        end_height: Optional[float] = None,
    ) -> Toolpath:
        """Radial slicing — not yet implemented with compas_slicer."""
        raise NotImplementedError(
            "Custom radial slicing deleted. "
            "Integrate compas_slicer for cylindrical/radial toolpaths."
        )
