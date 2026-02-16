"""
Curve-guided slicing for non-planar additive manufacturing.

Generates toolpath layers that follow a user-defined guide curve.  At each
step along the curve a slice plane is constructed perpendicular to the
local tangent, and the mesh cross-section at that plane is collected.
"""

import logging
import math
from typing import List, Optional, Tuple

import numpy as np
import trimesh
from compas.geometry import Point

from openaxis.core.geometry import BoundingBox, GeometryConverter
from openaxis.slicing.toolpath import Toolpath, ToolpathSegment, ToolpathType

logger = logging.getLogger(__name__)


class CurveSlicer:
    """
    Slicer where layers follow a guide curve.

    A guide curve is defined by a sequence of 3D points.  The slicer
    walks along the curve in steps of *layer_height*, constructs a plane
    perpendicular to the local tangent at each step, slices the mesh
    with that plane, and collects the resulting contours as toolpath
    segments.
    """

    def __init__(
        self,
        layer_height: float = 1.0,
        extrusion_width: float = 1.0,
        guide_points: Optional[List[List[float]]] = None,
    ):
        """
        Initialize the curve slicer.

        Args:
            layer_height: Spacing between slices along the curve in mm.
            extrusion_width: Width of extruded bead in mm.
            guide_points: Ordered list of [x, y, z] points defining the
                guide curve.  Must contain at least two points.
        """
        self.layer_height = layer_height
        self.extrusion_width = extrusion_width
        self.guide_points = np.array(guide_points or [[0, 0, 0], [0, 0, 100]])

        if len(self.guide_points) < 2:
            raise ValueError("guide_points must contain at least two points.")

    def slice(self, mesh) -> Toolpath:
        """
        Slice a mesh along the guide curve.

        Args:
            mesh: COMPAS Mesh to slice.

        Returns:
            Toolpath with contour segments at each slice plane.
        """
        tmesh = GeometryConverter.compas_to_trimesh(mesh)

        # Resample the guide curve at uniform spacing
        origins, normals = self._resample_curve()
        num_layers = len(origins)

        logger.info(
            "CurveSlicer: %d guide pts resampled to %d layers (spacing=%.2f mm)",
            len(self.guide_points), num_layers, self.layer_height,
        )

        toolpath = Toolpath(
            layer_height=self.layer_height,
            total_layers=num_layers,
            process_type="additive",
            metadata={"slicer": "curve"},
        )

        for layer_idx, (origin, normal) in enumerate(zip(origins, normals)):
            segments = self._slice_at_plane(tmesh, origin, normal, layer_idx)
            for seg in segments:
                toolpath.add_segment(seg)

        return toolpath

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resample_curve(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Resample the guide curve at uniform arc-length intervals.

        Returns:
            origins: (N, 3) array of slice plane origins.
            normals: (N, 3) array of slice plane normals (tangent vectors).
        """
        pts = self.guide_points.astype(float)

        # Compute cumulative arc length
        diffs = np.diff(pts, axis=0)
        seg_lengths = np.linalg.norm(diffs, axis=1)
        cum_length = np.concatenate([[0], np.cumsum(seg_lengths)])
        total_length = cum_length[-1]

        if total_length < self.layer_height:
            # Curve shorter than one layer -- just use endpoints
            tangent = pts[-1] - pts[0]
            norm = np.linalg.norm(tangent)
            if norm > 0:
                tangent = tangent / norm
            else:
                tangent = np.array([0.0, 0.0, 1.0])
            return pts[:1], tangent.reshape(1, 3)

        num_samples = max(2, int(math.ceil(total_length / self.layer_height)) + 1)
        sample_dists = np.linspace(0, total_length, num_samples)

        origins = np.zeros((num_samples, 3))
        normals = np.zeros((num_samples, 3))

        for i, d in enumerate(sample_dists):
            # Find which segment this distance falls in
            seg_idx = np.searchsorted(cum_length, d, side="right") - 1
            seg_idx = max(0, min(seg_idx, len(pts) - 2))

            # Interpolate position
            seg_start_d = cum_length[seg_idx]
            seg_len = seg_lengths[seg_idx] if seg_lengths[seg_idx] > 0 else 1e-9
            t = (d - seg_start_d) / seg_len
            t = np.clip(t, 0.0, 1.0)
            origins[i] = pts[seg_idx] + t * diffs[seg_idx]

            # Tangent = direction of current segment
            tangent = diffs[seg_idx]
            norm = np.linalg.norm(tangent)
            normals[i] = tangent / norm if norm > 0 else np.array([0, 0, 1])

        return origins, normals

    def _slice_at_plane(
        self,
        tmesh: trimesh.Trimesh,
        origin: np.ndarray,
        normal: np.ndarray,
        layer_index: int,
    ) -> List[ToolpathSegment]:
        """Slice the mesh with an arbitrary plane and collect contours."""
        segments: List[ToolpathSegment] = []

        try:
            section = tmesh.section(
                plane_origin=origin.tolist(),
                plane_normal=normal.tolist(),
            )
            if section is None:
                return segments

            path_2d, transform = section.to_2D()
            if path_2d is None:
                return segments

            inv_transform = np.linalg.inv(transform)

            for entity in path_2d.entities:
                verts_2d = path_2d.vertices[entity.points]
                if len(verts_2d) < 3:
                    continue

                # Lift back to 3D
                pts_h = np.column_stack([
                    verts_2d,
                    np.zeros(len(verts_2d)),
                    np.ones(len(verts_2d)),
                ])
                pts_3d = (inv_transform @ pts_h.T).T[:, :3]

                compas_points = [
                    Point(float(p[0]), float(p[1]), float(p[2]))
                    for p in pts_3d
                ]
                compas_points.append(compas_points[0])  # close loop

                segments.append(ToolpathSegment(
                    points=compas_points,
                    type=ToolpathType.PERIMETER,
                    layer_index=layer_index,
                    extrusion_width=self.extrusion_width,
                ))

        except Exception as exc:
            logger.debug("CurveSlicer layer %d failed: %s", layer_index, exc)

        return segments
