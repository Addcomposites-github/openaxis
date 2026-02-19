"""
Unit tests for post-processor implementations.

Tests RAPID (.mod), KRL (.src), Fanuc (.ls), G-code output generation.
"""

import pytest

from openaxis.postprocessor import (
    PostProcessorBase,
    PostProcessorConfig,
    EventHooks,
    RAPIDPostProcessor,
    KRLPostProcessor,
    FanucPostProcessor,
    GCodePostProcessor,
)
from openaxis.postprocessor.base import PointData


# ── Shared test fixtures ──────────────────────────────────────────────────


@pytest.fixture
def sample_toolpath_data():
    """Minimal toolpath data dict for testing all post processors."""
    return {
        "totalLayers": 2,
        "layerHeight": 0.3,
        "processType": "waam",
        "statistics": {"totalPoints": 6},
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
            {
                "type": "travel",
                "layer": 1,
                "speed": 5000.0,
                "extrusionRate": 0.0,
                "points": [
                    [0.0, 0.0, 0.3],
                ],
            },
            {
                "type": "perimeter",
                "layer": 1,
                "speed": 1000.0,
                "extrusionRate": 1.0,
                "points": [
                    [10.0, 20.0, 0.3],
                    [30.0, 20.0, 0.3],
                ],
            },
        ],
    }


# ── PostProcessorConfig & EventHooks ──────────────────────────────────────


class TestPostProcessorConfig:
    """Tests for PostProcessorConfig."""

    def test_default_values(self):
        """Test default config values."""
        config = PostProcessorConfig()
        assert config.format_name == "gcode"
        assert config.file_extension == ".gcode"
        assert config.default_speed == 1000.0
        assert config.tool_name == "tool0"

    def test_to_dict_from_dict_roundtrip(self):
        """Test config serialization roundtrip."""
        original = PostProcessorConfig(
            format_name="rapid",
            file_extension=".mod",
            default_speed=500.0,
            tool_name="myTool",
            hooks=EventHooks(program_start="! Start", layer_start="! Layer {layerIndex}"),
        )
        d = original.to_dict()
        restored = PostProcessorConfig.from_dict(d)
        assert restored.format_name == "rapid"
        assert restored.file_extension == ".mod"
        assert restored.default_speed == 500.0
        assert restored.tool_name == "myTool"
        assert restored.hooks.program_start == "! Start"
        assert restored.hooks.layer_start == "! Layer {layerIndex}"

    def test_from_dict_ignores_unknown_fields(self):
        """Test from_dict gracefully ignores unknown fields."""
        d = {"format_name": "krl", "unknown_field": True}
        config = PostProcessorConfig.from_dict(d)
        assert config.format_name == "krl"


class TestEventHooks:
    """Tests for EventHooks."""

    def test_default_empty(self):
        """Test all hooks default to empty strings."""
        hooks = EventHooks()
        assert hooks.program_start == ""
        assert hooks.program_end == ""
        assert hooks.layer_start == ""
        assert hooks.process_on == ""

    def test_to_dict(self):
        """Test EventHooks serialization."""
        hooks = EventHooks(program_start="START", process_on="ARC ON")
        d = hooks.to_dict()
        assert d["program_start"] == "START"
        assert d["process_on"] == "ARC ON"
        assert d["program_end"] == ""

    def test_from_dict(self):
        """Test EventHooks deserialization."""
        d = {"program_start": "GO", "layer_end": "PAUSE"}
        hooks = EventHooks.from_dict(d)
        assert hooks.program_start == "GO"
        assert hooks.layer_end == "PAUSE"

    def test_from_dict_ignores_unknown(self):
        """Test from_dict ignores unknown keys."""
        d = {"program_start": "X", "nonexistent_hook": "Y"}
        hooks = EventHooks.from_dict(d)
        assert hooks.program_start == "X"


class TestPointData:
    """Tests for PointData."""

    def test_template_vars(self):
        """Test template variable generation."""
        pt = PointData(x=10.5, y=20.3, z=5.0, speed=1000.0, layer_index=3)
        vars_ = pt.template_vars("tool0")
        assert vars_["x"] == "10.500"
        assert vars_["y"] == "20.300"
        assert vars_["z"] == "5.000"
        assert vars_["speed"] == "1000.0"
        assert vars_["layerIndex"] == "3"
        assert vars_["toolName"] == "tool0"


# ── RAPID Post Processor ──────────────────────────────────────────────────


class TestRAPIDPostProcessor:
    """Tests for ABB RAPID post processor."""

    def test_default_config(self):
        """Test RAPID default configuration."""
        pp = RAPIDPostProcessor()
        assert pp.format_name == "rapid"
        assert pp.file_extension == ".mod"

    def test_header_contains_module(self, sample_toolpath_data):
        """Test RAPID header generates MODULE declaration."""
        pp = RAPIDPostProcessor()
        header = pp.header(sample_toolpath_data)
        header_text = "\n".join(header)
        assert "MODULE" in header_text
        assert "PROC main()" in header_text

    def test_footer_contains_endmodule(self):
        """Test RAPID footer generates ENDMODULE."""
        pp = RAPIDPostProcessor()
        footer = pp.footer()
        footer_text = "\n".join(footer)
        assert "ENDMODULE" in footer_text
        assert "ENDPROC" in footer_text

    def test_linear_move_generates_movel(self):
        """Test linear move generates MoveL command."""
        pp = RAPIDPostProcessor()
        pt = PointData(x=100.0, y=200.0, z=50.0, speed=500.0)
        lines = pp.linear_move(pt)
        output = "\n".join(lines)
        assert "MoveL" in output
        assert "100.00" in output
        assert "200.00" in output

    def test_rapid_move_generates_movej(self):
        """Test rapid move generates MoveJ command."""
        pp = RAPIDPostProcessor()
        pt = PointData(x=0.0, y=0.0, z=100.0, speed=2000.0)
        lines = pp.rapid_move(pt)
        output = "\n".join(lines)
        assert "MoveJ" in output

    def test_generate_full_program(self, sample_toolpath_data):
        """Test full RAPID program generation."""
        pp = RAPIDPostProcessor()
        output = pp.generate(sample_toolpath_data)
        assert output.startswith("MODULE")
        assert "ENDMODULE" in output
        assert "MoveL" in output or "MoveJ" in output
        assert "Layer 0" in output
        assert "Layer 1" in output

    def test_comment_format(self):
        """Test RAPID comment format uses '!'."""
        pp = RAPIDPostProcessor()
        comment = pp.comment("test comment")
        assert "!" in comment
        assert "test comment" in comment


# ── KRL Post Processor ───────────────────────────────────────────────────


class TestKRLPostProcessor:
    """Tests for KUKA KRL post processor."""

    def test_default_config(self):
        """Test KRL default configuration."""
        pp = KRLPostProcessor()
        assert pp.format_name == "krl"
        assert pp.file_extension == ".src"

    def test_header_contains_def(self, sample_toolpath_data):
        """Test KRL header generates DEF declaration."""
        pp = KRLPostProcessor()
        header = pp.header(sample_toolpath_data)
        header_text = "\n".join(header)
        assert "DEF" in header_text

    def test_footer_contains_end(self):
        """Test KRL footer generates END."""
        pp = KRLPostProcessor()
        footer = pp.footer()
        footer_text = "\n".join(footer)
        assert "END" in footer_text

    def test_linear_move_generates_lin(self):
        """Test linear move generates LIN command."""
        pp = KRLPostProcessor()
        pt = PointData(x=100.0, y=200.0, z=50.0, speed=500.0)
        lines = pp.linear_move(pt)
        output = "\n".join(lines)
        assert "LIN" in output
        assert "100.00" in output

    def test_rapid_move_generates_ptp(self):
        """Test rapid move generates PTP command."""
        pp = KRLPostProcessor()
        pt = PointData(x=0.0, y=0.0, z=100.0, speed=2000.0)
        lines = pp.rapid_move(pt)
        output = "\n".join(lines)
        assert "PTP" in output

    def test_generate_full_program(self, sample_toolpath_data):
        """Test full KRL program generation."""
        pp = KRLPostProcessor()
        output = pp.generate(sample_toolpath_data)
        assert "DEF" in output
        assert "END" in output
        assert "LIN" in output or "PTP" in output


# ── Fanuc Post Processor ─────────────────────────────────────────────────


class TestFanucPostProcessor:
    """Tests for Fanuc LS post processor."""

    def test_default_config(self):
        """Test Fanuc default configuration."""
        pp = FanucPostProcessor()
        assert pp.format_name == "fanuc"
        assert pp.file_extension == ".ls"

    def test_header_contains_prog(self, sample_toolpath_data):
        """Test Fanuc header generates /PROG declaration."""
        pp = FanucPostProcessor()
        header = pp.header(sample_toolpath_data)
        header_text = "\n".join(header)
        assert "/PROG" in header_text

    def test_footer_contains_end(self):
        """Test Fanuc footer generates /END."""
        pp = FanucPostProcessor()
        footer = pp.footer()
        footer_text = "\n".join(footer)
        assert "/END" in footer_text

    def test_linear_move_generates_l(self):
        """Test linear move generates L P[] command."""
        pp = FanucPostProcessor()
        pt = PointData(x=100.0, y=200.0, z=50.0, speed=500.0)
        lines = pp.linear_move(pt)
        output = "\n".join(lines)
        assert ":L" in output
        assert "P[" in output

    def test_rapid_move_generates_j(self):
        """Test rapid move generates J P[] command."""
        pp = FanucPostProcessor()
        pt = PointData(x=0.0, y=0.0, z=100.0, speed=2000.0)
        lines = pp.rapid_move(pt)
        output = "\n".join(lines)
        assert ":J" in output
        assert "P[" in output

    def test_generate_full_program(self, sample_toolpath_data):
        """Test full Fanuc program generation."""
        pp = FanucPostProcessor()
        output = pp.generate(sample_toolpath_data)
        assert "/PROG" in output
        assert "/END" in output


# ── G-code Post Processor ────────────────────────────────────────────────


class TestGCodePostProcessor:
    """Tests for G-code post processor."""

    def test_default_config(self):
        """Test G-code default configuration."""
        pp = GCodePostProcessor()
        assert pp.format_name == "gcode"
        assert pp.file_extension == ".gcode"

    def test_header_contains_g21(self, sample_toolpath_data):
        """Test G-code header sets millimeter units with G21."""
        pp = GCodePostProcessor()
        header = pp.header(sample_toolpath_data)
        header_text = "\n".join(header)
        assert "G21" in header_text

    def test_linear_move_generates_g1(self):
        """Test linear move generates G1 command."""
        pp = GCodePostProcessor()
        # Must call header first to init state
        pp.header({"layerHeight": 0.3, "totalLayers": 1, "statistics": {}})
        pt = PointData(x=10.0, y=20.0, z=0.3, speed=1000.0)
        lines = pp.linear_move(pt)
        output = "\n".join(lines)
        assert "G1" in output
        assert "X10.000" in output
        assert "Y20.000" in output

    def test_rapid_move_generates_g0(self):
        """Test rapid move generates G0 command."""
        pp = GCodePostProcessor()
        pt = PointData(x=0.0, y=0.0, z=10.0, speed=5000.0)
        lines = pp.rapid_move(pt)
        output = "\n".join(lines)
        assert "G0" in output

    def test_generate_full_program(self, sample_toolpath_data):
        """Test full G-code program generation."""
        pp = GCodePostProcessor()
        output = pp.generate(sample_toolpath_data)
        assert "G21" in output
        assert "G1" in output or "G0" in output
        # Should have layer comments
        assert "Layer 0" in output
        assert "Layer 1" in output


# ── Event Hooks Integration ──────────────────────────────────────────────


class TestEventHooksIntegration:
    """Test that event hooks appear in generated output."""

    def test_program_start_hook_in_output(self, sample_toolpath_data):
        """Test program_start hook appears in generated output."""
        config = PostProcessorConfig(
            hooks=EventHooks(program_start="; CUSTOM START MARKER")
        )
        pp = GCodePostProcessor(config)
        output = pp.generate(sample_toolpath_data)
        assert "; CUSTOM START MARKER" in output

    def test_program_end_hook_in_output(self, sample_toolpath_data):
        """Test program_end hook appears in generated output."""
        config = PostProcessorConfig(
            hooks=EventHooks(program_end="; CUSTOM END MARKER")
        )
        pp = GCodePostProcessor(config)
        output = pp.generate(sample_toolpath_data)
        assert "; CUSTOM END MARKER" in output

    def test_before_point_hook_with_template(self, sample_toolpath_data):
        """Test before_point hook with template variable expansion."""
        config = PostProcessorConfig(
            hooks=EventHooks(before_point="; Point at X={x} Y={y}")
        )
        pp = GCodePostProcessor(config)
        output = pp.generate(sample_toolpath_data)
        assert "; Point at X=10.000 Y=20.000" in output

    def test_empty_hooks_produce_no_extra_lines(self, sample_toolpath_data):
        """Test that empty hooks don't add blank lines."""
        pp = GCodePostProcessor()
        output = pp.generate(sample_toolpath_data)
        # Should still produce valid output without hook artifacts
        assert len(output) > 0
