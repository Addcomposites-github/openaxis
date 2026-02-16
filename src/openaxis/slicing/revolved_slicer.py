"""
Revolved slicing for rotational parts with a positioner.

Generates helical toolpaths wound around a user-defined axis, suitable for
deposition onto parts mounted on a rotary positioner (e.g. pipes, shafts).
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


class RevolvedSlicer:
    """
    Slicer that generates helical toolpaths around a rotation axis.

    For each layer the slicer creates a helix of one full revolution at
    the current build radius, then steps outward by *layer_height* for
    the next layer.  This produces a spiral winding pattern commonly used
    in rotary additive manufacturing.
    """

    def __init__(
        self,
        layer_height: float = 1.0,
        extrusion_width: float = 1.0,
        axis: Optional[List[float]] = None,
        center: Optional[List[float]] = None,
        points_per_revolution: int = 72,
    ):
        """
        Initialize the revolved slicer.

        Args:
            layer_height: Height of each layer in mm (radial step).
            extrusion_width: Width of extruded bead in mm.
            axis: Rotation axis as [x, y, z] (default [0, 0, 1]).
            center: Centre point of the rotation as [x, y, z] (default origin).
            points_per_revolution: Discrete points per full revolution.
        """
        self.layer_height = layer_height
        self.extrusion_width = extrusion_width
        self.axis = np.array(axis or [0.0, 0.0, 1.0], dtype=float)
        self.center = np.array(center or [0.0, 0.0, 0.0], dtype=float)
        self.points_per_revolution = points_per_revolution

        # Normalise axis
        norm = np.linalg.norm(self.axis)
        if norm > 0:
            self.axis = self.axis / norm
        else:
            self.axis = np.array([0.0, 0.0, 1.0])

    def slice(self, mesh) -> Toolpath:
        """
        Generate helical toolpaths from the mesh geometry.

        The Z (along-axis) range and radial extent are derived from the
        mesh bounding box.

        Args:
            mesh: COMPAS Mesh to slice.

        Returns:
            Toolpath containing helical segments.
        """
        tmesh = GeometryConverter.compas_to_trimesh(mesh)

        # Project vertices onto the axis to find axial range
        verts = tmesh.vertices - self.center
        axial_proj = verts @ self.axis
        z_min = float(axial_proj.min())
        z_max = float(axial_proj.max())

        # Compute radial distances from axis
        axial_components = np.outer(axial_proj, self.axis)
        radial_vecs = verts - axial_components
        radial_dists = np.linalg.norm(radial_vecs, axis=1)
        r_min = float(radial_dists.min())
        r_max = float(radial_dists.max())

        if r_max < self.extrusion_width:
            r_max = self.extrusion_width

        num_layers = max(1, int(math.ceil((r_max - r_min) / self.layer_height)))

        logger.info(
            "RevolvedSlicer: axis=%s, r=[%.2f,%.2f], z=[%.2f,%.2f], layers=%d",
            self.axis.tolist(), r_min, r_max, z_min, z_max, num_layers,
        )

        toolpath = Toolpath(
            layer_height=self.layer_height,
            total_layers=num_layers,
            process_type="additive",
            metadata={"slicer": "revolved"},
        )

        for layer_idx in range(num_layers):
            radius = r_min + layer_idx * self.layer_height
            segments = self._generate_helix(radius, z_min, z_max, layer_idx)
            for seg in segments:
                toolpath.add_segment(seg)

        return toolpath

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_helix(
        self,
        radius: float,
        z_min: float,
        z_max: float,
        layer_index: int,
    ) -> List[ToolpathSegment]:
        """Create a single helical revolution at the given radius."""
        segments: List[ToolpathSegment] = []

        # Build a local coordinate frame around the axis
        u, v = self._orthonormal_basis()

        z_span = z_max - z_min
        n_pts = self.points_per_revolution
        angles = np.linspace(0, 2 * math.pi, n_pts, endpoint=False)

        # Height advances linearly with angle for a continuous helix
        heights = np.linspace(z_min, z_min + z_span, n_pts, endpoint=False)

        points: List[Point] = []
        for angle, h in zip(angles, heights):
            # Point on circle in the local frame
            offset = radius * (math.cos(angle) * u + math.sin(angle) * v)
            pos = self.center + h * self.axis + offset
            points.append(Point(float(pos[0]), float(pos[1]), float(pos[2])))

        # Close the helix loop
        if points:
            points.append(points[0])

        # First and last layers are perimeters; inner layers are infill
        if layer_index == 0:
            seg_type = ToolpathType.PERIMETER
        else:
            seg_type = ToolpathType.INFILL

        segments.append(ToolpathSegment(
            points=points,
            type=seg_type,
            layer_index=layer_index,
            extrusion_width=self.extrusion_width,
        ))

        return segments

    def _orthonormal_basis(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return two unit vectors perpendicular to self.axis."""
        a = self.axis
        # Pick a vector not parallel to a
        if abs(np.dot(a, np.array([1, 0, 0]))) < 0.9:
            ref = np.array([1.0, 0.0, 0.0])
        else:
            ref = np.array([0.0, 1.0, 0.0])
        u = np.cross(a, ref)
        u = u / np.linalg.norm(u)
        v = np.cross(a, u)
        v = v / np.linalg.norm(v)
        return u, v
