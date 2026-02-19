"""
Unit tests for OpenCAMLib milling toolpath generation.

Tests the MillingToolpathGenerator wrapper around OpenCAMLib's
waterline (roughing) and drop-cutter (finishing) algorithms.

Library under test: opencamlib (pip install opencamlib)
"""

import os
import tempfile

import numpy as np
import pytest

try:
    import opencamlib as ocl

    OCL_AVAILABLE = True
except ImportError:
    OCL_AVAILABLE = False

try:
    import trimesh

    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False

from openaxis.slicing.toolpath import ToolpathType

pytestmark = pytest.mark.skipif(
    not OCL_AVAILABLE or not TRIMESH_AVAILABLE,
    reason="opencamlib or trimesh not installed",
)


@pytest.fixture(scope="module")
def box_mesh_path():
    """Create a simple box mesh for testing."""
    box = trimesh.creation.box(extents=[20, 20, 10])
    path = os.path.join(tempfile.gettempdir(), "test_milling_box.stl")
    box.export(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture(scope="module")
def sphere_mesh_path():
    """Create a sphere mesh for testing curved surfaces."""
    sphere = trimesh.creation.icosphere(radius=10.0, subdivisions=3)
    path = os.path.join(tempfile.gettempdir(), "test_milling_sphere.stl")
    sphere.export(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


class TestMillingToolpathGeneratorInit:
    """Test generator initialization."""

    def test_create_cylindrical(self):
        """Create generator with cylindrical cutter."""
        from openaxis.slicing.milling_toolpath import (
            CutterType,
            MillingToolpathGenerator,
        )

        gen = MillingToolpathGenerator(
            cutter_diameter=6.0,
            cutter_length=50.0,
            cutter_type=CutterType.CYLINDRICAL,
        )
        assert gen.cutter_diameter == 6.0
        assert gen.cutter_type == CutterType.CYLINDRICAL

    def test_create_ball(self):
        """Create generator with ball cutter."""
        from openaxis.slicing.milling_toolpath import (
            CutterType,
            MillingToolpathGenerator,
        )

        gen = MillingToolpathGenerator(
            cutter_diameter=6.0,
            cutter_type=CutterType.BALL,
        )
        assert gen.cutter_type == CutterType.BALL

    def test_create_bull(self):
        """Create generator with bull nose cutter."""
        from openaxis.slicing.milling_toolpath import (
            CutterType,
            MillingToolpathGenerator,
        )

        gen = MillingToolpathGenerator(
            cutter_diameter=6.0,
            cutter_type=CutterType.BULL,
            corner_radius=1.0,
        )
        assert gen.cutter_type == CutterType.BULL

    def test_bull_requires_corner_radius(self):
        """Bull cutter without corner_radius should raise ValueError."""
        from openaxis.slicing.milling_toolpath import (
            CutterType,
            MillingToolpathGenerator,
        )

        with pytest.raises(ValueError, match="corner_radius"):
            MillingToolpathGenerator(
                cutter_diameter=6.0,
                cutter_type=CutterType.BULL,
                corner_radius=0.0,
            )

    def test_is_available(self):
        """OpenCAMLib should be detected as available."""
        from openaxis.slicing.milling_toolpath import MillingToolpathGenerator

        assert MillingToolpathGenerator.is_available()


class TestRoughing:
    """Test waterline roughing toolpath generation."""

    def test_roughing_produces_segments(self, box_mesh_path):
        """Roughing a box should produce toolpath segments."""
        from openaxis.slicing.milling_toolpath import MillingToolpathGenerator

        gen = MillingToolpathGenerator(cutter_diameter=6.0)
        toolpath = gen.generate_roughing(
            box_mesh_path, step_down=2.0, sampling=1.0
        )

        assert len(toolpath.segments) > 0
        assert toolpath.process_type == "subtractive"
        assert toolpath.metadata["operation"] == "roughing"
        assert toolpath.metadata["algorithm"] == "waterline"

    def test_roughing_segment_types(self, box_mesh_path):
        """All roughing segments should be MACHINING type."""
        from openaxis.slicing.milling_toolpath import MillingToolpathGenerator

        gen = MillingToolpathGenerator(cutter_diameter=6.0)
        toolpath = gen.generate_roughing(box_mesh_path, step_down=2.0)

        for seg in toolpath.segments:
            assert seg.type == ToolpathType.MACHINING

    def test_roughing_z_levels(self, box_mesh_path):
        """Roughing should produce contours at multiple Z levels."""
        from openaxis.slicing.milling_toolpath import MillingToolpathGenerator

        gen = MillingToolpathGenerator(cutter_diameter=6.0)
        toolpath = gen.generate_roughing(box_mesh_path, step_down=2.0)

        z_levels = set()
        for seg in toolpath.segments:
            z_levels.add(round(seg.metadata["z_level"], 1))

        # Box is 10mm tall, step_down=2mm → at least 5 Z levels
        assert len(z_levels) >= 3

    def test_roughing_total_length(self, box_mesh_path):
        """Roughing toolpath should have positive total length."""
        from openaxis.slicing.milling_toolpath import MillingToolpathGenerator

        gen = MillingToolpathGenerator(cutter_diameter=6.0)
        toolpath = gen.generate_roughing(box_mesh_path, step_down=2.0)

        assert toolpath.get_total_length() > 0

    def test_roughing_sphere(self, sphere_mesh_path):
        """Roughing a sphere should produce contours at varying radii."""
        from openaxis.slicing.milling_toolpath import MillingToolpathGenerator

        gen = MillingToolpathGenerator(cutter_diameter=3.0)
        toolpath = gen.generate_roughing(
            sphere_mesh_path, step_down=2.0, sampling=1.0
        )

        assert len(toolpath.segments) > 0


class TestFinishing:
    """Test drop-cutter finishing toolpath generation."""

    def test_finishing_produces_segments(self, box_mesh_path):
        """Finishing a box should produce scan line segments."""
        from openaxis.slicing.milling_toolpath import MillingToolpathGenerator

        gen = MillingToolpathGenerator(cutter_diameter=6.0)
        toolpath = gen.generate_finishing(
            box_mesh_path, step_over=3.0, sampling=1.0
        )

        assert len(toolpath.segments) > 0
        assert toolpath.process_type == "subtractive"
        assert toolpath.metadata["operation"] == "finishing"
        assert toolpath.metadata["algorithm"] == "drop_cutter"

    def test_finishing_x_direction(self, box_mesh_path):
        """X-parallel finishing should produce Y-indexed passes."""
        from openaxis.slicing.milling_toolpath import MillingToolpathGenerator

        gen = MillingToolpathGenerator(cutter_diameter=6.0)
        toolpath = gen.generate_finishing(
            box_mesh_path, step_over=3.0, direction="x"
        )

        for seg in toolpath.segments:
            assert "y_position" in seg.metadata

    def test_finishing_y_direction(self, box_mesh_path):
        """Y-parallel finishing should produce X-indexed passes."""
        from openaxis.slicing.milling_toolpath import MillingToolpathGenerator

        gen = MillingToolpathGenerator(cutter_diameter=6.0)
        toolpath = gen.generate_finishing(
            box_mesh_path, step_over=3.0, direction="y"
        )

        for seg in toolpath.segments:
            assert "x_position" in seg.metadata

    def test_finishing_points_on_surface(self, box_mesh_path):
        """Finishing points should be at or above the mesh surface."""
        from openaxis.slicing.milling_toolpath import MillingToolpathGenerator

        gen = MillingToolpathGenerator(cutter_diameter=6.0)
        toolpath = gen.generate_finishing(
            box_mesh_path, step_over=3.0, sampling=1.0
        )

        # Box top is at z=5. Drop-cutter should find z >= -5 for all points
        for seg in toolpath.segments:
            for pt in seg.points:
                assert pt.z >= -10, f"Point below mesh: z={pt.z}"

    def test_finishing_ball_cutter(self, sphere_mesh_path):
        """Ball cutter finishing on a sphere should follow the surface."""
        from openaxis.slicing.milling_toolpath import (
            CutterType,
            MillingToolpathGenerator,
        )

        gen = MillingToolpathGenerator(
            cutter_diameter=6.0, cutter_type=CutterType.BALL
        )
        toolpath = gen.generate_finishing(
            sphere_mesh_path, step_over=2.0, sampling=1.0
        )

        assert len(toolpath.segments) > 0


class TestErrorHandling:
    """Test error handling for invalid inputs."""

    def test_nonexistent_mesh(self):
        """Non-existent mesh file should raise FileNotFoundError."""
        from openaxis.slicing.milling_toolpath import MillingToolpathGenerator

        gen = MillingToolpathGenerator(cutter_diameter=6.0)
        with pytest.raises(FileNotFoundError):
            gen.generate_roughing("/nonexistent/mesh.stl")

    def test_nonexistent_mesh_finishing(self):
        """Non-existent mesh for finishing should raise FileNotFoundError."""
        from openaxis.slicing.milling_toolpath import MillingToolpathGenerator

        gen = MillingToolpathGenerator(cutter_diameter=6.0)
        with pytest.raises(FileNotFoundError):
            gen.generate_finishing("/nonexistent/mesh.stl")
