"""
Planar slicing for additive manufacturing.

This module provides planar slicing functionality that intersects a 3D mesh
with horizontal planes to generate 2D contours for each layer.

Integrates with:
- contour_offset  — proper polygon inset for inner wall generation
- infill_patterns — 8 infill pattern generators
- seam_control    — 3 seam placement modes + 4 seam shapes
- engage_disengage — lead-in/lead-out/retract moves
"""

import math
import logging
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import trimesh
from compas.datastructures import Mesh as CompasMesh
from compas.geometry import Point, Polygon

from openaxis.core.geometry import BoundingBox, GeometryConverter
from openaxis.slicing.toolpath import Toolpath, ToolpathSegment, ToolpathType, InfillPattern

# New Sprint 5 modules
from openaxis.slicing.contour_offset import (
    compute_inner_walls,
    get_infill_boundary,
)
from openaxis.slicing.infill_patterns import generate_infill
from openaxis.slicing.seam_control import apply_seam
from openaxis.slicing.engage_disengage import add_engage_disengage
from openaxis.slicing.support_generation import add_supports_to_toolpath

logger = logging.getLogger(__name__)


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
        # Advanced params (Sprint 5)
        wall_width: Optional[float] = None,
        print_speed: float = 1000.0,
        travel_speed: float = 5000.0,
        seam_mode: str = "guided",
        seam_shape: str = "straight",
        lead_in_distance: float = 0.0,
        lead_in_angle: float = 45.0,
        lead_out_distance: float = 0.0,
        lead_out_angle: float = 45.0,
        infill_pattern_name: Optional[str] = None,
    ):
        """
        Initialize the planar slicer.

        Args:
            layer_height: Height of each layer (mm)
            extrusion_width: Width of extruded bead (mm)
            wall_count: Number of perimeter walls
            infill_density: Infill density (0.0 to 1.0)
            infill_pattern: Pattern for infill (legacy enum)
            support_enabled: Whether to generate support structures
            seam_angle: Angle (degrees) from centroid for perimeter start point alignment.
            wall_width: Width of wall extrusion (defaults to extrusion_width)
            print_speed: Print speed in mm/min
            travel_speed: Travel speed in mm/min
            seam_mode: Seam placement mode ('guided', 'distributed', 'random')
            seam_shape: Seam shape ('straight', 'zigzag', 'triangular', 'sine')
            lead_in_distance: Lead-in distance (mm)
            lead_in_angle: Lead-in angle (degrees)
            lead_out_distance: Lead-out distance (mm)
            lead_out_angle: Lead-out angle (degrees)
            infill_pattern_name: String infill pattern name (overrides infill_pattern enum)
        """
        self.layer_height = layer_height
        self.extrusion_width = extrusion_width
        self.wall_count = wall_count
        self.infill_density = infill_density
        self.infill_pattern = infill_pattern
        self.support_enabled = support_enabled
        self.seam_angle = seam_angle
        self.wall_width = wall_width or extrusion_width
        self.print_speed = print_speed
        self.travel_speed = travel_speed
        self.seam_mode = seam_mode
        self.seam_shape = seam_shape
        self.lead_in_distance = lead_in_distance
        self.lead_in_angle = lead_in_angle
        self.lead_out_distance = lead_out_distance
        self.lead_out_angle = lead_out_angle

        # Resolve infill pattern name to string for new infill_patterns module
        if infill_pattern_name:
            self.infill_pattern_str = infill_pattern_name
        else:
            # Map legacy enum to new pattern string
            _pattern_map = {
                InfillPattern.LINES: "grid",
                InfillPattern.GRID: "grid",
                InfillPattern.TRIANGLES: "triangles",
                InfillPattern.HEXAGONS: "hexgrid",
                InfillPattern.CONCENTRIC: "offset",
                InfillPattern.ZIGZAG: "zigzag",
            }
            self.infill_pattern_str = _pattern_map.get(infill_pattern, "grid")

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

        logger.info(
            f"Slicing {num_layers} layers, pattern={self.infill_pattern_str}, "
            f"walls={self.wall_count}, density={self.infill_density:.1%}"
        )

        # Process each layer
        for layer_idx, z_height in enumerate(slice_heights):
            layer_segments = self._slice_layer(tmesh, z_height, layer_idx, num_layers)
            for seg in layer_segments:
                toolpath.add_segment(seg)

        # Add support structures if enabled
        if self.support_enabled:
            self.add_supports(mesh, toolpath)

        return toolpath

    def _slice_layer(
        self,
        mesh: trimesh.Trimesh,
        z_height: float,
        layer_index: int,
        total_layers: int = 100,
    ) -> List[ToolpathSegment]:
        """
        Slice mesh at a specific Z height and generate toolpath segments.

        Args:
            mesh: Trimesh mesh to slice
            z_height: Z coordinate of slice plane
            layer_index: Index of this layer
            total_layers: Total number of layers (for seam distribution)

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

                # Convert to 2D polygon for the new modules
                contour_2d = [(float(v[0]), float(v[1])) for v in vertices]

                # ── Perimeter walls (using contour_offset) ──
                perimeter_segments = self._generate_perimeters_advanced(
                    contour_2d, z_height, layer_index, total_layers
                )
                segments.extend(perimeter_segments)

                # ── Infill (using infill_patterns module) ──
                if entity_idx == 0 and self.infill_density > 0:
                    infill_segments = self._generate_infill_advanced(
                        contour_2d, z_height, layer_index
                    )
                    segments.extend(infill_segments)

        except Exception as e:
            # If slicing fails for this layer, return empty list
            # This can happen at the very top/bottom of the mesh
            logger.debug(f"Layer {layer_index} slice failed: {e}")

        return segments

    def _generate_perimeters_advanced(
        self,
        contour_2d: List[Tuple[float, float]],
        z_height: float,
        layer_index: int,
        total_layers: int,
    ) -> List[ToolpathSegment]:
        """
        Generate perimeter walls using proper contour offset.

        Uses contour_offset.compute_inner_walls() for accurate polygon inset,
        seam_control.apply_seam() for seam placement/shaping, and
        engage_disengage for lead-in/lead-out.
        """
        segments = []

        # Outer wall = original contour
        all_walls = [contour_2d]

        # Inner walls via polygon offset
        if self.wall_count > 1:
            inner_walls = compute_inner_walls(
                contour_2d,
                wall_count=self.wall_count - 1,
                wall_width=self.wall_width,
            )
            all_walls.extend(inner_walls)

        # Process each wall
        for wall_idx, wall in enumerate(all_walls):
            if len(wall) < 3:
                continue

            # Apply seam control — rotate start point and shape
            seamed = apply_seam(
                wall,
                mode=self.seam_mode,
                shape=self.seam_shape,
                layer=layer_index,
                angle_deg=self.seam_angle,
                total_layers=total_layers,
            )

            # Convert to 3D points
            points_3d = [(x, y, z_height) for (x, y) in seamed]

            # Close the loop
            if len(points_3d) > 2:
                points_3d.append(points_3d[0])

            # Apply engage/disengage if configured
            if self.lead_in_distance > 0 or self.lead_out_distance > 0:
                points_3d = add_engage_disengage(
                    points_3d,
                    lead_in_distance=self.lead_in_distance,
                    lead_in_angle=self.lead_in_angle,
                    lead_out_distance=self.lead_out_distance,
                    lead_out_angle=self.lead_out_angle,
                )

            # Convert to COMPAS Points for ToolpathSegment
            compas_points = [Point(p[0], p[1], p[2]) for p in points_3d]

            if len(compas_points) < 2:
                continue

            # Perimeter speed (slightly slower than infill)
            perimeter_speed = self.print_speed * 0.8

            segment = ToolpathSegment(
                points=compas_points,
                type=ToolpathType.PERIMETER,
                layer_index=layer_index,
                extrusion_width=self.wall_width if wall_idx > 0 else self.extrusion_width,
                speed=perimeter_speed,
                flow_rate=1.0,
                direction="cw",
            )
            segments.append(segment)

        return segments

    def _generate_infill_advanced(
        self,
        contour_2d: List[Tuple[float, float]],
        z_height: float,
        layer_index: int,
    ) -> List[ToolpathSegment]:
        """
        Generate infill using the infill_patterns module.

        Uses contour_offset.get_infill_boundary() to find the innermost
        wall boundary, then dispatches to generate_infill() with the
        selected pattern.
        """
        segments = []

        # Get the infill boundary (inside all walls)
        infill_boundary = get_infill_boundary(
            contour_2d,
            wall_count=self.wall_count,
            wall_width=self.wall_width,
        )

        # Fallback to original contour if offset fails
        if infill_boundary is None or len(infill_boundary) < 3:
            infill_boundary = contour_2d

        # Calculate spacing from density
        if self.infill_density <= 0:
            return segments
        spacing = self.extrusion_width / max(self.infill_density, 0.01)

        # Generate infill paths
        try:
            infill_polylines = generate_infill(
                polygon=infill_boundary,
                pattern=self.infill_pattern_str,
                spacing=spacing,
                layer=layer_index,
            )
        except Exception as e:
            logger.debug(f"Infill generation failed for layer {layer_index}: {e}")
            # Fallback to simple grid
            infill_polylines = generate_infill(
                polygon=infill_boundary,
                pattern="grid",
                spacing=spacing,
                layer=layer_index,
            )

        # Convert each polyline to a ToolpathSegment
        for polyline in infill_polylines:
            if len(polyline) < 2:
                continue

            # Convert 2D polyline to 3D
            points_3d = [(x, y, z_height) for (x, y) in polyline]
            compas_points = [Point(p[0], p[1], p[2]) for p in points_3d]

            segment = ToolpathSegment(
                points=compas_points,
                type=ToolpathType.INFILL,
                layer_index=layer_index,
                extrusion_width=self.extrusion_width,
                speed=self.print_speed,
                flow_rate=1.0,
            )
            segments.append(segment)

        return segments

    # ── Legacy methods (kept for backward compatibility) ──

    def _generate_perimeters(
        self,
        vertices: np.ndarray,
        z_height: float,
        layer_index: int,
    ) -> List[ToolpathSegment]:
        """
        Generate perimeter walls from a 2D contour (legacy method).

        This is the original simple implementation kept for reference.
        The active code uses _generate_perimeters_advanced().
        """
        segments = []

        for wall_idx in range(self.wall_count):
            offset = wall_idx * self.extrusion_width
            points = []
            for vertex in vertices:
                x, y = vertex[0], vertex[1]
                points.append(Point(x, y, z_height))

            if len(points) < 2:
                continue

            # Seam alignment
            if len(points) >= 3:
                cx = sum(p.x for p in points) / len(points)
                cy = sum(p.y for p in points) / len(points)

                best_idx = 0
                best_angle_diff = float("inf")
                seam_rad = math.radians(self.seam_angle)
                for pi, p in enumerate(points):
                    angle = math.atan2(p.y - cy, p.x - cx)
                    diff = abs(angle - seam_rad)
                    if diff > math.pi:
                        diff = 2 * math.pi - diff
                    if diff < best_angle_diff:
                        best_angle_diff = diff
                        best_idx = pi

                if best_idx > 0:
                    points = points[best_idx:] + points[:best_idx]

            if len(points) > 2:
                points.append(points[0])

            segment = ToolpathSegment(
                points=points,
                type=ToolpathType.PERIMETER,
                layer_index=layer_index,
                extrusion_width=self.extrusion_width,
                speed=40.0,
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
        Generate infill pattern inside a contour (legacy method).

        This is the original simple implementation kept for reference.
        The active code uses _generate_infill_advanced().
        """
        segments = []
        min_x, min_y = vertices.min(axis=0)
        max_x, max_y = vertices.max(axis=0)
        spacing = self.extrusion_width / self.infill_density

        if self.infill_pattern == InfillPattern.LINES:
            if layer_index % 2 == 0:
                y = min_y
                while y <= max_y:
                    points = [Point(min_x, y, z_height), Point(max_x, y, z_height)]
                    segment = ToolpathSegment(
                        points=points,
                        type=ToolpathType.INFILL,
                        layer_index=layer_index,
                        extrusion_width=self.extrusion_width,
                        speed=60.0,
                        flow_rate=1.0,
                    )
                    segments.append(segment)
                    y += spacing
            else:
                x = min_x
                while x <= max_x:
                    points = [Point(x, min_y, z_height), Point(x, max_y, z_height)]
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

        return segments

    def add_supports(
        self,
        mesh: CompasMesh,
        toolpath: Toolpath,
        threshold_angle: float = 45.0,
        support_density: float = 0.15,
    ) -> int:
        """
        Add support structures to the toolpath.

        Uses trimesh face-normal analysis to detect overhanging regions and
        generates columnar line-fill supports from the build plate up to
        the overhang.  See ``support_generation.py`` for implementation.

        Args:
            mesh: Original COMPAS mesh
            toolpath: Toolpath to add supports to
            threshold_angle: overhang angle threshold in degrees (default 45)
            support_density: infill density for support (default 15%)

        Returns:
            Number of support segments added (0 if supports disabled).
        """
        if not self.support_enabled:
            return 0

        # Convert to trimesh for face-normal analysis
        tmesh = GeometryConverter.compas_to_trimesh(mesh)

        count = add_supports_to_toolpath(
            tmesh,
            toolpath,
            threshold_angle=threshold_angle,
            support_density=support_density,
        )
        logger.info("Support generation: added %d segments", count)
        return count
