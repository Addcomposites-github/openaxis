"""
Planar slicing for additive manufacturing.

Primary backend: ORNL Slicer 2 (subprocess wrapper).
ORNL Slicer 2 is a production-grade slicer used by 50+ equipment manufacturers
for FDM, WAAM, LFAM, MFAM, and Concrete 3D printing.

Repository: https://github.com/ORNLSlicer/Slicer-2

Previously used compas_slicer (ETH Zurich), but compas_slicer requires
compas<2.0 which conflicts with our compas 2.x dependency. See
docs/UNGROUNDED_CODE.md for details.

When ORNL Slicer 2 is not installed, slice() will raise an ImportError
with installation instructions.
"""

import logging
from typing import Optional

from compas.datastructures import Mesh as CompasMesh

from openaxis.slicing.toolpath import (
    InfillPattern,
    Toolpath,
    ToolpathSegment,
    ToolpathType,
)

logger = logging.getLogger(__name__)


class PlanarSlicer:
    """
    Planar slicing engine delegating to ORNL Slicer 2.

    When ORNL Slicer 2 is installed, uses the subprocess wrapper to
    call the binary for production-grade slicing. When not installed,
    raises an ImportError with instructions.

    For direct ORNL Slicer 2 access with full configuration control,
    use ORNLSlicer directly::

        from openaxis.slicing.ornl_slicer import ORNLSlicer, ORNLSlicerConfig
        slicer = ORNLSlicer()
        config = ORNLSlicerConfig("WAAM").set_layer_height(1.0)
        toolpath = slicer.slice("model.stl", config)
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
            infill_pattern: Pattern for infill
            support_enabled: Whether to generate support structures
            seam_angle: Angle for seam placement
            wall_width: Width of wall extrusion (defaults to extrusion_width)
            print_speed: Print speed in mm/min
            travel_speed: Travel speed in mm/min
            seam_mode: Seam placement mode
            seam_shape: Seam shape
            lead_in_distance: Lead-in distance (mm)
            lead_in_angle: Lead-in angle (degrees)
            lead_out_distance: Lead-out distance (mm)
            lead_out_angle: Lead-out angle (degrees)
            infill_pattern_name: String infill pattern name
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
        self.infill_pattern_name = infill_pattern_name

    def slice(
        self,
        mesh: CompasMesh,
        start_height: Optional[float] = None,
        end_height: Optional[float] = None,
    ) -> Toolpath:
        """
        Slice a mesh into layers and generate toolpath.

        Delegates to ORNL Slicer 2 when available. The mesh is exported
        to a temporary STL file and sliced via the subprocess wrapper.

        Args:
            mesh: COMPAS mesh to slice
            start_height: Starting Z height (currently unused — passed
                          to ORNL Slicer 2 config when supported)
            end_height: Ending Z height (currently unused)

        Returns:
            Complete toolpath with all layers

        Raises:
            ImportError: If ORNL Slicer 2 is not installed
        """
        from openaxis.slicing.ornl_slicer import ORNLSlicer, ORNLSlicerConfig

        if not ORNLSlicer.is_available():
            raise ImportError(
                "ORNL Slicer 2 binary not found. "
                "Install from https://github.com/ORNLSlicer/Slicer-2 or "
                "set ORNL_SLICER2_PATH environment variable.\n\n"
                "For direct API access, use ORNLSlicer:\n"
                "  from openaxis.slicing.ornl_slicer import ORNLSlicer\n"
                "  slicer = ORNLSlicer('/path/to/slicer2.exe')\n"
                "  toolpath = slicer.slice('model.stl')"
            )

        import os
        import tempfile

        import trimesh

        logger.info(
            "Slicing with ORNL Slicer 2: layer_height=%.2f, "
            "extrusion_width=%.2f, walls=%d, density=%.1f%%",
            self.layer_height,
            self.extrusion_width,
            self.wall_count,
            self.infill_density * 100,
        )

        # Export COMPAS mesh to temp STL file for ORNL Slicer 2
        vertices = [mesh.vertex_coordinates(v) for v in mesh.vertices()]
        faces = [mesh.face_vertices(f) for f in mesh.faces()]
        trimesh_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

        temp_stl = tempfile.NamedTemporaryFile(
            suffix=".stl", delete=False
        )
        temp_stl.close()
        trimesh_mesh.export(temp_stl.name)

        try:
            # Build ORNL Slicer 2 config from our parameters
            config = ORNLSlicerConfig()
            config.set_layer_height(self.layer_height)
            config.set_bead_width(self.extrusion_width)
            config.set_perimeters(self.wall_count)
            # Map InfillPattern string values to ORNL Slicer 2 integer indices
            _pattern_map = {
                "lines": 0,
                "grid": 1,
                "triangles": 2,
                "hexagons": 3,
                "concentric": 4,
                "zigzag": 5,
            }
            pattern_idx = _pattern_map.get(self.infill_pattern.value, 0)
            config.set_infill(
                density=self.infill_density * 100,
                pattern=pattern_idx,
            )
            # PlanarSlicer speeds are in mm/min; ORNLSlicerConfig expects mm/s
            config.set_speed(
                print_speed_mm_s=self.print_speed / 60.0,
                travel_speed_mm_s=self.travel_speed / 60.0,
            )
            config.set_support(enabled=self.support_enabled)

            # Slice with ORNL Slicer 2
            slicer = ORNLSlicer()
            toolpath = slicer.slice(temp_stl.name, config)

            logger.info(
                "Slicing complete: %d layers, %d segments",
                toolpath.total_layers,
                len(toolpath.segments),
            )

            return toolpath

        finally:
            os.unlink(temp_stl.name)
