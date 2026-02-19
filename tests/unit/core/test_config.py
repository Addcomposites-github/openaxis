"""
Unit tests for configuration management.
"""

import pytest

from openaxis.core.config import ConfigManager, ProcessConfig, RobotConfig, ToolConfig
from openaxis.core.exceptions import ConfigurationError


class TestRobotConfig:
    """Tests for RobotConfig model."""

    def test_create_minimal(self):
        """Test creating config with minimal fields."""
        config = RobotConfig(name="Test", manufacturer="Test Mfg")
        assert config.name == "Test"
        assert config.manufacturer == "Test Mfg"
        assert config.type == "industrial_arm"

    def test_create_full(self):
        """Test creating config with all fields."""
        config = RobotConfig(
            name="ABB IRB6700",
            manufacturer="ABB",
            type="industrial_arm",
            urdf_path="/path/to/urdf",
            base_frame="base",
            tool_frame="tool0",
            joint_limits={"j1": {"lower": -180, "upper": 180}},
            communication={"driver": "robot_raconteur", "ip": "192.168.1.100"},
        )
        assert config.name == "ABB IRB6700"
        assert config.joint_limits["j1"]["lower"] == -180

    def test_home_position_default_empty(self):
        """Test home_position defaults to empty list."""
        config = RobotConfig(name="Test", manufacturer="Mfg")
        assert config.home_position == []

    def test_home_position_set(self):
        """Test home_position can be set."""
        home = [0.0, -0.5, 0.5, 0.0, -0.5, 0.0]
        config = RobotConfig(
            name="Test", manufacturer="Mfg", home_position=home
        )
        assert config.home_position == home
        assert len(config.home_position) == 6


class TestProcessConfig:
    """Tests for ProcessConfig model."""

    def test_create_minimal(self):
        """Test creating config with minimal fields."""
        config = ProcessConfig(name="WAAM Steel", type="waam")
        assert config.name == "WAAM Steel"
        assert config.type == "waam"

    def test_create_with_parameters(self):
        """Test creating config with process parameters."""
        config = ProcessConfig(
            name="WAAM Steel",
            type="waam",
            parameters={"wire_feed_rate": 8.0, "voltage": 22.0},
            slicing={"layer_height": 2.5},
        )
        assert config.parameters["wire_feed_rate"] == 8.0
        assert config.slicing["layer_height"] == 2.5


class TestConfigManager:
    """Tests for ConfigManager."""

    def test_init_with_valid_dir(self, sample_config_dir):
        """Test initialization with valid directory."""
        manager = ConfigManager(sample_config_dir)
        assert manager.config_dir == sample_config_dir

    def test_init_with_invalid_dir(self, temp_dir):
        """Test initialization with non-existent directory."""
        with pytest.raises(ConfigurationError):
            ConfigManager(temp_dir / "nonexistent")

    def test_load_robots(self, sample_config_dir):
        """Test loading robot configurations."""
        manager = ConfigManager(sample_config_dir)
        manager.load()

        robots = manager.list_robots()
        assert "test_robot" in robots

    def test_get_robot(self, sample_config_dir):
        """Test getting a specific robot configuration."""
        manager = ConfigManager(sample_config_dir)

        robot = manager.get_robot("test_robot")
        assert robot.name == "Test Robot"
        assert robot.manufacturer == "Test Manufacturer"

    def test_get_robot_not_found(self, sample_config_dir):
        """Test getting a non-existent robot."""
        manager = ConfigManager(sample_config_dir)

        with pytest.raises(ConfigurationError) as exc_info:
            manager.get_robot("nonexistent")

        assert "available" in exc_info.value.details

    def test_load_processes(self, sample_config_dir):
        """Test loading process configurations."""
        manager = ConfigManager(sample_config_dir)
        manager.load()

        processes = manager.list_processes()
        assert "test_waam" in processes

    def test_get_process(self, sample_config_dir):
        """Test getting a specific process configuration."""
        manager = ConfigManager(sample_config_dir)

        process = manager.get_process("test_waam")
        assert process.name == "Test Process"
        assert process.type == "waam"
        assert process.parameters["wire_feed_rate"] == 8.0

    def test_get_process_not_found(self, sample_config_dir):
        """Test getting a non-existent process."""
        manager = ConfigManager(sample_config_dir)

        with pytest.raises(ConfigurationError):
            manager.get_process("nonexistent")

    def test_home_position_loaded_from_yaml(self, sample_config_dir):
        """Test home_position is loaded from robot YAML config."""
        manager = ConfigManager(sample_config_dir)
        robot = manager.get_robot("test_robot")
        assert robot.home_position == [0.0, -0.5, 0.5, 0.0, -0.5, 0.0]

    def test_load_tools(self, sample_config_dir):
        """Test loading tool configurations."""
        manager = ConfigManager(sample_config_dir)
        manager.load()
        tools = manager.list_tools()
        assert "test_mill" in tools

    def test_get_tool(self, sample_config_dir):
        """Test getting a specific tool configuration."""
        manager = ConfigManager(sample_config_dir)
        tool = manager.get_tool("test_mill")
        assert tool.name == "Test Milling Tool"
        assert tool.type == "milling"
        assert tool.mass == 2.0
        assert tool.properties["diameter"] == 6.0
        assert tool.properties["rotation_speed"] == 10000

    def test_get_tool_not_found(self, sample_config_dir):
        """Test getting a non-existent tool."""
        manager = ConfigManager(sample_config_dir)
        with pytest.raises(ConfigurationError) as exc_info:
            manager.get_tool("nonexistent")
        assert "available" in exc_info.value.details


class TestToolConfig:
    """Tests for ToolConfig model."""

    def test_create_minimal(self):
        """Test creating tool config with minimal fields."""
        config = ToolConfig(name="Test Tool", type="milling")
        assert config.name == "Test Tool"
        assert config.type == "milling"
        assert config.mass == 1.0
        assert config.tcp_offset == [0, 0, 0, 0, 0, 0]
        assert config.properties == {}

    def test_create_full(self):
        """Test creating tool config with all fields."""
        config = ToolConfig(
            name="WAAM Torch",
            type="extruder",
            urdf_path="urdf/tools/extruder.urdf",
            tcp_offset=[0, 0, 0.15, 0, 0, 0],
            mass=5.0,
            description="Wire arc torch",
            properties={"material_type": "steel", "wire_diameter": 1.2},
        )
        assert config.name == "WAAM Torch"
        assert config.type == "extruder"
        assert config.urdf_path == "urdf/tools/extruder.urdf"
        assert config.tcp_offset[2] == 0.15
        assert config.mass == 5.0
        assert config.properties["wire_diameter"] == 1.2

    def test_default_tcp_offset(self):
        """Test tcp_offset defaults to all zeros."""
        config = ToolConfig(name="T", type="milling")
        assert config.tcp_offset == [0, 0, 0, 0, 0, 0]
        assert len(config.tcp_offset) == 6
