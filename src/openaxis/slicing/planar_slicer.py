"""
Planar slicing for additive manufacturing.

This module provides planar slicing functionality that intersects a 3D mesh
with horizontal planes to generate 2D contours for each layer.
"""

import math
from typing import List, Optional, Tuple

import numpy as np
import trimesh
from compas.datastructures import Mesh as CompasMesh
from compas.geometry import Point, Polygon

from openaxis.core.geometry import BoundingBox, GeometryConverter
from openaxis.slicing.toolpath import Toolpath, ToolpathSegment, ToolpathType, InfillPattern


class PlanarSlicer:
    """
    Planar slicing engine for generating layer-by-layer toolpaths.

    This slicer intersects a 3D mesh with horizontal planes to create
    2D contours, then generates toolpaths with perimeters and infill.
    """

    def __init__(
        self,
        layer_height: float = 1.0,
        extrusion_width: float = 1.0,
        wall_count: int = 2,
        infill_density: float = 0.2,
        infill_pattern: InfillPattern = InfillPattern.LINES,
        support_enabled: bool = False,
        seam_angle: float = 0.0,
    ):
        """
        Initialize the planar slicer.

        Args:
            layer_height: Height of each layer (mm)
            extrusion_width: Width of extruded bead (mm)
            wall_count: Number of perimeter walls
            infill_density: Infill density (0.0 to 1.0)
            infill_pattern: Pattern for infill
            support_enabled: Whether to generate support structures
            seam_angle: Angle (radians) from centroid for perimeter start point alignment.
                        0.0 = positive X direction. Ensures consistent seam across layers.
        """
        self.layer_height = layer_height
        self.extrusion_width = extrusion_width
        self.wall_count = wall_count
        self.infill_density = infill_density
        self.infill_pattern = infill_pattern
        self.support_enabled = support_enabled
        self.seam_angle = seam_angle

    def slice(
        self,
        mesh: CompasMesh,
        start_height: Optional[float] = None,
        end_height: Optional[float] = None,
    ) -> Toolpath:
        """
        Slice a mesh into layers and generate toolpath.

        Args:
            mesh: COMPAS mesh to slice
            start_height: Starting Z height (default: mesh min Z)
            end_height: Ending Z height (default: mesh max Z)

        Returns:
            Complete toolpath with all layers
        """
        # Convert to trimesh for slicing operations
        tmesh = GeometryConverter.compas_to_trimesh(mesh)

        # Get bounding box
        bbox = BoundingBox.from_mesh(mesh)
        min_pt = bbox.xmin, bbox.ymin, bbox.zmin
        max_pt = bbox.xmax, bbox.ymax, bbox.zmax

        # Determine slicing range
        if start_height is None:
            start_height = min_pt[2]
        if end_height is None:
            end_height = max_pt[2]

        # Generate slice heights
        num_layers = int(np.ceil((end_height - start_height) / self.layer_height))
        slice_heights = [
            start_height + i * self.layer_height for i in range(num_layers)
        ]

        # Create toolpath
        toolpath = Toolpath(
            layer_height=self.layer_height,
            total_layers=num_layers,
            process_type="additive",
        )

        # Process each layer
        for layer_idx, z_height in enumerate(slice_heights):
            layer_segments = self._slice_layer(tmesh, z_height, layer_idx)
            for seg in layer_segments:
                toolpath.add_segment(seg)

        return toolpath

    def _slice_layer(
        self,
        mesh: trimesh.Trimesh,
        z_height: float,
        layer_index: int,
    ) -> List[ToolpathSegment]:
        """
        Slice mesh at a specific Z height and generate toolpath segments.

        Args:
            mesh: Trimesh mesh to slice
            z_height: Z coordinate of slice plane
            layer_index: Index of this layer

        Returns:
            List of toolpath segments for this layer
        """
        segments = []

        try:
            # Get 2D cross-section at this height
            slice_2d = mesh.section(
                plane_origin=[0, 0, z_height], plane_normal=[0, 0, 1]
            )

            if slice_2d is None:
                return segments

            # Convert to 2D (replaces deprecated to_planar)
            path_2d, transform = slice_2d.to_2D()

            if path_2d is None:
                return segments

            # Process each entity (discrete curve segment) in the path
            for entity_idx, entity in enumerate(path_2d.entities):
                # Get the vertices for this entity
                vertices = path_2d.vertices[entity.points]

                # Skip if too few points
                if len(vertices) < 3:
                    continue

                # Generate perimeter walls
                perimeter_segments = self._generate_perimeters(
                    vertices, z_height, layer_index
                )
                segments.extend(perimeter_segments)

                # Generate infill (only for first entity)
                if entity_idx == 0 and self.infill_density > 0:
                    infill_segments = self._generate_infill(
                        vertices, z_height, layer_index
                    )
                    segments.extend(infill_segments)

        except Exception as e:
            # If slicing fails for this layer, return empty list
            # This can happen at the very top/bottom of the mesh
            pass

        return segments

    def _generate_perimeters(
        self,
        vertices: np.ndarray,
        z_height: float,
        layer_index: int,
    ) -> List[ToolpathSegment]:
        """
        Generate perimeter walls from a 2D contour.

        Args:
            vertices: 2D vertices of the contour
            z_height: Z coordinate
            layer_index: Layer index

        Returns:
            List of perimeter segments
        """
        segments = []

        # Generate multiple walls by offsetting inward
        for wall_idx in range(self.wall_count):
            # For simplicity, we'll just use the same contour
            # In a production slicer, you'd offset the contour inward
            offset = wall_idx * self.extrusion_width

            # Convert vertices to 3D points
            points = []
            for vertex in vertices:
                # Simple inward offset (this is a basic approximation)
                x, y = vertex[0], vertex[1]
                points.append(Point(x, y, z_height))

            if len(points) < 2:
                continue

            # Seam alignment: rotate the point list so the point nearest
            # to self.seam_angle (relative to the contour centroid) comes first.
            # This ensures every layer's perimeter starts at the same angular
            # position, creating a consistent seam line.
            if len(points) >= 3:
                cx = sum(p.x for p in points) / len(points)
                cy = sum(p.y for p in points) / len(points)

                best_idx = 0
                best_angle_diff = float("inf")
                for pi, p in enumerate(points):
                    angle = math.atan2(p.y - cy, p.x - cx)
                    diff = abs(angle - self.seam_angle)
                    # Wrap to [0, pi]
                    if diff > math.pi:
                        diff = 2 * math.pi - diff
                    if diff < best_angle_diff:
                        best_angle_diff = diff
                        best_idx = pi

                # Rotate so the seam-aligned vertex is first
                if best_idx > 0:
                    points = points[best_idx:] + points[:best_idx]

            # Close the loop
            if len(points) > 2:
                points.append(points[0])

            segment = ToolpathSegment(
                points=points,
                type=ToolpathType.PERIMETER,
                layer_index=layer_index,
                extrusion_width=self.extrusion_width,
                speed=40.0,  # Slower speed for perimeters
                flow_rate=1.0,
            )
            segments.append(segment)

        return segments

    def _generate_infill(
        self,
        vertices: np.ndarray,
        z_height: float,
        layer_index: int,
    ) -> List[ToolpathSegment]:
        """
        Generate infill pattern inside a contour.

        Args:
            vertices: 2D vertices defining the boundary
            z_height: Z coordinate
            layer_index: Layer index

        Returns:
            List of infill segments
        """
        segments = []

        # Get bounding box of the contour
        min_x, min_y = vertices.min(axis=0)
        max_x, max_y = vertices.max(axis=0)

        # Calculate infill line spacing
        spacing = self.extrusion_width / self.infill_density

        # Generate lines infill (simplest pattern)
        if self.infill_pattern == InfillPattern.LINES:
            # Alternate direction each layer
            if layer_index % 2 == 0:
                # Horizontal lines
                y = min_y
                while y <= max_y:
                    points = [
                        Point(min_x, y, z_height),
                        Point(max_x, y, z_height),
                    ]

                    segment = ToolpathSegment(
                        points=points,
                        type=ToolpathType.INFILL,
                        layer_index=layer_index,
                        extrusion_width=self.extrusion_width,
                        speed=60.0,  # Faster speed for infill
                        flow_rate=1.0,
                    )
                    segments.append(segment)
                    y += spacing
            else:
                # Vertical lines
                x = min_x
                while x <= max_x:
                    points = [
                        Point(x, min_y, z_height),
                        Point(x, max_y, z_height),
                    ]

                    segment = ToolpathSegment(
                        points=points,
                        type=ToolpathType.INFILL,
                        layer_index=layer_index,
                        extrusion_width=self.extrusion_width,
                        speed=60.0,
                        flow_rate=1.0,
                    )
                    segments.append(segment)
                    x += spacing

        # For other patterns, implement similar logic
        # (GRID, TRIANGLES, etc.)

        return segments

    def add_supports(self, mesh: CompasMesh, toolpath: Toolpath) -> None:
        """
        Add support structures to the toolpath.

        Args:
            mesh: Original mesh
            toolpath: Toolpath to add supports to
        """
        if not self.support_enabled:
            return

        # TODO: Implement support generation
        # This would identify overhangs and generate support structures
        pass
