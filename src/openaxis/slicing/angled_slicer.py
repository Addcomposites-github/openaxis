"""
Angled slicing for non-planar additive manufacturing.

DELETED: Custom rotation-based slicing code removed. The previous
implementation rotated a mesh by -slice_angle, performed planar slicing
with trimesh, then rotated waypoints back. While the math (rotation
matrices) was correct, this was custom code without research validation.

compas_slicer provides non-planar slicing capabilities designed for
robotic additive manufacturing.

Library: https://compas.dev/compas_slicer/
"""

from typing import Optional

from compas.datastructures import Mesh as CompasMesh

from openaxis.slicing.toolpath import Toolpath


class AngledSlicer:
    """
    Angled slicing — delegates to compas_slicer.

    TODO: Integrate compas_slicer's non-planar slicing capabilities.
    """

    def __init__(
        self,
        slice_angle: float = 30.0,
        layer_height: float = 1.0,
        extrusion_width: float = 1.0,
        **kwargs: object,
    ):
        self.slice_angle = slice_angle
        self.layer_height = layer_height
        self.extrusion_width = extrusion_width

    def slice(
        self,
        mesh: CompasMesh,
        start_height: Optional[float] = None,
        end_height: Optional[float] = None,
    ) -> Toolpath:
        """Angled slicing — not yet implemented with compas_slicer."""
        raise NotImplementedError(
            "Custom angled slicing deleted. "
            "Integrate compas_slicer's non-planar slicing capabilities."
        )
