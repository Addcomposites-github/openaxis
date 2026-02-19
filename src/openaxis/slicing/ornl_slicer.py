"""
ORNL Slicer 2 subprocess wrapper for additive manufacturing slicing.

ORNL Slicer 2 is a production-grade slicer used by 50+ equipment manufacturers
for FDM, WAAM, LFAM (Large Format Additive Manufacturing), MFAM (Metal),
and Concrete 3D printing.

This module wraps the Slicer 2 CLI binary via subprocess, using JSON-based
.s2c configuration files to control slicing parameters.

CLI mode: When called with command-line arguments (argc > 1), Slicer 2
runs headless with QCoreApplication (no GUI).

Repository: https://github.com/ORNLSlicer/Slicer-2
Version: v1.3.001 (Aug 2025)
License: Custom ORNL license

Requires: ORNL Slicer 2 binary installed on the system.
- Windows: slicer2.exe (from installer or portable)
- Linux: Slicer-2 AppImage

This is a subprocess wrapper — no custom slicing math.
All slicing is delegated to the ORNL Slicer 2 binary.
"""

import json
import logging
import os
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from compas.geometry import Point

from openaxis.slicing.toolpath import Toolpath, ToolpathSegment, ToolpathType

logger = logging.getLogger(__name__)

# Default search paths for the ORNL Slicer 2 CLI binary.
# Prefer slicer2_cli.exe (headless) over slicer2.exe (GUI).
_DEFAULT_PATHS_WINDOWS = [
    # Portable / user-installed locations (CLI first)
    os.path.expanduser(r"~\ORNL-Slicer-2\bin\slicer2_cli.exe"),
    os.path.expanduser(r"~\ORNL-Slicer-2\bin\slicer2.exe"),
    # System install locations
    r"C:\Program Files\ORNL Slicer 2\slicer2_cli.exe",
    r"C:\Program Files\ORNL Slicer 2\slicer2.exe",
    r"C:\Program Files (x86)\ORNL Slicer 2\slicer2_cli.exe",
    r"C:\Program Files (x86)\ORNL Slicer 2\slicer2.exe",
]
_DEFAULT_PATHS_LINUX = [
    "/usr/local/bin/slicer2_cli",
    "/usr/local/bin/slicer2",
    "/opt/ornl-slicer2/slicer2_cli",
    "/opt/ornl-slicer2/slicer2",
]


def find_slicer_executable() -> Optional[str]:
    """
    Search for the ORNL Slicer 2 binary on the system.

    Checks the ORNL_SLICER2_PATH environment variable first,
    then searches default installation directories.

    Returns:
        Path to the slicer binary, or None if not found.
    """
    # Check environment variable first
    env_path = os.environ.get("ORNL_SLICER2_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # Search default paths
    if platform.system() == "Windows":
        search_paths = _DEFAULT_PATHS_WINDOWS
    else:
        search_paths = _DEFAULT_PATHS_LINUX

    for path in search_paths:
        if os.path.isfile(path):
            return path

    return None


class ORNLSlicerConfig:
    """
    Configuration builder for ORNL Slicer 2 .s2c files.

    ORNL Slicer 2 uses JSON-based configuration files (.s2c) with a
    ``{"header": {...}, "settings": [{...}]}`` structure.

    Internal units are **microns** (µm) for lengths and µm/min for speeds,
    matching the native .s2c format used by the ORNL Slicer 2 templates
    shipped in ``share/slicer2/templates/``.

    The public API accepts **millimetres** and converts internally.
    """

    # Process type → machine_type integer mapping used in .s2c files.
    _MACHINE_TYPES = {
        "FDM": 1,
        "LFAM": 0,
        "WAAM": 3,
        "MFAM": 0,
        "Concrete": 4,
    }

    def __init__(self, process_type: str = "FDM"):
        """
        Initialize slicer configuration.

        Args:
            process_type: Manufacturing process type.
                Supported: 'FDM', 'WAAM', 'LFAM', 'MFAM', 'Concrete'
        """
        self.process_type = process_type
        self._settings: Dict[str, Any] = self._base_settings()

    @staticmethod
    def _mm_to_um(mm: float) -> int:
        """Convert millimetres to microns (ORNL Slicer 2 native unit)."""
        return int(round(mm * 1000))

    def _base_settings(self) -> Dict[str, Any]:
        """
        Create base settings dict matching the real .s2c schema.

        Defaults are modelled after the Desktop_04mm.s2c template.
        """
        machine_type = self._MACHINE_TYPES.get(self.process_type, 1)
        return {
            "syntax": 11,
            "machine_type": machine_type,
            "main_extruder": 0,
            "extruder_xyz_offsets": 0,
            "supports_G2_3": False,
            # Workspace limits (microns)
            "minimum_x": 0,
            "maximum_x": 200000,
            "minimum_y": 0,
            "maximum_y": 200000,
            "minimum_z": 0,
            "maximum_z": 200000,
            "x_offset": 0,
            "y_offset": 0,
            "z_offset": 0,
            "enable_w_axis": False,
            "maximum_w": 0.0,
            "minimum_w": 0.0,
            "layer_change": 0,
            "doffing": False,
            "doffing_location": 0,
            "enable_grid_x": True,
            "grid_x_distance": 10000,
            "enable_grid_y": True,
            "grid_y_distance": 10000,
            "final_z_lift": False,
            "final_z_lift_amount": 0,
            "enable_tamper": False,
            "tamper_voltage": 0,
            # Speeds (microns / min)
            "max_xy_speed": 200000,
            "min_xy_speed": 10000,
            "max_extruder_speed": 0,
            "w_table_speed": 0,
            "z_speed": 50000,
            # Acceleration
            "enable_dynamic_acceleration": False,
            "default_acceleration": 0,
            "perimeter_acceleration": 588399,
            "inset_acceleration": 784532,
            "skin_acceleration": 882599,
            "infill_acceleration": 882599,
            "skeleton_acceleration": 882599,
            "support_acceleration": 882599,
            "travel_acceleration": 980666,
            # Startup / end codes
            "enable_default_startup_code": True,
            "enable_material_load": False,
            "enable_wait_for_user": False,
            "enable_bounding_box": False,
            "enable_relative_coordinates": False,
            "start_code": "",
            "layer_change_code": "",
            "end_code": "",
            # Material
            "printing_material": 8,
            "other_density": 0,
            # Startup / slowdown defaults
            "perimeter_start-up": False,
            "perimeter_start-up_distance": 3000,
            "perimeter_start-up_extruder_speed": 150,
            "perimeter_start-up_speed": 6000,
            "inset_start-up": False,
            "inset_start-up_distance": 3000,
            "inset_start-up_extruder_speed": 150,
            "inset_start-up_speed": 6000,
            "skin_start-up": False,
            "skin_start-up_distance": 2000,
            "skin_start-up_extruder_speed": 150,
            "skin_start-up_speed": 6000,
            "infill_start-up": False,
            "infill_start-up_distance": 2000,
            "infill_start-up_extruder_speed": 150,
            "infill_start-up_speed": 6000,
            "perimeter_slow_down": False,
            "perimeter_slow_down_distance": 8000,
            "perimeter_slow_down_extruder_speed": 50,
            "perimeter_slow_down_speed": 19000,
            "inset_slow_down": False,
            "inset_slow_down_distance": 8000,
            "inset_slow_down_extruder_speed": 50,
            "inset_slow_down_speed": 19000,
            "skin_slow_down": False,
            "skin_slow_down_distance": 8000,
            "skin_slow_down_extruder_speed": 50,
            "skin_slow_down_speed": 19000,
            "infill_slow_down": False,
            "infill_slow_down_distance": 8000,
            "infill_slow_down_extruder_speed": 50,
            "infill_slow_down_speed": 19000,
            # Wipe
            "perimeter_wipe": False,
            "perimeter_wipe_direction": 0,
            "perimeter_wipe_distance": 20000,
            "perimeter_wipe_speed": 100000,
            "inset_wipe": False,
            "inset_wipe_direction": 0,
            "inset_wipe_distance": 20000,
            "inset_wipe_speed": 100000,
            "skeleton_wipe": False,
            "skeleton_wipe_direction": 0,
            "skeleton_wipe_distance": 20000,
            "skeleton_wipe_speed": 100000,
            "skin_wipe": False,
            "skin_wipe_direction": 0,
            "skin_wipe_distance": 20000,
            "skin_wipe_speed": 100000,
            "infill_wipe": False,
            "infill_wipe_direction": 0,
            "infill_wipe_distance": 20000,
            "infill_wipe_speed": 100000,
            # Spiral
            "enable_spiral_perimeter": False,
            "enable_spiral_inset": False,
            "enable_spiral_skin": False,
            "enable_spiral_infill": False,
            "spiral_end_of_layer": False,
            "spiral_lift_height": 0,
            "spiral_lift_points": 0,
            "spiral_lift_radius": 0,
            "spiral_lift_speed": 0,
            # Extrusion
            "initial_purge_duration": 0,
            "initial_purge_dwell_screw_rpm": 0,
            "initial_purge_tip_wipe_delay": 0,
            "initial_extruder_speed": 0,
            "extruder_on_delay_perimeter": 0,
            "extruder_on_delay_inset": 0,
            "extruder_on_delay_skin": 0,
            "extruder_on_delay_infill": 0,
            "extruder_off_delay": 0,
            "servo_extruder_to_travel_speed": False,
            "filament_diameter": 1750,
            "perimeter_filament_extrusion_multiplier": 1,
            "inset_filament_extrusion_multiplier": 1,
            "skin_filament_extrusion_multiplier": 1,
            "infill_filament_extrusion_multiplier": 1,
            # Retraction
            "retraction": True,
            "retract_min_travel_length": 1500,
            "retraction_length": 3200,
            "retraction_speed": 70000,
            "retraction_layer_change": True,
            "wipe_retract": False,
            "enable_extra_extrusion": False,
            "filament_prime_speed": 0,
            # Thermal
            "bed_temperature": 333.15,
            "extruder0_temperature": 483.15,
            "extruder1_temperature": 0,
            "standby0_temperature": 0,
            "standby1_temperature": 0,
            "fan": False,
            "fan_min_speed": 0,
            "fan_max_speed": 100,
            "force_minimum_layer_time": False,
            "minimum_layer_time": 30,
            # Adhesion
            "raft": False,
            "raft_offset": 0,
            "raft_layers": 0,
            "raft_bead_width": 4636,
            "brim": False,
            "brim_width": 12636,
            "brim_layer_count": 1,
            "brim_bead_width": 4636,
            "skirt": False,
            "skirt_loops": 1,
            "skirt_distance_from_object": 1000,
            "skirt_layer_count": 1,
            "skirt_minimum_length": 50000,
            "skirt_bead_width": 400,
            # Multi-material
            "enable_multi_material": False,
            "perimeter_material_num": 0,
            "inset_material_num": 0,
            "skin_material_num": 0,
            "infill_material_num": 0,
            "support_material_num": 0,
            "material_transition_distance": 0,
            # Path options
            "enable_single_path": False,
            "enable_bridge_exclusion": False,
            "enable_zippering": False,
            # Core geometry (microns)
            "layer_height": 200,
            "nozzle_diameter": 400,
            "default_width": 400,
            "default_speed": 60000,
            "default_extruder_speed": 0,
            "minimum_extrude_length": 2000,
            # Perimeter
            "perimeter": True,
            "perimeter_count": 1,
            "perimeter_width": 400,
            "perimeter_speed": 60000,
            "perimeter_extruder_speed": 0,
            "perimeter_minimum_path_length": 4000,
            "perimeter_reverse_direction": 0,
            # Insets
            "inset": True,
            "inset_count": 2,
            "inset_width": 400,
            "inset_speed": 70000,
            "inset_extruder_speed": 0,
            "inset_minimum_path_length": 4000,
            "inset_reverse_direction": 0,
            # Skin (top/bottom solid layers)
            "skin": False,
            "skin_top_count": 3,
            "skin_bottom_count": 3,
            "skin_pattern": 0,
            "skin_angle": 0,
            "skin_angle_rotation": 1.5708,
            "skin_width": 400,
            "skin_speed": 70000,
            "skin_extruder_speed": 0,
            "skin_exterior_overlap": 0,
            "skin_minimum_path_length": 4000,
            "skin_prestart": False,
            "skin_prestart_distance": 10000,
            "skin_prestart_extruder_speed": 50,
            "skin_prestart_speed": 30000,
            # Infill
            "infill": False,
            "infill_line_spacing": 800,
            "infill_density": 50,
            "infill_pattern": 0,
            "infill_angle": 0.0,
            "infill_angle_rotation": 1.5708,
            "infill_overlap_distance": 0,
            "infill_speed": 90000,
            "infill_width": 400,
            "infill_extruder_speed": 0,
            "infill_combine_every_x_layers": 0,
            "infill_minimum_path_length": 4000,
            "infill_prestart": False,
            "infill_prestart_distance": 1000,
            "infill_prestart_extruder_speed": 50,
            "infill_prestart_speed": 3000,
            "infill_sector_count": 12,
            # Skeleton
            "skeleton": False,
            "skeleton_input": 0,
            "skeleton_input_cleaning_distance": 25,
            "skeleton_output_cleaning_distance": 254,
            "skeleton_width": 400,
            "skeleton_minimum_path_length": 5000,
            "skeleton_speed": 65000,
            "skeleton_extruder_speed": 0,
            # Support
            "support": False,
            "support_extruder": 0,
            "support_print_first": False,
            "support_tapering": True,
            "support_threshold_angle": 0.698132,
            "support_xy_distance": 700,
            "support_layer_offset": 0,
            "support_minimum_infill_area": 5806440000,
            "support_minimum_area": 23225800000,
            "support_pattern": 0,
            "support_line_spacing": 1000,
            # Travel
            "minimum_travel_length": 800,
            "minimum_travel_for_lift": 5000,
            "travel_speed": 100000,
            "travel_lift_height": 200,
            # Start/end codes per region
            "perimeter_start_code": "",
            "perimeter_end_code": "",
            "inset_start_code": "",
            "inset_end_code": "",
            "skin_start_code": "",
            "skin_end_code": "",
            "infill_start_code": "",
            "infill_end_code": "",
            # Post-processing
            "smoothing": True,
            "smoothing_tolerance": 76,
            "enable_spiralize_mode": False,
            "enable_fix_model": False,  # Off by default: True fills holes in open shells
            "oversize": False,
            "oversize_distance": 0,
            "enable_width_height": False,
            "enable_inside_out_printing": False,
            "island_order_optimization": 0,
            "path_order_optimization": 0,
            "custom_path_order_x_location": 0,
            "custom_path_order_y_location": 0,
            "enable_second_custom_path_location": False,
            "custom_second_path_order_x_location": 0,
            "custom_second_path_order_y_location": 0,
            "consecutive_path_distance_threshold": 0,
            # Scanner (disabled by default)
            "laser_scanner": False,
            "laser_scanner_height_offset": 0,
            "laser_scanner_x_offset": 0,
            "laser_scanner_y_offset": 0,
            "laser_scanner_height": 0,
            "laser_scanner_width": 100000,
            "laser_scanner_step_distance": 0,
            "laser_scan_line_resolution": 0,
            "laser_scanner_axis": 0,
            "invert_laser_scanner_head": True,
            "enable_bed_scan": True,
            "scan_layer_skip": 1,
            "enable_scanner_buffer": True,
            "buffer_distance": 10000,
            "transmit_height_map": False,
            "thermal_scanner": False,
            "thermal_scanner_temperature_cutoff": 0,
            "thermal_scanner_x_offset": 1701800,
            "thermal_scanner_y_offset": 228600,
            # Orientation
            "slicing_plane_pitch": 0,
            "slicing_plane_yaw": 0,
            "slicing_plane_roll": 0,
        }

    # -- Public API (accepts millimetres, converts to microns) --

    def set_layer_height(self, height_mm: float) -> "ORNLSlicerConfig":
        """Set layer height in mm."""
        self._settings["layer_height"] = self._mm_to_um(height_mm)
        return self

    def set_bead_width(self, width_mm: float) -> "ORNLSlicerConfig":
        """Set bead/extrusion width in mm."""
        um = self._mm_to_um(width_mm)
        self._settings["default_width"] = um
        self._settings["nozzle_diameter"] = um
        self._settings["perimeter_width"] = um
        self._settings["inset_width"] = um
        self._settings["infill_width"] = um
        self._settings["skin_width"] = um
        return self

    def set_infill(
        self, density: float = 100, pattern: int = 0
    ) -> "ORNLSlicerConfig":
        """
        Set infill parameters.

        Args:
            density: Infill density percentage (0-100)
            pattern: Infill pattern index (0=lines, 1=grid, etc.)
        """
        self._settings["infill"] = density > 0
        self._settings["infill_density"] = density
        self._settings["infill_pattern"] = pattern
        return self

    def set_perimeters(self, count: int) -> "ORNLSlicerConfig":
        """Set number of perimeter shells."""
        self._settings["perimeter"] = count > 0
        self._settings["perimeter_count"] = count
        return self

    def set_speed(
        self, print_speed_mm_s: float = 50.0, travel_speed_mm_s: float = 100.0
    ) -> "ORNLSlicerConfig":
        """Set print and travel speeds in mm/s (converted to µm/min)."""
        # ORNL uses µm/min: mm/s * 1000 µm/mm * 60 s/min
        print_um_min = int(round(print_speed_mm_s * 1000 * 60))
        travel_um_min = int(round(travel_speed_mm_s * 1000 * 60))
        self._settings["default_speed"] = print_um_min
        self._settings["perimeter_speed"] = print_um_min
        self._settings["inset_speed"] = print_um_min
        self._settings["infill_speed"] = print_um_min
        self._settings["skin_speed"] = print_um_min
        self._settings["travel_speed"] = travel_um_min
        return self

    def set_support(
        self, enabled: bool = True, angle_deg: float = 45.0
    ) -> "ORNLSlicerConfig":
        """Set support generation parameters."""
        import math

        self._settings["support"] = enabled
        self._settings["support_threshold_angle"] = math.radians(angle_deg)
        return self

    def set_fix_model(self, enabled: bool) -> "ORNLSlicerConfig":
        """Enable/disable ORNL Slicer 2 auto mesh repair (fills holes in open shells).

        When True, ORNL will attempt to close open meshes (e.g. filling the top
        of a nozzle). Set to True only for watertight solid parts that may have
        minor mesh defects.
        """
        self._settings["enable_fix_model"] = enabled
        return self

    def set_custom(self, key: str, value: Any) -> "ORNLSlicerConfig":
        """Set a raw .s2c configuration key (in native ORNL units)."""
        self._settings[key] = value
        return self

    def get_layer_height_mm(self) -> float:
        """Return the configured layer height in mm."""
        return self._settings["layer_height"] / 1000.0

    def to_dict(self) -> Dict[str, Any]:
        """Return the full .s2c dictionary."""
        return {
            "header": {
                "created_by": "OpenAxis",
                "created_on": "",
                "last_modified": "",
                "version": 2.0,
                "lock": "false",
            },
            "settings": [self._settings.copy()],
        }

    def save(self, path: str) -> str:
        """
        Save configuration to a .s2c (JSON) file.

        Args:
            path: Output file path

        Returns:
            Path to the saved file
        """
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path


class ORNLSlicer:
    """
    ORNL Slicer 2 subprocess wrapper.

    Calls the ORNL Slicer 2 CLI binary to slice meshes into toolpaths.
    All slicing computation is done by the external binary — this class
    only handles configuration, subprocess management, and output parsing.

    Usage::

        slicer = ORNLSlicer(executable_path="/path/to/slicer2.exe")
        config = ORNLSlicerConfig("FDM")
        config.set_layer_height(0.5)
        toolpath = slicer.slice("model.stl", config)

    Or with auto-detection::

        slicer = ORNLSlicer()  # Searches default paths
        toolpath = slicer.slice("model.stl")

    Args:
        executable_path: Path to the slicer binary. If None, searches
                         default paths and ORNL_SLICER2_PATH env var.
        timeout: Maximum time in seconds to wait for slicing (default: 300)

    Raises:
        FileNotFoundError: If the slicer binary is not found.
    """

    def __init__(
        self,
        executable_path: Optional[str] = None,
        timeout: int = 300,
    ):
        if executable_path is None:
            executable_path = find_slicer_executable()

        if executable_path is None:
            raise FileNotFoundError(
                "ORNL Slicer 2 binary not found. "
                "Install from https://github.com/ORNLSlicer/Slicer-2 or "
                "set ORNL_SLICER2_PATH environment variable."
            )

        if not os.path.isfile(executable_path):
            raise FileNotFoundError(
                f"ORNL Slicer 2 binary not found at: {executable_path}"
            )

        self.executable = executable_path
        self.timeout = timeout
        logger.info("ORNL Slicer 2 initialized: %s", executable_path)

    def slice(
        self,
        mesh_path: str,
        config: Optional[ORNLSlicerConfig] = None,
        output_dir: Optional[str] = None,
    ) -> Toolpath:
        """
        Slice a mesh file using ORNL Slicer 2.

        Calls the v1.3 CLI with::

            slicer2_cli --input_stl_files <mesh>
                        --input_global_settings <config.s2c>
                        --output_location <dir>
                        --overwrite_output_file
                        --shift_parts_on_load true
                        --align_parts true

        Args:
            mesh_path: Path to STL/OBJ/3MF mesh file
            config: Slicer configuration. If None, uses defaults.
            output_dir: Directory for output files. If None, uses temp dir.

        Returns:
            Toolpath object with sliced segments

        Raises:
            FileNotFoundError: If mesh file doesn't exist
            RuntimeError: If slicing fails
            TimeoutError: If slicing exceeds timeout
        """
        mesh_path = str(Path(mesh_path).resolve())
        if not os.path.exists(mesh_path):
            raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

        if config is None:
            config = ORNLSlicerConfig()

        # Create temporary directory for output
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="ornl_slicer_")

        # Save configuration file
        config_path = os.path.join(output_dir, "config.s2c")
        config.save(config_path)

        # ORNL Slicer 2 v1.3 stores session data in
        #   %APPDATA%/slicer2_cli/app.history  (Windows)
        # If this file is empty (0 bytes) the slicer crashes with
        # "parse error … attempting to parse an empty input".
        # Guard against this by removing empty history files.
        self._fix_corrupt_history()

        # ORNL Slicer 2 v1.3 CLI arguments:
        #   --input_stl_files <file>         STL to slice
        #   --input_global_settings <file>   .s2c settings file
        #   --output_location <dir>          output directory
        #   --overwrite_output_file          overwrite existing output
        #   --shift_parts_on_load true       auto-shift STL
        #   --align_parts true               center part
        cmd = [
            self.executable,
            "--input_stl_files", mesh_path,
            "--input_global_settings", config_path,
            "--output_location", output_dir,
            "--overwrite_output_file",
            # Disable ORNL's auto-centering — the caller is responsible for
            # pre-centering the mesh.  With both enabled, the mesh gets
            # double-centered and the G-code output no longer matches the
            # coordinate frame expected by the frontend.
            "--shift_parts_on_load", "false",
            "--align_parts", "false",
            "--use_implicit_transforms", "true",
        ]

        logger.info(
            "Slicing %s with ORNL Slicer 2 (config: %s, output: %s)",
            mesh_path,
            config_path,
            output_dir,
        )

        # Run slicer subprocess
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=output_dir,
            )
        except subprocess.TimeoutExpired as e:
            raise TimeoutError(
                f"ORNL Slicer 2 timed out after {self.timeout}s. "
                f"Consider increasing timeout for large models."
            ) from e

        if result.returncode != 0:
            raise RuntimeError(
                f"ORNL Slicer 2 failed (exit code {result.returncode}):\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        # Find the generated G-code file in the output directory.
        # ORNL Slicer 2 names the output after the input STL stem.
        gcode_path = self._find_gcode_output(output_dir, mesh_path)

        if gcode_path is None:
            raise RuntimeError(
                f"ORNL Slicer 2 did not produce G-code output in {output_dir}. "
                f"stdout: {result.stdout}"
            )

        toolpath = self._parse_gcode(
            gcode_path,
            layer_height=config.get_layer_height_mm(),
        )

        logger.info(
            "Slicing complete: %d segments, %d layers, %.1f mm total length",
            len(toolpath.segments),
            toolpath.total_layers,
            toolpath.get_total_length(),
        )

        return toolpath

    @staticmethod
    def _find_gcode_output(
        output_dir: str, mesh_path: str
    ) -> Optional[str]:
        """
        Locate the G-code file produced by ORNL Slicer 2.

        ORNL Slicer 2 v1.3 writes the output file **adjacent** to the
        output_location directory — e.g. if ``--output_location /tmp/out``
        the G-code is written as ``/tmp/out.gcode``.  It may also place
        files inside the directory named after the STL stem.
        """
        import glob as glob_mod

        stem = Path(mesh_path).stem

        # 1. Check for <output_dir>.gcode (ORNL v1.3 default behaviour)
        for ext in (".gcode", ".nc", ".tap"):
            adjacent = output_dir.rstrip(os.sep) + ext
            if os.path.isfile(adjacent):
                return adjacent

        # 2. Check inside the output directory for <stem>.gcode
        for ext in (".gcode", ".nc", ".tap"):
            candidate = os.path.join(output_dir, stem + ext)
            if os.path.isfile(candidate):
                return candidate

        # 3. Fall back to any .gcode file inside the directory
        gcode_files = glob_mod.glob(os.path.join(output_dir, "*.gcode"))
        if gcode_files:
            return gcode_files[0]

        # 4. Any output file
        for pattern in ("*.nc", "*.tap"):
            matches = glob_mod.glob(os.path.join(output_dir, pattern))
            if matches:
                return matches[0]

        return None

    @staticmethod
    def _fix_corrupt_history() -> None:
        """
        Remove empty ``app.history`` file that crashes ORNL Slicer 2.

        ORNL Slicer 2 v1.3 stores session history in
        ``%APPDATA%/slicer2_cli/app.history``. If the process is killed
        mid-write (or exits uncleanly) this file can be left as 0 bytes.
        On the next invocation the slicer attempts to parse it as JSON,
        gets "empty input" and aborts with exit code 3.

        This method detects and removes the corrupt file so the slicer
        can start fresh.
        """
        if platform.system() == "Windows":
            appdata = os.environ.get("APPDATA", "")
            history = os.path.join(appdata, "slicer2_cli", "app.history")
        else:
            history = os.path.expanduser("~/.local/share/slicer2_cli/app.history")

        try:
            if os.path.isfile(history) and os.path.getsize(history) == 0:
                os.remove(history)
                logger.warning(
                    "Removed empty ORNL Slicer 2 history file: %s", history
                )
        except OSError:
            pass  # Best-effort — don't fail the slice if we can't clean up

    def _parse_gcode(
        self, gcode_path: str, layer_height: float = 1.0
    ) -> Toolpath:
        """
        Parse G-code output from ORNL Slicer 2 into a Toolpath.

        Parses standard G-code (G0/G1 moves) with layer change comments.
        ORNL Slicer 2 outputs layer markers as comments.

        Args:
            gcode_path: Path to G-code file
            layer_height: Layer height used for slicing

        Returns:
            Toolpath object
        """
        toolpath = Toolpath(
            layer_height=layer_height,
            process_type="additive",
            metadata={"source": "ORNL Slicer 2", "gcode_path": gcode_path},
        )

        current_layer = 0
        current_points: List[Point] = []
        current_type = ToolpathType.PERIMETER
        current_x, current_y, current_z = 0.0, 0.0, 0.0
        is_extruding = False

        with open(gcode_path, "r") as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and pure comments
                if not line or line.startswith(";"):
                    # Check for layer change marker.
                    # ORNL Slicer 2 v1.3 uses ";BEGINNING LAYER: N"
                    # Other slicers use ";LAYER:N" or "; layer N"
                    is_layer_marker = (
                        ";LAYER:" in line
                        or ";BEGINNING LAYER:" in line
                        or "; layer" in line.lower()
                    )
                    if is_layer_marker:
                        # Flush current segment
                        if len(current_points) >= 2:
                            seg = ToolpathSegment(
                                points=current_points,
                                type=current_type,
                                layer_index=current_layer,
                            )
                            toolpath.add_segment(seg)
                            current_points = []

                        # Parse layer number
                        try:
                            parts = line.split(":")
                            if len(parts) >= 2:
                                current_layer = int(
                                    parts[-1].strip().split()[0]
                                )
                        except (ValueError, IndexError):
                            current_layer += 1

                    # Check for type markers
                    if ";TYPE:" in line:
                        # Flush current segment
                        if len(current_points) >= 2:
                            seg = ToolpathSegment(
                                points=current_points,
                                type=current_type,
                                layer_index=current_layer,
                            )
                            toolpath.add_segment(seg)
                            current_points = []

                        type_str = line.split(":")[-1].strip().lower()
                        if "perimeter" in type_str or "wall" in type_str:
                            current_type = ToolpathType.PERIMETER
                        elif "infill" in type_str or "fill" in type_str:
                            current_type = ToolpathType.INFILL
                        elif "support" in type_str:
                            current_type = ToolpathType.SUPPORT
                        elif "travel" in type_str:
                            current_type = ToolpathType.TRAVEL
                        else:
                            current_type = ToolpathType.PERIMETER

                    continue

                # Parse G-code commands
                parts = line.split(";")[0].strip().split()
                if not parts:
                    continue

                cmd = parts[0].upper()

                if cmd in ("G0", "G1"):
                    # Movement command
                    new_x, new_y, new_z = current_x, current_y, current_z
                    has_extrusion = False

                    for param in parts[1:]:
                        if param.startswith("X") or param.startswith("x"):
                            try:
                                new_x = float(param[1:])
                            except ValueError:
                                pass
                        elif param.startswith("Y") or param.startswith("y"):
                            try:
                                new_y = float(param[1:])
                            except ValueError:
                                pass
                        elif param.startswith("Z") or param.startswith("z"):
                            try:
                                new_z = float(param[1:])
                            except ValueError:
                                pass
                        elif param.startswith("E") or param.startswith("e"):
                            try:
                                e_val = float(param[1:])
                                has_extrusion = e_val > 0
                            except ValueError:
                                pass

                    # G0 = rapid/travel, G1 = linear move
                    if cmd == "G0":
                        # Travel move — flush current segment
                        if len(current_points) >= 2:
                            seg = ToolpathSegment(
                                points=current_points,
                                type=current_type,
                                layer_index=current_layer,
                            )
                            toolpath.add_segment(seg)
                            current_points = []
                        is_extruding = False
                    else:
                        # G1 with extrusion
                        if has_extrusion and not is_extruding:
                            # Start new extrusion segment
                            if len(current_points) >= 2:
                                seg = ToolpathSegment(
                                    points=current_points,
                                    type=current_type,
                                    layer_index=current_layer,
                                )
                                toolpath.add_segment(seg)
                            current_points = [
                                Point(current_x, current_y, current_z)
                            ]
                            is_extruding = True

                    current_points.append(Point(new_x, new_y, new_z))
                    current_x, current_y, current_z = new_x, new_y, new_z

        # Flush remaining segment
        if len(current_points) >= 2:
            seg = ToolpathSegment(
                points=current_points,
                type=current_type,
                layer_index=current_layer,
            )
            toolpath.add_segment(seg)

        return toolpath

    @staticmethod
    def is_available() -> bool:
        """Check if ORNL Slicer 2 binary is available on the system."""
        return find_slicer_executable() is not None

    def get_version(self) -> Optional[str]:
        """
        Get ORNL Slicer 2 version string.

        Returns:
            Version string, or None if version query fails.
        """
        try:
            result = subprocess.run(
                [self.executable, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() or result.stderr.strip()
        except Exception:
            return None
