"""
Milling toolpath generation using OpenCAMLib.

OpenCAMLib provides 3-axis toolpath generation algorithms:
- Waterline: Constant-height contour paths (for roughing)
- Drop-cutter: Surface-following paths (for finishing)
- Batch drop-cutter: Efficient Z-height computation over XY grids

Library: https://github.com/aewallin/opencamlib
Install: pip install opencamlib
License: LGPL-2.1

This module provides a wrapper around OpenCAMLib for generating milling
toolpaths from triangle meshes (STL/OBJ loaded via trimesh).

Limitations (3-axis only):
- No 5-axis toolpath generation (use Noether/ROS-Industrial for 5-axis)
- No tool orientation output (tool axis is always Z-up)
- No feedrate/spindle speed calculation (use process plugin parameters)
"""

import logging
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np

try:
    import opencamlib as ocl

    OPENCAMLIB_AVAILABLE = True
except ImportError:
    OPENCAMLIB_AVAILABLE = False

try:
    import trimesh

    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False

from compas.geometry import Point

from openaxis.slicing.toolpath import Toolpath, ToolpathSegment, ToolpathType

logger = logging.getLogger(__name__)


class CutterType(Enum):
    """Cutter geometry types supported by OpenCAMLib."""

    CYLINDRICAL = "cylindrical"  # Flat endmill
    BALL = "ball"  # Ball nose endmill
    BULL = "bull"  # Bull nose (corner radius) endmill
    CONE = "cone"  # Conical cutter


class MillingToolpathGenerator:
    """
    Generate milling toolpaths using OpenCAMLib.

    Supports roughing (waterline contours at each Z level) and
    finishing (drop-cutter surface following) toolpath generation.

    Usage::

        gen = MillingToolpathGenerator(
            cutter_diameter=6.0,
            cutter_length=50.0,
            cutter_type=CutterType.CYLINDRICAL,
        )
        toolpath = gen.generate_roughing(mesh, step_down=1.0, step_over=3.0)

    Args:
        cutter_diameter: Cutter diameter in mm
        cutter_length: Cutter length in mm
        cutter_type: Cutter geometry type
        corner_radius: Corner radius for bull nose cutters (mm)

    Raises:
        ImportError: If opencamlib is not installed.
    """

    def __init__(
        self,
        cutter_diameter: float = 6.0,
        cutter_length: float = 50.0,
        cutter_type: CutterType = CutterType.CYLINDRICAL,
        corner_radius: float = 0.0,
    ):
        if not OPENCAMLIB_AVAILABLE:
            raise ImportError(
                "opencamlib is required for milling toolpath generation. "
                "Install with: pip install opencamlib"
            )

        self.cutter_diameter = cutter_diameter
        self.cutter_length = cutter_length
        self.cutter_type = cutter_type
        self.corner_radius = corner_radius
        self._cutter = self._create_cutter()

    def _create_cutter(self) -> "ocl.MillingCutter":
        """Create an OpenCAMLib cutter object."""
        if self.cutter_type == CutterType.CYLINDRICAL:
            return ocl.CylCutter(self.cutter_diameter, self.cutter_length)
        elif self.cutter_type == CutterType.BALL:
            return ocl.BallCutter(self.cutter_diameter, self.cutter_length)
        elif self.cutter_type == CutterType.BULL:
            if self.corner_radius <= 0:
                raise ValueError(
                    "Bull nose cutter requires corner_radius > 0"
                )
            return ocl.BullCutter(
                self.cutter_diameter, self.corner_radius, self.cutter_length
            )
        elif self.cutter_type == CutterType.CONE:
            return ocl.ConeCutter(self.cutter_diameter, self.cutter_length)
        else:
            raise ValueError(f"Unknown cutter type: {self.cutter_type}")

    def generate_roughing(
        self,
        mesh_path: str,
        step_down: float = 1.0,
        sampling: float = 0.5,
        z_safe: float = 5.0,
    ) -> Toolpath:
        """
        Generate roughing toolpaths using waterline algorithm.

        Waterline computes constant-height contour paths at each Z level.
        The cutter is projected horizontally at each height to find the
        intersection contours with the mesh surface.

        Args:
            mesh_path: Path to STL/OBJ mesh file
            step_down: Vertical step between Z levels (mm)
            sampling: Waterline sampling resolution (mm). Smaller = more
                      accurate but slower.
            z_safe: Safe Z height for retract moves (mm above mesh top)

        Returns:
            Toolpath with MACHINING segments for each Z level

        Raises:
            FileNotFoundError: If mesh file doesn't exist
            RuntimeError: If waterline computation fails
        """
        stl_surf = self._load_mesh(mesh_path)
        bounds = self._get_mesh_bounds(mesh_path)
        z_min, z_max = bounds[4], bounds[5]

        toolpath = Toolpath(
            layer_height=step_down,
            process_type="subtractive",
            metadata={
                "operation": "roughing",
                "algorithm": "waterline",
                "cutter_diameter": self.cutter_diameter,
                "cutter_type": self.cutter_type.value,
                "sampling": sampling,
            },
        )

        # Generate waterline contours from top to bottom
        z_levels = np.arange(z_max, z_min - step_down, -step_down)
        logger.info(
            "Generating roughing: %d Z levels from %.1f to %.1f mm",
            len(z_levels),
            z_max,
            z_min,
        )

        for layer_idx, z in enumerate(z_levels):
            wl = ocl.Waterline()
            wl.setSTL(stl_surf)
            wl.setCutter(self._cutter)
            wl.setSampling(sampling)
            wl.setZ(float(z))
            wl.run()

            loops = wl.getLoops()
            for loop in loops:
                if len(loop) < 2:
                    continue

                points = [Point(p.x, p.y, p.z) for p in loop]
                # Close the loop
                if len(points) > 2:
                    points.append(points[0])

                segment = ToolpathSegment(
                    points=points,
                    type=ToolpathType.MACHINING,
                    layer_index=layer_idx,
                    metadata={"z_level": float(z), "operation": "roughing"},
                )
                toolpath.add_segment(segment)

        logger.info(
            "Roughing complete: %d segments, %.1f mm total length",
            len(toolpath.segments),
            toolpath.get_total_length(),
        )

        return toolpath

    def generate_finishing(
        self,
        mesh_path: str,
        step_over: float = 0.5,
        sampling: float = 0.5,
        direction: str = "x",
    ) -> Toolpath:
        """
        Generate finishing toolpaths using drop-cutter algorithm.

        Drop-cutter computes the safe Z height for the cutter at each
        XY position, creating a surface-following toolpath.

        Args:
            mesh_path: Path to STL/OBJ mesh file
            step_over: Distance between parallel passes (mm)
            sampling: Along-path sampling resolution (mm)
            direction: Scan direction ('x' for X-parallel, 'y' for Y-parallel)

        Returns:
            Toolpath with MACHINING segments for each scan line

        Raises:
            FileNotFoundError: If mesh file doesn't exist
        """
        stl_surf = self._load_mesh(mesh_path)
        bounds = self._get_mesh_bounds(mesh_path)
        x_min, x_max = bounds[0], bounds[1]
        y_min, y_max = bounds[2], bounds[3]

        # Expand bounds by cutter radius
        r = self.cutter_diameter / 2.0
        x_min -= r
        x_max += r
        y_min -= r
        y_max += r

        toolpath = Toolpath(
            process_type="subtractive",
            metadata={
                "operation": "finishing",
                "algorithm": "drop_cutter",
                "cutter_diameter": self.cutter_diameter,
                "cutter_type": self.cutter_type.value,
                "step_over": step_over,
                "sampling": sampling,
                "direction": direction,
            },
        )

        if direction == "x":
            # X-parallel scan lines
            y_positions = np.arange(y_min, y_max + step_over, step_over)
            logger.info(
                "Generating finishing: %d X-parallel passes", len(y_positions)
            )

            for layer_idx, y in enumerate(y_positions):
                path = ocl.Path()
                path.append(
                    ocl.Line(
                        ocl.Point(x_min, float(y), 0),
                        ocl.Point(x_max, float(y), 0),
                    )
                )

                pdc = ocl.PathDropCutter()
                pdc.setSTL(stl_surf)
                pdc.setCutter(self._cutter)
                pdc.setPath(path)
                pdc.setSampling(sampling)
                pdc.run()

                cl_points = pdc.getCLPoints()
                if len(cl_points) < 2:
                    continue

                points = [Point(p.x, p.y, p.z) for p in cl_points]
                segment = ToolpathSegment(
                    points=points,
                    type=ToolpathType.MACHINING,
                    layer_index=layer_idx,
                    metadata={
                        "y_position": float(y),
                        "operation": "finishing",
                    },
                )
                toolpath.add_segment(segment)
        else:
            # Y-parallel scan lines
            x_positions = np.arange(x_min, x_max + step_over, step_over)
            logger.info(
                "Generating finishing: %d Y-parallel passes", len(x_positions)
            )

            for layer_idx, x in enumerate(x_positions):
                path = ocl.Path()
                path.append(
                    ocl.Line(
                        ocl.Point(float(x), y_min, 0),
                        ocl.Point(float(x), y_max, 0),
                    )
                )

                pdc = ocl.PathDropCutter()
                pdc.setSTL(stl_surf)
                pdc.setCutter(self._cutter)
                pdc.setPath(path)
                pdc.setSampling(sampling)
                pdc.run()

                cl_points = pdc.getCLPoints()
                if len(cl_points) < 2:
                    continue

                points = [Point(p.x, p.y, p.z) for p in cl_points]
                segment = ToolpathSegment(
                    points=points,
                    type=ToolpathType.MACHINING,
                    layer_index=layer_idx,
                    metadata={
                        "x_position": float(x),
                        "operation": "finishing",
                    },
                )
                toolpath.add_segment(segment)

        logger.info(
            "Finishing complete: %d segments, %.1f mm total length",
            len(toolpath.segments),
            toolpath.get_total_length(),
        )

        return toolpath

    def _load_mesh(self, mesh_path: str) -> "ocl.STLSurf":
        """
        Load a mesh file into an OpenCAMLib STLSurf.

        Uses trimesh to load the mesh and then converts triangles
        to OpenCAMLib format.

        Args:
            mesh_path: Path to STL/OBJ file

        Returns:
            ocl.STLSurf object

        Raises:
            FileNotFoundError: If file doesn't exist
            ImportError: If trimesh is not available
        """
        if not TRIMESH_AVAILABLE:
            raise ImportError(
                "trimesh is required for mesh loading. "
                "Install with: pip install trimesh"
            )

        import os

        if not os.path.exists(mesh_path):
            raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

        mesh = trimesh.load(mesh_path)

        stl_surf = ocl.STLSurf()
        vertices = mesh.vertices
        faces = mesh.faces

        for face in faces:
            v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
            tri = ocl.Triangle(
                ocl.Point(float(v0[0]), float(v0[1]), float(v0[2])),
                ocl.Point(float(v1[0]), float(v1[1]), float(v1[2])),
                ocl.Point(float(v2[0]), float(v2[1]), float(v2[2])),
            )
            stl_surf.addTriangle(tri)

        logger.debug(
            "Loaded mesh %s: %d triangles", mesh_path, stl_surf.size()
        )
        return stl_surf

    def _get_mesh_bounds(
        self, mesh_path: str
    ) -> Tuple[float, float, float, float, float, float]:
        """
        Get mesh bounding box (x_min, x_max, y_min, y_max, z_min, z_max).
        """
        mesh = trimesh.load(mesh_path)
        bounds = mesh.bounds  # [[x_min, y_min, z_min], [x_max, y_max, z_max]]
        return (
            float(bounds[0][0]),
            float(bounds[1][0]),
            float(bounds[0][1]),
            float(bounds[1][1]),
            float(bounds[0][2]),
            float(bounds[1][2]),
        )

    @staticmethod
    def is_available() -> bool:
        """Check if OpenCAMLib is available."""
        return OPENCAMLIB_AVAILABLE
