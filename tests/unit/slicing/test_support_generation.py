"""
Tests for support generation module.

All custom support generation code has been deleted (was ungrounded custom code).
These tests verify that the functions raise NotImplementedError with clear
messages pointing to compas_slicer as the replacement.

The previous implementation used custom overhang detection and support region
generation without research citations. See docs/UNGROUNDED_CODE.md.
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
    """Tests for overhang face detection — currently raises NotImplementedError."""

    def test_raises_not_implemented(self):
        """detect_overhangs should raise NotImplementedError."""
        mesh = trimesh.primitives.Box(extents=[10, 10, 10])
        with pytest.raises(NotImplementedError, match="compas_slicer"):
            detect_overhangs(mesh, threshold_angle=45.0)


class TestGenerateSupportRegions:
    """Tests for support region generation — currently raises NotImplementedError."""

    def test_raises_not_implemented(self):
        """generate_support_regions should raise NotImplementedError."""
        mesh = trimesh.primitives.Box(extents=[10, 10, 10])
        mask = np.zeros(len(mesh.faces), dtype=bool)
        with pytest.raises(NotImplementedError, match="compas_slicer"):
            generate_support_regions(mesh, mask)


class TestGenerateSupportToolpath:
    """Tests for support toolpath generation — currently raises NotImplementedError."""

    def test_raises_not_implemented(self):
        """generate_support_toolpath should raise NotImplementedError."""
        regions = [[(0, 0), (10, 0), (10, 10), (0, 10)]]
        with pytest.raises(NotImplementedError, match="compas_slicer"):
            generate_support_toolpath(regions)


class TestAddSupportsToToolpath:
    """Tests for adding supports — currently raises NotImplementedError."""

    def test_raises_not_implemented(self):
        """add_supports_to_toolpath should raise NotImplementedError."""
        mesh = trimesh.primitives.Box(extents=[10, 10, 10])
        toolpath = Toolpath(layer_height=2.0, total_layers=5)
        with pytest.raises(NotImplementedError, match="compas_slicer"):
            add_supports_to_toolpath(mesh, toolpath, threshold_angle=45.0)
