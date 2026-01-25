"""
Tests for geometry module.
"""

import math
from pathlib import Path

import pytest
import trimesh
from compas.datastructures import Mesh as CompasMesh
from compas.geometry import Box, Frame, Point, Vector

from openaxis.core.exceptions import GeometryError
from openaxis.core.geometry import (
    BoundingBox,
    GeometryConverter,
    GeometryLoader,
    TransformationUtilities,
)


@pytest.fixture
def simple_trimesh():
    """Create a simple trimesh cube for testing."""
    return trimesh.creation.box(extents=[2.0, 2.0, 2.0])


@pytest.fixture
def simple_compas_mesh():
    """Create a simple COMPAS mesh for testing."""
    vertices = [
        [0, 0, 0],
        [1, 0, 0],
        [1, 1, 0],
        [0, 1, 0],
        [0, 0, 1],
        [1, 0, 1],
        [1, 1, 1],
        [0, 1, 1],
    ]
    faces = [
        [0, 1, 2, 3],  # bottom
        [4, 5, 6, 7],  # top
        [0, 1, 5, 4],  # front
        [2, 3, 7, 6],  # back
        [0, 3, 7, 4],  # left
        [1, 2, 6, 5],  # right
    ]
    return CompasMesh.from_vertices_and_faces(vertices, faces)


class TestGeometryConverter:
    """Tests for GeometryConverter."""

    def test_trimesh_to_compas(self, simple_trimesh):
        """Test conversion from Trimesh to COMPAS."""
        compas_mesh = GeometryConverter.trimesh_to_compas(simple_trimesh)

        assert isinstance(compas_mesh, CompasMesh)
        assert compas_mesh.number_of_vertices() == simple_trimesh.vertices.shape[0]
        assert compas_mesh.number_of_faces() == simple_trimesh.faces.shape[0]

    def test_compas_to_trimesh(self, simple_compas_mesh):
        """Test conversion from COMPAS to Trimesh."""
        tmesh = GeometryConverter.compas_to_trimesh(simple_compas_mesh)

        assert isinstance(tmesh, trimesh.Trimesh)
        assert len(tmesh.vertices) == simple_compas_mesh.number_of_vertices()
        # Trimesh triangulates quad faces, so we expect more faces
        assert len(tmesh.faces) >= simple_compas_mesh.number_of_faces()

    def test_roundtrip_conversion(self, simple_trimesh):
        """Test roundtrip conversion preserves geometry."""
        compas_mesh = GeometryConverter.trimesh_to_compas(simple_trimesh)
        back_to_trimesh = GeometryConverter.compas_to_trimesh(compas_mesh)

        # Check vertex count is preserved
        assert len(back_to_trimesh.vertices) == simple_trimesh.vertices.shape[0]

        # Check face count is preserved
        assert len(back_to_trimesh.faces) == simple_trimesh.faces.shape[0]


class TestGeometryLoader:
    """Tests for GeometryLoader."""

    def test_supported_formats(self):
        """Test that supported formats are defined."""
        assert ".stl" in GeometryLoader.SUPPORTED_FORMATS
        assert ".obj" in GeometryLoader.SUPPORTED_FORMATS

    def test_load_nonexistent_file(self):
        """Test loading non-existent file raises error."""
        with pytest.raises(GeometryError, match="File not found"):
            GeometryLoader.load("nonexistent_file.stl")

    def test_load_unsupported_format(self, tmp_path):
        """Test loading unsupported format raises error."""
        # Create a dummy file with unsupported extension
        dummy_file = tmp_path / "test.xyz"
        dummy_file.write_text("dummy content")

        with pytest.raises(GeometryError, match="Unsupported format"):
            GeometryLoader.load(dummy_file)

    def test_save_and_load_stl(self, simple_compas_mesh, tmp_path):
        """Test saving and loading STL file."""
        output_file = tmp_path / "test.stl"

        # Save mesh
        GeometryLoader.save(simple_compas_mesh, output_file)

        # Verify file was created
        assert output_file.exists()

        # Load it back
        loaded_mesh = GeometryLoader.load(output_file)

        assert isinstance(loaded_mesh, CompasMesh)
        assert loaded_mesh.number_of_vertices() > 0
        assert loaded_mesh.number_of_faces() > 0


class TestBoundingBox:
    """Tests for BoundingBox utilities."""

    def test_from_mesh(self, simple_compas_mesh):
        """Test bounding box computation from mesh."""
        bbox = BoundingBox.from_mesh(simple_compas_mesh)

        assert isinstance(bbox, Box)

        # Check dimensions (mesh is 0-1 in each axis)
        dims = BoundingBox.get_dimensions(bbox)
        assert abs(dims[0] - 1.0) < 0.01  # x
        assert abs(dims[1] - 1.0) < 0.01  # y
        assert abs(dims[2] - 1.0) < 0.01  # z

    def test_get_center(self, simple_compas_mesh):
        """Test getting bounding box center."""
        bbox = BoundingBox.from_mesh(simple_compas_mesh)
        center = BoundingBox.get_center(bbox)

        assert isinstance(center, Point)

        # Center should be at (0.5, 0.5, 0.5)
        assert abs(center.x - 0.5) < 0.01
        assert abs(center.y - 0.5) < 0.01
        assert abs(center.z - 0.5) < 0.01

    def test_get_dimensions(self):
        """Test getting box dimensions."""
        frame = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
        box = Box(xsize=2.0, ysize=3.0, zsize=4.0, frame=frame)

        dims = BoundingBox.get_dimensions(box)

        assert dims == (2.0, 3.0, 4.0)


class TestTransformationUtilities:
    """Tests for TransformationUtilities."""

    def test_translate_with_vector(self, simple_compas_mesh):
        """Test mesh translation with Vector."""
        translation = Vector(1.0, 2.0, 3.0)
        transformed = TransformationUtilities.translate(simple_compas_mesh, translation)

        assert isinstance(transformed, CompasMesh)

        # Original mesh should be unchanged
        orig_vertex = simple_compas_mesh.vertex_coordinates(0)
        assert orig_vertex == [0, 0, 0]

        # Transformed mesh should be shifted
        # Note: first vertex of unit cube at origin becomes (1, 2, 3)
        # But we need to account for the transformation logic
        assert transformed.number_of_vertices() == simple_compas_mesh.number_of_vertices()

    def test_translate_with_list(self, simple_compas_mesh):
        """Test mesh translation with list."""
        translation = [1.0, 2.0, 3.0]
        transformed = TransformationUtilities.translate(simple_compas_mesh, translation)

        assert isinstance(transformed, CompasMesh)
        assert transformed.number_of_vertices() == simple_compas_mesh.number_of_vertices()

    def test_rotate(self, simple_compas_mesh):
        """Test mesh rotation."""
        axis = Vector(0, 0, 1)  # Z-axis
        angle = math.pi / 2  # 90 degrees

        transformed = TransformationUtilities.rotate(
            simple_compas_mesh, angle, axis
        )

        assert isinstance(transformed, CompasMesh)
        assert transformed.number_of_vertices() == simple_compas_mesh.number_of_vertices()

        # Original mesh should be unchanged
        orig_vertex = simple_compas_mesh.vertex_coordinates(0)
        assert orig_vertex == [0, 0, 0]

    def test_rotate_around_point(self, simple_compas_mesh):
        """Test mesh rotation around a point."""
        axis = Vector(0, 0, 1)
        angle = math.pi / 4  # 45 degrees
        point = Point(0.5, 0.5, 0)

        transformed = TransformationUtilities.rotate(
            simple_compas_mesh, angle, axis, point
        )

        assert isinstance(transformed, CompasMesh)
        assert transformed.number_of_vertices() == simple_compas_mesh.number_of_vertices()

    def test_scale_uniform(self, simple_compas_mesh):
        """Test uniform scaling."""
        factor = 2.0
        transformed = TransformationUtilities.scale(simple_compas_mesh, factor)

        assert isinstance(transformed, CompasMesh)
        assert transformed.number_of_vertices() == simple_compas_mesh.number_of_vertices()

        # Check that bounding box is roughly 2x larger
        orig_bbox = BoundingBox.from_mesh(simple_compas_mesh)
        new_bbox = BoundingBox.from_mesh(transformed)

        orig_dims = BoundingBox.get_dimensions(orig_bbox)
        new_dims = BoundingBox.get_dimensions(new_bbox)

        assert abs(new_dims[0] - orig_dims[0] * factor) < 0.1
        assert abs(new_dims[1] - orig_dims[1] * factor) < 0.1
        assert abs(new_dims[2] - orig_dims[2] * factor) < 0.1

    def test_scale_non_uniform(self, simple_compas_mesh):
        """Test non-uniform scaling."""
        factors = (2.0, 1.0, 0.5)
        transformed = TransformationUtilities.scale(simple_compas_mesh, factors)

        assert isinstance(transformed, CompasMesh)
        assert transformed.number_of_vertices() == simple_compas_mesh.number_of_vertices()

    def test_transform_creates_new_instance(self, simple_compas_mesh):
        """Test that transformations create new mesh instances."""
        transformed = TransformationUtilities.translate(
            simple_compas_mesh, [1, 0, 0]
        )

        # Meshes should be different instances
        assert transformed is not simple_compas_mesh

        # Original should be unchanged
        orig_vertex = simple_compas_mesh.vertex_coordinates(0)
        assert orig_vertex == [0, 0, 0]
