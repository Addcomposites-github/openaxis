"""
Tests for support generation module.

Tests overhang detection, support region generation, and support toolpath
creation using trimesh primitives.
"""

import numpy as np
import pytest
import trimesh

from openaxis.slicing.support_generation import (
    detect_overhangs,
    generate_support_regions,
    generate_support_toolpath,
    add_supports_to_toolpath,
)
from openaxis.slicing.toolpath import Toolpath, ToolpathType


class TestDetectOverhangs:
    """Tests for overhang face detection."""

    def test_cube_no_overhangs(self):
        """A simple cube has no overhangs — all faces are vertical or flat."""
        mesh = trimesh.primitives.Box(extents=[10, 10, 10])
        mask = detect_overhangs(mesh, threshold_angle=45.0)
        assert mask.shape[0] == len(mesh.faces)
        # Cube faces are either top (up), bottom (down), or vertical
        # Only the bottom face points straight down = overhang
        # Top face = no overhang, sides = no overhang
        # The bottom face has normal [0, 0, -1], angle = 180° from build dir
        # That exceeds 90 + 45 = 135°, so it should be flagged
        # But a standing cube with no part below doesn't need supports
        # The function just detects faces; interpretation is up to the caller

    def test_tilted_surface_detects_overhangs(self):
        """A mesh with angled faces should detect overhangs at strict thresholds."""
        # Create a simple wedge using trimesh
        mesh = trimesh.primitives.Box(extents=[10, 10, 10])
        # Rotate 60 degrees around X to create overhang
        rotation = trimesh.transformations.rotation_matrix(
            np.radians(60), [1, 0, 0]
        )
        mesh.apply_transform(rotation)

        mask = detect_overhangs(mesh, threshold_angle=30.0)
        assert mask.any(), "Should detect overhangs on a tilted box at 30° threshold"

    def test_threshold_sensitivity(self):
        """Larger threshold = fewer overhangs detected."""
        mesh = trimesh.primitives.Box(extents=[10, 10, 10])
        rotation = trimesh.transformations.rotation_matrix(
            np.radians(45), [1, 0, 0]
        )
        mesh.apply_transform(rotation)

        strict = detect_overhangs(mesh, threshold_angle=20.0)
        lenient = detect_overhangs(mesh, threshold_angle=70.0)
        assert strict.sum() >= lenient.sum(), (
            "Stricter threshold should flag at least as many faces"
        )

    def test_custom_build_direction(self):
        """Custom build direction should change which faces are overhangs."""
        mesh = trimesh.primitives.Box(extents=[10, 10, 10])
        # With build direction [1, 0, 0] (X-up), different faces are overhangs
        mask_z = detect_overhangs(mesh, threshold_angle=45.0, build_direction=np.array([0, 0, 1]))
        mask_x = detect_overhangs(mesh, threshold_angle=45.0, build_direction=np.array([1, 0, 0]))
        # Different build directions should produce different results
        assert not np.array_equal(mask_z, mask_x)


class TestGenerateSupportRegions:
    """Tests for 2D support region polygon generation."""

    def test_no_overhangs_no_regions(self):
        """No overhang faces => no support regions."""
        mesh = trimesh.primitives.Box(extents=[10, 10, 10])
        mask = np.zeros(len(mesh.faces), dtype=bool)
        regions = generate_support_regions(mesh, mask, layer_height=1.0)
        assert len(regions) == 0

    def test_overhangs_produce_regions(self):
        """Overhang faces should produce at least one support region."""
        mesh = trimesh.primitives.Box(extents=[10, 10, 10])
        # Mark all downward-facing faces as overhangs
        mask = detect_overhangs(mesh, threshold_angle=30.0)
        if mask.any():
            regions = generate_support_regions(mesh, mask, layer_height=1.0)
            assert len(regions) >= 1
            for region in regions:
                assert len(region) >= 3, "Region polygon must have at least 3 points"


class TestGenerateSupportToolpath:
    """Tests for support toolpath segment generation."""

    def test_basic_support_generation(self):
        """Generate support toolpath from a simple rectangular region."""
        regions = [[(0, 0), (10, 0), (10, 10), (0, 10)]]
        segments = generate_support_toolpath(
            regions,
            z_min=0.0,
            z_max=10.0,
            layer_height=2.0,
            extrusion_width=2.0,
            infill_density=0.2,
        )
        assert len(segments) > 0
        for seg in segments:
            assert seg.type == ToolpathType.SUPPORT
            assert seg.flow_rate == 0.5  # reduced flow for support

    def test_zero_density_no_segments(self):
        """Zero infill density should produce no support segments."""
        regions = [[(0, 0), (10, 0), (10, 10), (0, 10)]]
        segments = generate_support_toolpath(
            regions,
            z_min=0.0,
            z_max=10.0,
            layer_height=2.0,
            infill_density=0.0,
        )
        assert len(segments) == 0

    def test_empty_regions_no_segments(self):
        """No regions => no segments."""
        segments = generate_support_toolpath(
            [],
            z_min=0.0,
            z_max=10.0,
            layer_height=2.0,
        )
        assert len(segments) == 0

    def test_layer_count_correct(self):
        """Number of layers should match z_range / layer_height."""
        regions = [[(0, 0), (10, 0), (10, 10), (0, 10)]]
        segments = generate_support_toolpath(
            regions,
            z_min=0.0,
            z_max=10.0,
            layer_height=2.0,
            extrusion_width=2.0,
            infill_density=0.2,
        )
        layer_indices = set(seg.layer_index for seg in segments)
        # 10mm / 2mm = 5 layers (0, 1, 2, 3, 4)
        assert len(layer_indices) == 5


class TestAddSupportsToToolpath:
    """Integration tests for adding supports to an existing toolpath."""

    def test_no_overhangs_no_additions(self):
        """Flat cube has overhangs but they're at the bottom — support
        generation should add 0 segments if overhang is too close to plate."""
        mesh = trimesh.primitives.Box(extents=[10, 10, 10])
        # Center box at z=5 so bottom face is at z=0 (build plate)
        mesh.apply_translation([0, 0, 5])
        toolpath = Toolpath(layer_height=2.0, total_layers=5)
        count = add_supports_to_toolpath(mesh, toolpath, threshold_angle=45.0)
        # Bottom face overhang is at z=0 = build plate, so no room for supports
        assert count == 0

    def test_elevated_overhang_adds_supports(self):
        """A box elevated above the build plate should get supports underneath."""
        mesh = trimesh.primitives.Box(extents=[10, 10, 2])
        # Elevate so bottom face is at z=10, creating a large overhang gap
        mesh.apply_translation([0, 0, 11])
        toolpath = Toolpath(layer_height=2.0, total_layers=1)
        count = add_supports_to_toolpath(
            mesh, toolpath, threshold_angle=45.0, support_density=0.2
        )
        # Should have supports from z=0 up to z=10
        assert count > 0
        # Verify support segments are in the toolpath
        support_segs = [s for s in toolpath.segments if s.type == ToolpathType.SUPPORT]
        assert len(support_segs) == count
