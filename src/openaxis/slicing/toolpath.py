"""
Toolpath data structures for representing manufacturing paths.

This module provides classes for representing and manipulating toolpaths
generated from slicing operations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

import numpy as np
from compas.geometry import Point, Vector


class ToolpathType(Enum):
    """Type of toolpath segment."""

    PERIMETER = "perimeter"  # Outer contours
    INFILL = "infill"  # Interior fill patterns
    SUPPORT = "support"  # Support structures
    TRAVEL = "travel"  # Non-printing moves
    MACHINING = "machining"  # Subtractive operations


class InfillPattern(Enum):
    """Infill pattern types."""

    LINES = "lines"  # Parallel lines
    GRID = "grid"  # Orthogonal grid
    TRIANGLES = "triangles"  # Triangular pattern
    HEXAGONS = "hexagons"  # Hexagonal pattern
    CONCENTRIC = "concentric"  # Concentric circles/polygons
    ZIGZAG = "zigzag"  # Zigzag pattern


@dataclass
class ToolpathSegment:
    """
    Represents a single segment of a toolpath.

    Attributes:
        points: List of 3D points defining the path
        type: Type of toolpath segment
        layer_index: Index of the layer this segment belongs to
        extrusion_width: Width of extruded material (mm)
        speed: Movement speed (mm/s)
        flow_rate: Material flow rate (0-1 scale)
        temperature: Process temperature (°C)
        is_retract: Whether this is a retraction move
        metadata: Additional process-specific data
    """

    points: List[Point]
    type: ToolpathType
    layer_index: int
    extrusion_width: float = 1.0
    speed: float = 50.0
    flow_rate: float = 1.0
    temperature: float = 0.0
    is_retract: bool = False
    metadata: dict = field(default_factory=dict)

    def get_length(self) -> float:
        """Calculate total length of the segment."""
        if len(self.points) < 2:
            return 0.0

        total_length = 0.0
        for i in range(len(self.points) - 1):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            dz = p2.z - p1.z
            total_length += np.sqrt(dx**2 + dy**2 + dz**2)

        return total_length

    def get_start_point(self) -> Point:
        """Get the starting point of the segment."""
        if not self.points:
            raise ValueError("Segment has no points")
        return self.points[0]

    def get_end_point(self) -> Point:
        """Get the ending point of the segment."""
        if not self.points:
            raise ValueError("Segment has no points")
        return self.points[-1]

    def reverse(self) -> "ToolpathSegment":
        """Return a new segment with reversed point order."""
        return ToolpathSegment(
            points=list(reversed(self.points)),
            type=self.type,
            layer_index=self.layer_index,
            extrusion_width=self.extrusion_width,
            speed=self.speed,
            flow_rate=self.flow_rate,
            temperature=self.temperature,
            is_retract=self.is_retract,
            metadata=self.metadata.copy(),
        )


@dataclass
class Toolpath:
    """
    Complete toolpath for a manufacturing operation.

    Attributes:
        segments: List of toolpath segments
        layer_height: Height of each layer (mm)
        total_layers: Total number of layers
        process_type: Type of manufacturing process
        material: Material being processed
        metadata: Additional toolpath metadata
    """

    segments: List[ToolpathSegment] = field(default_factory=list)
    layer_height: float = 1.0
    total_layers: int = 0
    process_type: str = "additive"
    material: str = "unknown"
    metadata: dict = field(default_factory=dict)

    def add_segment(self, segment: ToolpathSegment) -> None:
        """Add a segment to the toolpath."""
        self.segments.append(segment)
        self.total_layers = max(self.total_layers, segment.layer_index + 1)

    def get_segments_by_layer(self, layer_index: int) -> List[ToolpathSegment]:
        """Get all segments for a specific layer."""
        return [seg for seg in self.segments if seg.layer_index == layer_index]

    def get_segments_by_type(self, seg_type: ToolpathType) -> List[ToolpathSegment]:
        """Get all segments of a specific type."""
        return [seg for seg in self.segments if seg.type == seg_type]

    def get_total_length(self) -> float:
        """Calculate total toolpath length."""
        return sum(seg.get_length() for seg in self.segments)

    def get_build_time_estimate(self) -> float:
        """
        Estimate total build time in seconds.

        Assumes constant speed for each segment.
        """
        total_time = 0.0
        for seg in self.segments:
            length = seg.get_length()
            if seg.speed > 0:
                total_time += length / seg.speed

        return total_time

    def get_bounds(self) -> tuple[Point, Point]:
        """
        Get bounding box of the toolpath.

        Returns:
            Tuple of (min_point, max_point)
        """
        if not self.segments:
            raise ValueError("Toolpath has no segments")

        all_points = []
        for seg in self.segments:
            all_points.extend(seg.points)

        if not all_points:
            raise ValueError("Toolpath has no points")

        xs = [p.x for p in all_points]
        ys = [p.y for p in all_points]
        zs = [p.z for p in all_points]

        min_point = Point(min(xs), min(ys), min(zs))
        max_point = Point(max(xs), max(ys), max(zs))

        return min_point, max_point

    def optimize_segment_order(self) -> None:
        """
        Optimize segment order to minimize travel moves.

        Uses a greedy nearest-neighbor approach with bi-directional traversal.
        Also carries the end position across layers to minimize layer transitions.
        """
        if not self.segments:
            return

        # Group segments by layer
        layers: dict[int, list[ToolpathSegment]] = {}
        for seg in self.segments:
            if seg.layer_index not in layers:
                layers[seg.layer_index] = []
            layers[seg.layer_index].append(seg)

        # Optimize each layer, carrying end position across layers
        optimized_segments: list[ToolpathSegment] = []
        last_end_point: Optional[Point] = None

        for layer_idx in sorted(layers.keys()):
            layer_segs = layers[layer_idx]

            # Separate travel moves from other segments
            travel_segs = [s for s in layer_segs if s.type == ToolpathType.TRAVEL]
            other_segs = [s for s in layer_segs if s.type != ToolpathType.TRAVEL]

            if not other_segs:
                optimized_segments.extend(travel_segs)
                continue

            # Pick the best first segment: nearest to previous layer's end point
            if last_end_point is not None:
                best_first_idx = 0
                best_first_dist = float("inf")
                best_first_reversed = False
                for idx, seg in enumerate(other_segs):
                    # Check distance to start
                    start = seg.get_start_point()
                    d_start = np.sqrt(
                        (start.x - last_end_point.x) ** 2
                        + (start.y - last_end_point.y) ** 2
                        + (start.z - last_end_point.z) ** 2
                    )
                    if d_start < best_first_dist:
                        best_first_dist = d_start
                        best_first_idx = idx
                        best_first_reversed = False
                    # Check distance to end (reversed)
                    end = seg.get_end_point()
                    d_end = np.sqrt(
                        (end.x - last_end_point.x) ** 2
                        + (end.y - last_end_point.y) ** 2
                        + (end.z - last_end_point.z) ** 2
                    )
                    if d_end < best_first_dist:
                        best_first_dist = d_end
                        best_first_idx = idx
                        best_first_reversed = True

                first_seg = other_segs.pop(best_first_idx)
                if best_first_reversed:
                    first_seg = first_seg.reverse()
                ordered = [first_seg]
            else:
                ordered = [other_segs.pop(0)]

            # Greedy nearest neighbor with bi-directional check
            while other_segs:
                current_end = ordered[-1].get_end_point()
                nearest_idx = 0
                min_dist = float("inf")
                use_reversed = False

                for idx, seg in enumerate(other_segs):
                    # Check distance to start point (normal direction)
                    start = seg.get_start_point()
                    dx = start.x - current_end.x
                    dy = start.y - current_end.y
                    dz = start.z - current_end.z
                    dist_start = np.sqrt(dx**2 + dy**2 + dz**2)

                    if dist_start < min_dist:
                        min_dist = dist_start
                        nearest_idx = idx
                        use_reversed = False

                    # Check distance to end point (reversed direction)
                    end = seg.get_end_point()
                    dx = end.x - current_end.x
                    dy = end.y - current_end.y
                    dz = end.z - current_end.z
                    dist_end = np.sqrt(dx**2 + dy**2 + dz**2)

                    if dist_end < min_dist:
                        min_dist = dist_end
                        nearest_idx = idx
                        use_reversed = True

                next_seg = other_segs.pop(nearest_idx)
                if use_reversed:
                    next_seg = next_seg.reverse()
                ordered.append(next_seg)

            optimized_segments.extend(ordered)
            last_end_point = ordered[-1].get_end_point()

        self.segments = optimized_segments

    def insert_travel_segments(
        self, travel_speed: float = 100.0, threshold: float = 0.1
    ) -> None:
        """
        Insert travel segments between non-adjacent segments.

        Scans the segment list and wherever two consecutive segments have a gap
        (end of segment N != start of segment N+1), inserts a TRAVEL segment
        connecting them. Travel segments have flow_rate=0 (no material deposition).

        Args:
            travel_speed: Speed for travel moves (mm/s)
            threshold: Minimum gap distance (mm) to insert a travel segment
        """
        if len(self.segments) < 2:
            return

        new_segments: list[ToolpathSegment] = [self.segments[0]]
        for i in range(1, len(self.segments)):
            prev_end = new_segments[-1].get_end_point()
            curr_start = self.segments[i].get_start_point()
            dx = curr_start.x - prev_end.x
            dy = curr_start.y - prev_end.y
            dz = curr_start.z - prev_end.z
            dist = np.sqrt(dx**2 + dy**2 + dz**2)

            if dist > threshold:
                travel = ToolpathSegment(
                    points=[
                        Point(prev_end.x, prev_end.y, prev_end.z),
                        Point(curr_start.x, curr_start.y, curr_start.z),
                    ],
                    type=ToolpathType.TRAVEL,
                    layer_index=self.segments[i].layer_index,
                    speed=travel_speed,
                    flow_rate=0.0,
                )
                new_segments.append(travel)

            new_segments.append(self.segments[i])

        self.segments = new_segments
