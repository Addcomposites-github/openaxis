"""Tests for PlanarSlicer — parameter defaults, validation, ORNL Slicer 2 delegation.

ORNL Slicer 2 is a C++ desktop application, not a pip-installable library.
We mock the ORNLSlicer subprocess wrapper to test the PlanarSlicer logic
without requiring the binary installed.
"""

import sys
import types

import pytest
from unittest.mock import patch, MagicMock

from openaxis.slicing.planar_slicer import PlanarSlicer
from openaxis.slicing.toolpath import InfillPattern, Toolpath, ToolpathSegment, ToolpathType


@pytest.mark.unit
@pytest.mark.slicing
class TestPlanarSlicerDefaults:
    """Verify constructor defaults match docstring specification."""

    def test_default_layer_height(self):
        s = PlanarSlicer()
        assert s.layer_height == 1.0

    def test_default_extrusion_width(self):
        s = PlanarSlicer()
        assert s.extrusion_width == 1.0

    def test_default_wall_count(self):
        s = PlanarSlicer()
        assert s.wall_count == 2

    def test_default_infill_density(self):
        s = PlanarSlicer()
        assert s.infill_density == 0.2

    def test_default_infill_pattern(self):
        s = PlanarSlicer()
        assert s.infill_pattern == InfillPattern.LINES

    def test_default_support_disabled(self):
        s = PlanarSlicer()
        assert s.support_enabled is False

    def test_wall_width_defaults_to_extrusion_width(self):
        s = PlanarSlicer(extrusion_width=2.5)
        assert s.wall_width == 2.5

    def test_wall_width_override(self):
        s = PlanarSlicer(extrusion_width=2.5, wall_width=3.0)
        assert s.wall_width == 3.0


@pytest.mark.unit
@pytest.mark.slicing
class TestPlanarSlicerCustomParams:
    """Verify constructor accepts and stores custom parameters."""

    def test_custom_params(self):
        s = PlanarSlicer(
            layer_height=2.0,
            extrusion_width=3.0,
            wall_count=4,
            infill_density=0.5,
            infill_pattern=InfillPattern.GRID,
            support_enabled=True,
            seam_angle=90.0,
            print_speed=2000.0,
            travel_speed=8000.0,
        )
        assert s.layer_height == 2.0
        assert s.extrusion_width == 3.0
        assert s.wall_count == 4
        assert s.infill_density == 0.5
        assert s.infill_pattern == InfillPattern.GRID
        assert s.support_enabled is True
        assert s.seam_angle == 90.0
        assert s.print_speed == 2000.0
        assert s.travel_speed == 8000.0

    def test_advanced_params(self):
        s = PlanarSlicer(
            seam_mode="random",
            seam_shape="scarf",
            lead_in_distance=5.0,
            lead_in_angle=30.0,
            lead_out_distance=3.0,
            lead_out_angle=60.0,
        )
        assert s.seam_mode == "random"
        assert s.seam_shape == "scarf"
        assert s.lead_in_distance == 5.0
        assert s.lead_out_distance == 3.0


@pytest.mark.unit
@pytest.mark.slicing
class TestPlanarSlicerSlice:
    """Test slice() method with mocked ORNL Slicer 2."""

    def test_slice_raises_when_ornl_unavailable(self):
        """When ORNL Slicer 2 is not installed, slice() raises ImportError."""
        slicer = PlanarSlicer()
        mock_mesh = MagicMock()

        # ORNLSlicer is imported locally inside slice(), so we inject a
        # fake ornl_slicer module into sys.modules.
        mock_ornl_module = types.ModuleType("openaxis.slicing.ornl_slicer")
        MockORNL = MagicMock()
        MockORNL.is_available.return_value = False
        mock_ornl_module.ORNLSlicer = MockORNL
        mock_ornl_module.ORNLSlicerConfig = MagicMock()

        with patch.dict(sys.modules, {"openaxis.slicing.ornl_slicer": mock_ornl_module}):
            with pytest.raises(ImportError, match="ORNL Slicer 2 binary not found"):
                slicer.slice(mock_mesh)

    def test_slice_delegates_to_ornl(self):
        """When ORNL Slicer 2 is available, slice() delegates to the wrapper."""
        from compas.geometry import Point

        slicer = PlanarSlicer(
            layer_height=1.5,
            extrusion_width=2.0,
            wall_count=3,
            infill_density=0.4,
        )

        # Build a mock toolpath result with correct field names
        mock_toolpath = Toolpath()
        mock_toolpath.add_segment(
            ToolpathSegment(
                points=[Point(0, 0, 0), Point(10, 0, 0), Point(10, 10, 0)],
                type=ToolpathType.PERIMETER,
                layer_index=0,
                speed=1000.0,
            )
        )

        mock_mesh = MagicMock()
        mock_mesh.vertices.return_value = [0, 1, 2, 3]
        mock_mesh.faces.return_value = [0, 1]
        mock_mesh.vertex_coordinates.return_value = [0.0, 0.0, 0.0]
        mock_mesh.face_vertices.return_value = [0, 1, 2]

        # Build fake ornl_slicer module for local import inside slice()
        mock_ornl_module = types.ModuleType("openaxis.slicing.ornl_slicer")
        MockORNL = MagicMock()
        MockORNL.is_available.return_value = True
        mock_slicer_instance = MockORNL.return_value
        mock_slicer_instance.slice.return_value = mock_toolpath
        mock_ornl_module.ORNLSlicer = MockORNL

        MockConfig = MagicMock()
        mock_config_instance = MockConfig.return_value
        mock_ornl_module.ORNLSlicerConfig = MockConfig

        with patch.dict(sys.modules, {"openaxis.slicing.ornl_slicer": mock_ornl_module}), \
             patch("trimesh.Trimesh") as MockTrimesh, \
             patch("tempfile.NamedTemporaryFile") as MockTempFile, \
             patch("os.unlink"):

            mock_trimesh_instance = MockTrimesh.return_value

            mock_temp = MagicMock()
            mock_temp.name = "/tmp/test.stl"
            MockTempFile.return_value = mock_temp

            result = slicer.slice(mock_mesh)

            assert isinstance(result, Toolpath)
            assert len(result.segments) == 1
            mock_config_instance.set_layer_height.assert_called_once_with(1.5)
            mock_config_instance.set_bead_width.assert_called_once_with(2.0)
            mock_config_instance.set_perimeters.assert_called_once_with(3)
