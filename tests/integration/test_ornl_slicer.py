"""
Integration tests for ORNL Slicer 2 subprocess wrapper.

These tests require the ORNL Slicer 2 binary to be installed on the system.
Tests will be automatically skipped if the binary is not found.

Set ORNL_SLICER2_PATH environment variable to the slicer binary path,
or install to the default location.
"""

import json
import os
import tempfile

import pytest

from openaxis.slicing.ornl_slicer import (
    ORNLSlicer,
    ORNLSlicerConfig,
    find_slicer_executable,
)

_HAS_SLICER = find_slicer_executable() is not None

_requires_slicer = pytest.mark.skipif(
    not _HAS_SLICER,
    reason="ORNL Slicer 2 binary not found (set ORNL_SLICER2_PATH)",
)


class TestORNLSlicerConfig:
    """Test configuration builder (always runs — no binary needed)."""

    def test_default_config(self):
        """Default config should have sensible defaults."""
        config = ORNLSlicerConfig()
        d = config.to_dict()
        # .s2c format: {"header": {...}, "settings": [{...}]}
        assert "header" in d
        assert "settings" in d
        s = d["settings"][0]
        # Default layer_height is 200 µm (0.2 mm)
        assert s["layer_height"] == 200
        assert s["perimeter"] is True

    def test_set_layer_height(self):
        """Config should allow setting layer height (mm → µm)."""
        config = ORNLSlicerConfig()
        config.set_layer_height(0.5)
        s = config.to_dict()["settings"][0]
        assert s["layer_height"] == 500  # 0.5 mm = 500 µm
        assert config.get_layer_height_mm() == 0.5

    def test_set_infill(self):
        """Config should allow setting infill parameters."""
        config = ORNLSlicerConfig()
        config.set_infill(density=50, pattern=1)
        s = config.to_dict()["settings"][0]
        assert s["infill_density"] == 50
        assert s["infill_pattern"] == 1
        assert s["infill"] is True

    def test_save_config(self):
        """Config should save to JSON file with real .s2c structure."""
        config = ORNLSlicerConfig("WAAM")
        config.set_layer_height(1.5)
        config.set_speed(print_speed_mm_s=30.0)

        with tempfile.NamedTemporaryFile(
            suffix=".s2c", delete=False, mode="w"
        ) as f:
            path = f.name

        try:
            config.save(path)
            with open(path) as f:
                loaded = json.load(f)
            assert loaded["header"]["created_by"] == "OpenAxis"
            s = loaded["settings"][0]
            assert s["layer_height"] == 1500  # 1.5 mm = 1500 µm
            assert s["machine_type"] == 3  # WAAM
        finally:
            os.remove(path)

    def test_fluent_api(self):
        """Config methods should support fluent chaining."""
        config = (
            ORNLSlicerConfig("FDM")
            .set_layer_height(0.2)
            .set_bead_width(0.4)
            .set_infill(density=20, pattern=1)
            .set_perimeters(3)
            .set_speed(60.0, 120.0)
            .set_support(enabled=True, angle_deg=50.0)
        )
        s = config.to_dict()["settings"][0]
        assert s["layer_height"] == 200  # 0.2 mm
        assert s["default_width"] == 400  # 0.4 mm
        assert s["infill_density"] == 20
        assert s["perimeter_count"] == 3
        assert s["support"] is True


@_requires_slicer
class TestORNLSlicerInit:
    """Test slicer initialization (requires binary)."""

    def test_init_with_found_binary(self):
        """Slicer should initialize when binary is found."""
        slicer = ORNLSlicer()
        assert slicer.executable is not None

    def test_init_with_explicit_path(self):
        """Slicer should accept explicit path."""
        path = find_slicer_executable()
        slicer = ORNLSlicer(executable_path=path)
        assert slicer.executable == path


class TestORNLSlicerNotInstalled:
    """Tests for when slicer is not installed."""

    @pytest.mark.skipif(
        _HAS_SLICER, reason="Slicer IS installed — skipping not-found test"
    )
    def test_not_found_raises(self):
        """Slicer should raise FileNotFoundError if binary not found."""
        with pytest.raises(FileNotFoundError, match="not found"):
            ORNLSlicer()

    def test_is_available(self):
        """is_available should reflect actual binary availability."""
        assert ORNLSlicer.is_available() == _HAS_SLICER


@_requires_slicer
class TestORNLSlicing:
    """End-to-end slicing tests (requires binary + trimesh for test STL)."""

    @pytest.fixture()
    def test_stl(self, tmp_path):
        """Create a simple box STL for testing."""
        try:
            import trimesh
        except ImportError:
            pytest.skip("trimesh not installed")
        box = trimesh.creation.box(extents=[20, 20, 10])
        stl_path = str(tmp_path / "test_box.stl")
        box.export(stl_path)
        return stl_path

    def test_slice_box(self, test_stl):
        """Slicing a 20x20x10 box should produce multi-layer toolpath."""
        slicer = ORNLSlicer()
        config = ORNLSlicerConfig("FDM")
        config.set_layer_height(0.2)
        config.set_bead_width(0.4)
        config.set_perimeters(2)

        toolpath = slicer.slice(test_stl, config)
        assert len(toolpath.segments) > 0
        assert toolpath.total_layers > 1
        assert toolpath.get_total_length() > 0
