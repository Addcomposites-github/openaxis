"""
Radial slicing for cylindrical substrate toolpaths.

Generates concentric circular toolpaths at each layer height, suitable for
printing onto cylindrical substrates or building rotationally symmetric parts.
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


class RadialSlicer:
    """
    Slicer that generates concentric circular toolpaths.

    For each layer, concentric circles are created starting from
    *radius_start* and expanding outward with spacing equal to
    *extrusion_width*, until *radius_end* is reached.  This is useful
    for cylindrical or disk-shaped deposits.
    """

    def __init__(
        self,
        layer_height: float = 1.0,
        extrusion_width: float = 1.0,
        center: Tuple[float, float] = (0.0, 0.0),
        radius_start: float = 5.0,
        radius_end: float = 50.0,
        points_per_circle: int = 64,
    ):
        """
        Initialize the radial slicer.

        Args:
            layer_height: Height of each layer in mm.
            extrusion_width: Width of extruded bead in mm.
            center: (x, y) centre of the concentric circles.
            radius_start: Starting radius in mm.
            radius_end: Ending (outermost) radius in mm.
            points_per_circle: Number of discrete points per circle.
        """
        self.layer_height = layer_height
        self.extrusion_width = extrusion_width
        self.center = center
        self.radius_start = radius_start
        self.radius_end = radius_end
        self.points_per_circle = points_per_circle

    def slice(self, mesh) -> Toolpath:
        """
        Generate concentric radial toolpaths from the mesh bounding box.

        The Z range is derived from the mesh.  At each layer height,
        concentric circles are emitted from *radius_start* outward.

        Args:
            mesh: COMPAS Mesh (used to determine Z range).

        Returns:
            Toolpath containing concentric circle segments.
        """
        tmesh = GeometryConverter.compas_to_trimesh(mesh)
        z_min = float(tmesh.bounds[0][2])
        z_max = float(tmesh.bounds[1][2])
        num_layers = max(1, int(math.ceil((z_max - z_min) / self.layer_height)))

        logger.info(
            "RadialSlicer: center=(%.1f,%.1f), r=[%.1f,%.1f], layers=%d",
            self.center[0], self.center[1],
            self.radius_start, self.radius_end, num_layers,
        )

        toolpath = Toolpath(
            layer_height=self.layer_height,
            total_layers=num_layers,
            process_type="additive",
            metadata={"slicer": "radial"},
        )

        for layer_idx in range(num_layers):
            z_height = z_min + layer_idx * self.layer_height
            segments = self._generate_layer(z_height, layer_idx)
            for seg in segments:
                toolpath.add_segment(seg)

        return toolpath

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_layer(
        self,
        z_height: float,
        layer_index: int,
    ) -> List[ToolpathSegment]:
        """Create concentric circles for a single layer."""
        segments: List[ToolpathSegment] = []
        cx, cy = self.center

        radius = self.radius_start
        ring_idx = 0
        while radius <= self.radius_end:
            points = self._circle_points(cx, cy, radius, z_height)

            # Outermost and innermost rings are perimeters; middle rings are infill
            if ring_idx == 0 or radius + self.extrusion_width > self.radius_end:
                seg_type = ToolpathType.PERIMETER
            else:
                seg_type = ToolpathType.INFILL

            segments.append(ToolpathSegment(
                points=points,
                type=seg_type,
                layer_index=layer_index,
                extrusion_width=self.extrusion_width,
            ))

            radius += self.extrusion_width
            ring_idx += 1

        return segments

    def _circle_points(
        self,
        cx: float,
        cy: float,
        radius: float,
        z: float,
    ) -> List[Point]:
        """Generate evenly spaced points on a circle and close the loop."""
        angles = np.linspace(0, 2 * math.pi, self.points_per_circle, endpoint=False)
        points = [
            Point(
                cx + radius * math.cos(a),
                cy + radius * math.sin(a),
                z,
            )
            for a in angles
        ]
        # Close the loop
        points.append(points[0])
        return points
