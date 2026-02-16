"""
Angled slicing for non-planar additive manufacturing.

Rotates the mesh by -slice_angle around X, performs planar slicing,
then rotates all waypoints back to the original orientation.
"""

import logging
import math
from typing import List

import numpy as np
import trimesh
from compas.geometry import Point

from openaxis.core.geometry import BoundingBox, GeometryConverter
from openaxis.slicing.toolpath import Toolpath, ToolpathSegment, ToolpathType

logger = logging.getLogger(__name__)


class AngledSlicer:
    """Slicer that cuts layers at an angle from horizontal.

    An angle of 0 degrees produces standard planar slicing.
    """

    def __init__(
        self,
        layer_height: float = 1.0,
        extrusion_width: float = 1.0,
        slice_angle: float = 0.0,
        wall_count: int = 2,
        infill_density: float = 0.2,
    ):
        """Initialize the angled slicer.

        Args:
            layer_height: Height of each layer in mm.
            extrusion_width: Width of extruded bead in mm.
            slice_angle: Angle in degrees from horizontal (0 = planar).
            wall_count: Number of perimeter walls.
            infill_density: Infill density from 0.0 to 1.0.
        """
        self.layer_height = layer_height
        self.extrusion_width = extrusion_width
        self.slice_angle = slice_angle
        self.wall_count = wall_count
        self.infill_density = infill_density

    def slice(self, mesh) -> Toolpath:
        """Slice a mesh at the configured angle and return a Toolpath."""
        tmesh = GeometryConverter.compas_to_trimesh(mesh)
        angle_rad = math.radians(self.slice_angle)

        # Build rotation matrix around X axis by -angle
        rot_matrix = trimesh.transformations.rotation_matrix(-angle_rad, [1, 0, 0])
        rotated = tmesh.copy()
        rotated.apply_transform(rot_matrix)

        # Determine Z range of the rotated mesh
        z_min = float(rotated.bounds[0][2])
        z_max = float(rotated.bounds[1][2])
        num_layers = max(1, int(math.ceil((z_max - z_min) / self.layer_height)))

        logger.info(
            "AngledSlicer: angle=%.1f deg, layers=%d, z_range=[%.2f, %.2f]",
            self.slice_angle, num_layers, z_min, z_max,
        )

        # Inverse rotation to map points back to original frame
        inv_matrix = trimesh.transformations.rotation_matrix(angle_rad, [1, 0, 0])

        toolpath = Toolpath(
            layer_height=self.layer_height,
            total_layers=num_layers,
            process_type="additive",
            metadata={"slicer": "angled", "slice_angle": self.slice_angle},
        )

        for layer_idx in range(num_layers):
            z_height = z_min + layer_idx * self.layer_height
            segments = self._slice_layer(rotated, z_height, layer_idx, inv_matrix)
            for seg in segments:
                toolpath.add_segment(seg)

        return toolpath

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _slice_layer(
        self,
        tmesh: trimesh.Trimesh,
        z_height: float,
        layer_index: int,
        inv_matrix: np.ndarray,
    ) -> List[ToolpathSegment]:
        """Slice at *z_height* in rotated space, then rotate points back."""
        segments: List[ToolpathSegment] = []

        try:
            section = tmesh.section(
                plane_origin=[0, 0, z_height],
                plane_normal=[0, 0, 1],
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

                # Lift back to 3D in rotated space
                pts_3d = np.column_stack([
                    verts_2d,
                    np.zeros(len(verts_2d)),
                    np.ones(len(verts_2d)),
                ])
                pts_3d = (inv_transform @ pts_3d.T).T[:, :3]

                # Rotate back to original frame
                pts_h = np.column_stack([pts_3d, np.ones(len(pts_3d))])
                pts_original = (inv_matrix @ pts_h.T).T[:, :3]

                # Perimeter segments
                perimeter_points = [Point(float(p[0]), float(p[1]), float(p[2])) for p in pts_original]
                perimeter_points.append(perimeter_points[0])  # close loop
                segments.append(ToolpathSegment(
                    points=perimeter_points,
                    type=ToolpathType.PERIMETER,
                    layer_index=layer_index,
                    extrusion_width=self.extrusion_width,
                ))

                # Simple infill lines
                if self.infill_density > 0:
                    infill_segs = self._generate_infill(
                        pts_original, layer_index, inv_matrix,
                    )
                    segments.extend(infill_segs)

        except Exception as exc:
            logger.debug("AngledSlicer layer %d failed: %s", layer_index, exc)

        return segments

    def _generate_infill(
        self,
        pts: np.ndarray,
        layer_index: int,
        inv_matrix: np.ndarray,
    ) -> List[ToolpathSegment]:
        """Generate simple line infill inside the contour bounds."""
        segments: List[ToolpathSegment] = []
        if self.infill_density <= 0:
            return segments

        x_min, y_min, z_min = pts.min(axis=0)
        x_max, y_max, z_max = pts.max(axis=0)
        spacing = self.extrusion_width / max(self.infill_density, 0.01)
        z_avg = float(pts[:, 2].mean())

        if layer_index % 2 == 0:
            y = y_min
            while y <= y_max:
                line_pts = [Point(float(x_min), float(y), z_avg),
                            Point(float(x_max), float(y), z_avg)]
                segments.append(ToolpathSegment(
                    points=line_pts,
                    type=ToolpathType.INFILL,
                    layer_index=layer_index,
                    extrusion_width=self.extrusion_width,
                ))
                y += spacing
        else:
            x = x_min
            while x <= x_max:
                line_pts = [Point(float(x), float(y_min), z_avg),
                            Point(float(x), float(y_max), z_avg)]
                segments.append(ToolpathSegment(
                    points=line_pts,
                    type=ToolpathType.INFILL,
                    layer_index=layer_index,
                    extrusion_width=self.extrusion_width,
                ))
                x += spacing

        return segments
