"""
Unit tests for configuration management.
"""

import pytest

from openaxis.core.config import ConfigManager, ProcessConfig, RobotConfig
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
