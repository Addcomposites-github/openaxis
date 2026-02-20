"""
Integration test: ORNL Slicer 2 subprocess mock in CI.

Verifies the full slicing pipeline works with the mocked ORNL subprocess.
This test runs in CI without the real ORNL binary installed.
"""

import pytest
from compas.geometry import Point

from openaxis.slicing.ornl_slicer import ORNLSlicer, ORNLSlicerConfig
from openaxis.slicing.toolpath import Toolpath, ToolpathType


@pytest.mark.integration
class TestORNLMockSlicing:
    """Test the ORNL Slicer 2 wrapper with mock subprocess."""

    def test_slicer_creates_with_mock(self, mock_ornl_slicer):
        """ORNLSlicer initializes when mock binary exists."""
        slicer = ORNLSlicer()
        assert slicer.executable == mock_ornl_slicer

    def test_slice_returns_toolpath(self, mock_ornl_slicer, tmp_path):
        """Slicing a mesh file returns a Toolpath with segments and layers."""
        # Create a dummy STL file (content doesn't matter — mock ignores it)
        stl_path = str(tmp_path / "test_cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        slicer = ORNLSlicer()
        config = ORNLSlicerConfig("FDM")
        config.set_layer_height(0.2)
        config.set_bead_width(0.4)

        toolpath = slicer.slice(stl_path, config)

        assert isinstance(toolpath, Toolpath)
        assert len(toolpath.segments) > 0
        assert toolpath.total_layers >= 2  # Mock G-code has 2 layers

    def test_mock_gcode_has_perimeter_and_infill(self, mock_ornl_slicer, tmp_path):
        """Mock G-code contains both perimeter and infill segments."""
        stl_path = str(tmp_path / "test.stl")
        with open(stl_path, "w") as f:
            f.write("solid test\nendsolid test\n")

        slicer = ORNLSlicer()
        toolpath = slicer.slice(stl_path)

        types = {seg.type for seg in toolpath.segments}
        assert ToolpathType.PERIMETER in types
        assert ToolpathType.INFILL in types

    def test_mock_toolpath_has_valid_points(self, mock_ornl_slicer, tmp_path):
        """Each segment has at least 2 points with valid coordinates."""
        stl_path = str(tmp_path / "test.stl")
        with open(stl_path, "w") as f:
            f.write("solid test\nendsolid test\n")

        slicer = ORNLSlicer()
        toolpath = slicer.slice(stl_path)

        for seg in toolpath.segments:
            assert len(seg.points) >= 2, f"Segment {seg.type} has < 2 points"
            for pt in seg.points:
                assert hasattr(pt, 'x') and hasattr(pt, 'y') and hasattr(pt, 'z')

    def test_config_params_applied(self, mock_ornl_slicer, tmp_path):
        """ORNLSlicerConfig params are correctly set."""
        config = ORNLSlicerConfig("WAAM")
        config.set_layer_height(1.5)
        config.set_bead_width(3.0)
        config.set_perimeters(4)
        config.set_infill(density=80, pattern=1)
        config.set_support(enabled=True, angle_deg=60.0)

        d = config.to_dict()
        settings = d["settings"][0]
        assert settings["layer_height"] == 1500  # 1.5mm -> 1500µm
        assert settings["default_width"] == 3000
        assert settings["perimeter_count"] == 4
        assert settings["infill_density"] == 80
        assert settings["support"] is True

    def test_slicer_is_available_with_mock(self, mock_ornl_slicer):
        """ORNLSlicer.is_available() returns True with mock."""
        assert ORNLSlicer.is_available() is True
