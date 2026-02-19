"""
Unit tests for PostProcessorService.

Tests format listing, processor creation, and export functionality.
"""

import pytest

from openaxis.postprocessor import (
    PostProcessorConfig,
    EventHooks,
    RAPIDPostProcessor,
    KRLPostProcessor,
    FanucPostProcessor,
    GCodePostProcessor,
)

# Import the service (it's in src/backend/)
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "backend"))
from postprocessor_service import PostProcessorService, FORMAT_INFO


@pytest.fixture
def service():
    """Create a PostProcessorService instance."""
    return PostProcessorService()


@pytest.fixture
def sample_toolpath():
    """Minimal toolpath for export tests."""
    return {
        "totalLayers": 1,
        "layerHeight": 0.3,
        "processType": "test",
        "statistics": {"totalPoints": 3},
        "segments": [
            {
                "type": "perimeter",
                "layer": 0,
                "speed": 1000.0,
                "extrusionRate": 1.0,
                "points": [
                    [10.0, 20.0, 0.0],
                    [30.0, 20.0, 0.0],
                    [30.0, 40.0, 0.0],
                ],
            },
        ],
    }


class TestPostProcessorService:
    """Tests for PostProcessorService."""

    def test_get_available_formats_returns_four(self, service):
        """Test that all 4 formats are available."""
        formats = service.get_available_formats()
        assert len(formats) == 4
        format_ids = [f["id"] for f in formats]
        assert "gcode" in format_ids
        assert "rapid" in format_ids
        assert "krl" in format_ids
        assert "fanuc" in format_ids

    def test_format_info_has_required_keys(self, service):
        """Test each format entry has required metadata."""
        formats = service.get_available_formats()
        for fmt in formats:
            assert "id" in fmt
            assert "name" in fmt
            assert "extension" in fmt
            assert "vendor" in fmt
            assert "available" in fmt

    def test_create_gcode_processor(self, service):
        """Test creating a G-code processor."""
        pp = service.create_post_processor("gcode")
        assert pp is not None
        assert isinstance(pp, GCodePostProcessor)
        assert pp.file_extension == ".gcode"

    def test_create_rapid_processor(self, service):
        """Test creating a RAPID processor."""
        pp = service.create_post_processor("rapid")
        assert pp is not None
        assert isinstance(pp, RAPIDPostProcessor)

    def test_create_krl_processor(self, service):
        """Test creating a KRL processor."""
        pp = service.create_post_processor("krl")
        assert pp is not None
        assert isinstance(pp, KRLPostProcessor)

    def test_create_fanuc_processor(self, service):
        """Test creating a Fanuc processor."""
        pp = service.create_post_processor("fanuc")
        assert pp is not None
        assert isinstance(pp, FanucPostProcessor)

    def test_create_unknown_format_returns_none(self, service):
        """Test creating processor for unknown format returns None."""
        pp = service.create_post_processor("unknown_format")
        assert pp is None

    def test_export_gcode(self, service, sample_toolpath):
        """Test G-code export produces valid output."""
        result = service.export(sample_toolpath, "gcode")
        assert "error" not in result
        assert result["content"]
        assert result["extension"] == ".gcode"
        assert result["format"] == "gcode"
        assert result["lines"] > 0
        assert result["size"] > 0

    def test_export_rapid(self, service, sample_toolpath):
        """Test RAPID export produces MODULE/ENDMODULE content."""
        result = service.export(sample_toolpath, "rapid")
        assert "error" not in result
        assert result["format"] == "rapid"
        assert "MODULE" in result["content"]
        assert "ENDMODULE" in result["content"]

    def test_export_krl(self, service, sample_toolpath):
        """Test KRL export produces DEF/END content."""
        result = service.export(sample_toolpath, "krl")
        assert "error" not in result
        assert result["format"] == "krl"
        assert "DEF" in result["content"]
        assert "END" in result["content"]

    def test_export_fanuc(self, service, sample_toolpath):
        """Test Fanuc export produces /PROG and /END content."""
        result = service.export(sample_toolpath, "fanuc")
        assert "error" not in result
        assert result["format"] == "fanuc"
        assert "/PROG" in result["content"]
        assert "/END" in result["content"]

    def test_export_unknown_format_returns_error(self, service, sample_toolpath):
        """Test export with unknown format returns error."""
        result = service.export(sample_toolpath, "unknown")
        assert "error" in result

    def test_export_with_config_overrides(self, service, sample_toolpath):
        """Test export with custom config overrides."""
        result = service.export(
            sample_toolpath,
            "gcode",
            config_overrides={"program_name": "MyCustomProgram"},
        )
        assert "error" not in result
        assert result["content"]

    def test_get_default_config(self, service):
        """Test getting default config for a format."""
        config = service.get_default_config("rapid")
        assert isinstance(config, dict)
        assert "format_name" in config
        assert "hooks" in config
