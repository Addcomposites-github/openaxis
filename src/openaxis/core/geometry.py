"""
Geometry handling for OpenAxis using COMPAS.

Provides utilities for loading, converting, and manipulating geometric data
for robotic manufacturing workflows.
"""

from pathlib import Path
from typing import Any

import trimesh
from compas.datastructures import Mesh as CompasMesh
from compas.geometry import Box, Frame, Point, Rotation, Scale, Transformation, Translation, Vector

from openaxis.core.exceptions import GeometryError


class GeometryConverter:
    """
    Converter between different geometry representations.

    Handles conversion between COMPAS, Trimesh, and other geometry formats.
    """

    @staticmethod
    def trimesh_to_compas(mesh: trimesh.Trimesh) -> CompasMesh:
        """
        Convert Trimesh mesh to COMPAS Mesh.

        Args:
            mesh: Trimesh mesh object

        Returns:
            COMPAS Mesh object

        Raises:
            GeometryError: If conversion fails
        """
        try:
            vertices = mesh.vertices.tolist()
            faces = mesh.faces.tolist()
            return CompasMesh.from_vertices_and_faces(vertices, faces)
        except Exception as e:
            raise GeometryError(f"Failed to convert Trimesh to COMPAS: {e}") from e

    @staticmethod
    def compas_to_trimesh(mesh: CompasMesh) -> trimesh.Trimesh:
        """
        Convert COMPAS Mesh to Trimesh.

        Args:
            mesh: COMPAS Mesh object

        Returns:
            Trimesh mesh object

        Raises:
            GeometryError: If conversion fails
        """
        try:
            vertices = [mesh.vertex_coordinates(v) for v in mesh.vertices()]
            faces = [mesh.face_vertices(f) for f in mesh.faces()]
            return trimesh.Trimesh(vertices=vertices, faces=faces)
        except Exception as e:
            raise GeometryError(f"Failed to convert COMPAS to Trimesh: {e}") from e


class GeometryLoader:
    """
    Loads geometric models from various file formats.

    Supports STL, OBJ, STEP (via trimesh), and converts to COMPAS format.
    """

    SUPPORTED_FORMATS = {".stl", ".obj", ".ply", ".off"}

    @classmethod
    def load(cls, file_path: str | Path, **kwargs: Any) -> CompasMesh:
        """
        Load geometry from file.

        Args:
            file_path: Path to geometry file
            **kwargs: Additional arguments passed to trimesh.load

        Returns:
            COMPAS Mesh object

        Raises:
            GeometryError: If file format is unsupported or loading fails
        """
        path = Path(file_path)

        if not path.exists():
            raise GeometryError(f"File not found: {path}")

        if path.suffix.lower() not in cls.SUPPORTED_FORMATS:
            raise GeometryError(
                f"Unsupported format: {path.suffix}. "
                f"Supported formats: {cls.SUPPORTED_FORMATS}"
            )

        try:
            # Load with trimesh
            loaded = trimesh.load(str(path), **kwargs)

            # Handle Scene vs Mesh
            if isinstance(loaded, trimesh.Scene):
                # Combine all geometries in scene
                mesh = trimesh.util.concatenate(
                    [geom for geom in loaded.geometry.values()
                     if isinstance(geom, trimesh.Trimesh)]
                )
            elif isinstance(loaded, trimesh.Trimesh):
                mesh = loaded
            else:
                raise GeometryError(f"Unexpected geometry type: {type(loaded)}")

            # Convert to COMPAS
            return GeometryConverter.trimesh_to_compas(mesh)

        except Exception as e:
            raise GeometryError(f"Failed to load geometry from {path}: {e}") from e

    @classmethod
    def save(cls, mesh: CompasMesh, file_path: str | Path, **kwargs: Any) -> None:
        """
        Save COMPAS mesh to file.

        Args:
            mesh: COMPAS Mesh to save
            file_path: Output file path
            **kwargs: Additional arguments passed to trimesh.export

        Raises:
            GeometryError: If saving fails
        """
        path = Path(file_path)

        try:
            # Convert to trimesh
            tmesh = GeometryConverter.compas_to_trimesh(mesh)

            # Export
            tmesh.export(str(path), **kwargs)

        except Exception as e:
            raise GeometryError(f"Failed to save geometry to {path}: {e}") from e


class BoundingBox:
    """
    Bounding box utilities for geometry.

    Provides methods to compute and manipulate axis-aligned bounding boxes.
    """

    @staticmethod
    def from_mesh(mesh: CompasMesh) -> Box:
        """
        Compute axis-aligned bounding box from mesh.

        Args:
            mesh: COMPAS Mesh object

        Returns:
            COMPAS Box representing the bounding box
        """
        vertices = [mesh.vertex_coordinates(v) for v in mesh.vertices()]

        # Compute min/max
        xs = [v[0] for v in vertices]
        ys = [v[1] for v in vertices]
        zs = [v[2] for v in vertices]

        min_pt = Point(min(xs), min(ys), min(zs))
        max_pt = Point(max(xs), max(ys), max(zs))

        # Box dimensions
        xsize = max_pt.x - min_pt.x
        ysize = max_pt.y - min_pt.y
        zsize = max_pt.z - min_pt.z

        # Box center
        center = Point(
            (min_pt.x + max_pt.x) / 2,
            (min_pt.y + max_pt.y) / 2,
            (min_pt.z + max_pt.z) / 2,
        )

        # Create frame at center
        frame = Frame(center, Vector(1, 0, 0), Vector(0, 1, 0))

        return Box(xsize=xsize, ysize=ysize, zsize=zsize, frame=frame)

    @staticmethod
    def get_dimensions(box: Box) -> tuple[float, float, float]:
        """
        Get bounding box dimensions.

        Args:
            box: COMPAS Box object

        Returns:
            Tuple of (x_size, y_size, z_size)
        """
        return (box.xsize, box.ysize, box.zsize)

    @staticmethod
    def get_center(box: Box) -> Point:
        """
        Get bounding box center point.

        Args:
            box: COMPAS Box object

        Returns:
            Center point as COMPAS Point
        """
        return box.frame.point


class TransformationUtilities:
    """
    Utilities for geometric transformations.

    Provides common transformation operations for manufacturing workflows.
    """

    @staticmethod
    def transform_mesh(mesh: CompasMesh, transformation: Transformation) -> CompasMesh:
        """
        Apply transformation to mesh.

        Args:
            mesh: COMPAS Mesh to transform
            transformation: COMPAS Transformation object

        Returns:
            Transformed COMPAS Mesh (new instance)
        """
        transformed = mesh.copy()
        transformed.transform(transformation)
        return transformed

    @staticmethod
    def translate(mesh: CompasMesh, vector: Vector | list[float]) -> CompasMesh:
        """
        Translate mesh by vector.

        Args:
            mesh: COMPAS Mesh to translate
            vector: Translation vector (COMPAS Vector or [x, y, z])

        Returns:
            Translated mesh (new instance)
        """
        if isinstance(vector, (list, tuple)):
            vector = Vector(*vector)

        t = Translation.from_vector(vector)
        return TransformationUtilities.transform_mesh(mesh, t)

    @staticmethod
    def rotate(mesh: CompasMesh, angle: float, axis: Vector, point: Point = None) -> CompasMesh:
        """
        Rotate mesh around axis.

        Args:
            mesh: COMPAS Mesh to rotate
            angle: Rotation angle in radians
            axis: Rotation axis as COMPAS Vector
            point: Point to rotate around (default: origin)

        Returns:
            Rotated mesh (new instance)
        """
        if point is None:
            point = Point(0, 0, 0)

        t = Rotation.from_axis_and_angle(axis, angle, point)
        return TransformationUtilities.transform_mesh(mesh, t)

    @staticmethod
    def scale(mesh: CompasMesh, factor: float | tuple[float, float, float]) -> CompasMesh:
        """
        Scale mesh uniformly or non-uniformly.

        Args:
            mesh: COMPAS Mesh to scale
            factor: Scale factor (uniform) or (x, y, z) factors

        Returns:
            Scaled mesh (new instance)
        """
        if isinstance(factor, (int, float)):
            t = Scale.from_factors([factor, factor, factor])
        else:
            t = Scale.from_factors(factor)

        return TransformationUtilities.transform_mesh(mesh, t)
