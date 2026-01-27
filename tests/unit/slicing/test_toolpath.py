"""
Tests for toolpath module.
"""

import pytest
from compas.geometry import Point

from openaxis.slicing.toolpath import (
    InfillPattern,
    Toolpath,
    ToolpathSegment,
    ToolpathType,
)


class TestToolpathSegment:
    """Tests for ToolpathSegment."""

    def test_initialization(self):
        """Test segment initialization."""
        points = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 10, 0)]
        segment = ToolpathSegment(
            points=points,
            type=ToolpathType.PERIMETER,
            layer_index=0,
            extrusion_width=1.0,
            speed=50.0,
        )

        assert segment.points == points
        assert segment.type == ToolpathType.PERIMETER
        assert segment.layer_index == 0
        assert segment.extrusion_width == 1.0
        assert segment.speed == 50.0

    def test_get_length(self):
        """Test length calculation."""
        points = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 10, 0)]
        segment = ToolpathSegment(
            points=points,
            type=ToolpathType.PERIMETER,
            layer_index=0,
        )

        length = segment.get_length()
        assert abs(length - 20.0) < 0.01  # 10 + 10

    def test_get_length_empty(self):
        """Test length calculation with no points."""
        segment = ToolpathSegment(
            points=[],
            type=ToolpathType.PERIMETER,
            layer_index=0,
        )

        assert segment.get_length() == 0.0

    def test_get_start_end_points(self):
        """Test getting start and end points."""
        points = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 10, 0)]
        segment = ToolpathSegment(
            points=points,
            type=ToolpathType.PERIMETER,
            layer_index=0,
        )

        start = segment.get_start_point()
        end = segment.get_end_point()

        assert start.x == 0 and start.y == 0 and start.z == 0
        assert end.x == 10 and end.y == 10 and end.z == 0

    def test_get_points_empty_raises(self):
        """Test that getting points from empty segment raises error."""
        segment = ToolpathSegment(
            points=[],
            type=ToolpathType.PERIMETER,
            layer_index=0,
        )

        with pytest.raises(ValueError):
            segment.get_start_point()

        with pytest.raises(ValueError):
            segment.get_end_point()

    def test_reverse(self):
        """Test reversing segment point order."""
        points = [Point(0, 0, 0), Point(10, 0, 0), Point(10, 10, 0)]
        segment = ToolpathSegment(
            points=points,
            type=ToolpathType.PERIMETER,
            layer_index=0,
        )

        reversed_seg = segment.reverse()

        assert reversed_seg.points[0] == points[-1]
        assert reversed_seg.points[-1] == points[0]
        assert reversed_seg.type == segment.type
        assert reversed_seg.layer_index == segment.layer_index


class TestToolpath:
    """Tests for Toolpath."""

    def test_initialization(self):
        """Test toolpath initialization."""
        toolpath = Toolpath(
            layer_height=1.0,
            total_layers=10,
            process_type="additive",
        )

        assert toolpath.layer_height == 1.0
        assert toolpath.total_layers == 10
        assert toolpath.process_type == "additive"
        assert len(toolpath.segments) == 0

    def test_add_segment(self):
        """Test adding segments."""
        toolpath = Toolpath()

        segment = ToolpathSegment(
            points=[Point(0, 0, 0), Point(10, 0, 0)],
            type=ToolpathType.PERIMETER,
            layer_index=0,
        )

        toolpath.add_segment(segment)

        assert len(toolpath.segments) == 1
        assert toolpath.total_layers == 1

    def test_get_segments_by_layer(self):
        """Test getting segments by layer."""
        toolpath = Toolpath()

        seg1 = ToolpathSegment(
            points=[Point(0, 0, 0)], type=ToolpathType.PERIMETER, layer_index=0
        )
        seg2 = ToolpathSegment(
            points=[Point(0, 0, 1)], type=ToolpathType.PERIMETER, layer_index=1
        )
        seg3 = ToolpathSegment(
            points=[Point(0, 0, 0)], type=ToolpathType.INFILL, layer_index=0
        )

        toolpath.add_segment(seg1)
        toolpath.add_segment(seg2)
        toolpath.add_segment(seg3)

        layer0_segs = toolpath.get_segments_by_layer(0)
        assert len(layer0_segs) == 2

        layer1_segs = toolpath.get_segments_by_layer(1)
        assert len(layer1_segs) == 1

    def test_get_segments_by_type(self):
        """Test getting segments by type."""
        toolpath = Toolpath()

        seg1 = ToolpathSegment(
            points=[Point(0, 0, 0)], type=ToolpathType.PERIMETER, layer_index=0
        )
        seg2 = ToolpathSegment(
            points=[Point(0, 0, 1)], type=ToolpathType.INFILL, layer_index=0
        )
        seg3 = ToolpathSegment(
            points=[Point(0, 0, 0)], type=ToolpathType.PERIMETER, layer_index=1
        )

        toolpath.add_segment(seg1)
        toolpath.add_segment(seg2)
        toolpath.add_segment(seg3)

        perimeter_segs = toolpath.get_segments_by_type(ToolpathType.PERIMETER)
        assert len(perimeter_segs) == 2

        infill_segs = toolpath.get_segments_by_type(ToolpathType.INFILL)
        assert len(infill_segs) == 1

    def test_get_total_length(self):
        """Test total length calculation."""
        toolpath = Toolpath()

        seg1 = ToolpathSegment(
            points=[Point(0, 0, 0), Point(10, 0, 0)],
            type=ToolpathType.PERIMETER,
            layer_index=0,
        )
        seg2 = ToolpathSegment(
            points=[Point(0, 0, 0), Point(0, 20, 0)],
            type=ToolpathType.INFILL,
            layer_index=0,
        )

        toolpath.add_segment(seg1)
        toolpath.add_segment(seg2)

        total_length = toolpath.get_total_length()
        assert abs(total_length - 30.0) < 0.01  # 10 + 20

    def test_get_build_time_estimate(self):
        """Test build time estimation."""
        toolpath = Toolpath()

        # 10mm segment at 10 mm/s = 1 second
        seg1 = ToolpathSegment(
            points=[Point(0, 0, 0), Point(10, 0, 0)],
            type=ToolpathType.PERIMETER,
            layer_index=0,
            speed=10.0,
        )

        toolpath.add_segment(seg1)

        time = toolpath.get_build_time_estimate()
        assert abs(time - 1.0) < 0.01

    def test_get_bounds(self):
        """Test bounding box calculation."""
        toolpath = Toolpath()

        seg = ToolpathSegment(
            points=[Point(-5, -10, 0), Point(15, 20, 30)],
            type=ToolpathType.PERIMETER,
            layer_index=0,
        )

        toolpath.add_segment(seg)

        min_pt, max_pt = toolpath.get_bounds()

        assert min_pt.x == -5
        assert min_pt.y == -10
        assert min_pt.z == 0
        assert max_pt.x == 15
        assert max_pt.y == 20
        assert max_pt.z == 30

    def test_get_bounds_empty_raises(self):
        """Test that getting bounds from empty toolpath raises error."""
        toolpath = Toolpath()

        with pytest.raises(ValueError):
            toolpath.get_bounds()
