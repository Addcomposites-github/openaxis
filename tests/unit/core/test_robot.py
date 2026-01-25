"""
Tests for robot module.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from compas.geometry import Frame
from compas_robots import RobotModel

from openaxis.core.config import RobotConfig
from openaxis.core.exceptions import RobotError
from openaxis.core.robot import KinematicsEngine, RobotInstance, RobotLoader


@pytest.fixture
def mock_robot_config():
    """Create a mock robot configuration."""
    return RobotConfig(
        name="test_robot",
        manufacturer="Test Corp",
        type="industrial_arm",
        urdf_path="/fake/path/robot.urdf",
        base_frame="base_link",
        tool_frame="tool0",
        joint_limits={
            "joint_1": {"min": -3.14, "max": 3.14},
            "joint_2": {"min": -1.57, "max": 1.57},
        },
    )


@pytest.fixture
def mock_robot_model():
    """Create a mock RobotModel."""
    model = MagicMock(spec=RobotModel)

    # Mock joints
    joint1 = MagicMock()
    joint1.name = "joint_1"
    joint1.is_configurable.return_value = True
    joint1.limit = MagicMock()
    joint1.limit.lower = -3.0
    joint1.limit.upper = 3.0

    joint2 = MagicMock()
    joint2.name = "joint_2"
    joint2.is_configurable.return_value = True
    joint2.limit = MagicMock()
    joint2.limit.lower = -1.5
    joint2.limit.upper = 1.5

    fixed_joint = MagicMock()
    fixed_joint.name = "fixed_joint"
    fixed_joint.is_configurable.return_value = False

    model.joints = [joint1, joint2, fixed_joint]

    # Mock links
    link1 = MagicMock()
    link1.name = "base_link"
    link2 = MagicMock()
    link2.name = "link1"
    link3 = MagicMock()
    link3.name = "tool0"

    model.links = [link1, link2, link3]

    return model


class TestRobotLoader:
    """Tests for RobotLoader."""

    def test_load_nonexistent_urdf(self):
        """Test loading non-existent URDF raises error."""
        with pytest.raises(RobotError, match="URDF file not found"):
            RobotLoader.load_from_urdf("/nonexistent/path/robot.urdf")

    @patch("openaxis.core.robot.RobotModel.from_urdf_file")
    def test_load_from_urdf(self, mock_from_urdf, tmp_path, mock_robot_model):
        """Test loading robot from URDF."""
        # Create a dummy URDF file
        urdf_file = tmp_path / "robot.urdf"
        urdf_file.write_text("<robot></robot>")

        # Mock the from_urdf_file method
        mock_from_urdf.return_value = mock_robot_model

        model = RobotLoader.load_from_urdf(urdf_file)

        assert model is not None
        mock_from_urdf.assert_called_once()

    def test_load_from_config_no_urdf(self):
        """Test loading from config without URDF path raises error."""
        config = RobotConfig(
            name="test_robot",
            manufacturer="Test Corp",
            urdf_path=None,  # No URDF path
        )

        with pytest.raises(RobotError, match="has no URDF path"):
            RobotLoader.load_from_config(config)

    @patch("openaxis.core.robot.RobotLoader.load_from_urdf")
    def test_load_from_config(self, mock_load_urdf, mock_robot_config, mock_robot_model):
        """Test loading robot from configuration."""
        mock_load_urdf.return_value = mock_robot_model

        robot = RobotLoader.load_from_config(mock_robot_config)

        assert isinstance(robot, RobotInstance)
        assert robot.name == "test_robot"
        assert robot.manufacturer == "Test Corp"
        mock_load_urdf.assert_called_once()


class TestRobotInstance:
    """Tests for RobotInstance."""

    def test_initialization(self, mock_robot_model, mock_robot_config):
        """Test robot instance initialization."""
        robot = RobotInstance(model=mock_robot_model, config=mock_robot_config)

        assert robot.model is mock_robot_model
        assert robot.config is mock_robot_config
        assert robot.name == "test_robot"
        assert robot.manufacturer == "Test Corp"

    def test_properties(self, mock_robot_model, mock_robot_config):
        """Test robot instance properties."""
        robot = RobotInstance(model=mock_robot_model, config=mock_robot_config)

        assert robot.base_frame == "base_link"
        assert robot.tool_frame == "tool0"

    def test_get_joint_names(self, mock_robot_model, mock_robot_config):
        """Test getting joint names."""
        robot = RobotInstance(model=mock_robot_model, config=mock_robot_config)

        joint_names = robot.get_joint_names()

        assert len(joint_names) == 2  # Only configurable joints
        assert "joint_1" in joint_names
        assert "joint_2" in joint_names
        assert "fixed_joint" not in joint_names

    def test_get_link_names(self, mock_robot_model, mock_robot_config):
        """Test getting link names."""
        robot = RobotInstance(model=mock_robot_model, config=mock_robot_config)

        link_names = robot.get_link_names()

        assert len(link_names) == 3
        assert "base_link" in link_names
        assert "link1" in link_names
        assert "tool0" in link_names

    def test_get_joint_limits_from_urdf(self, mock_robot_model, mock_robot_config):
        """Test getting joint limits from URDF."""
        # Config without overrides
        config = RobotConfig(
            name="test",
            manufacturer="Test",
            urdf_path="/fake/path.urdf",
        )

        robot = RobotInstance(model=mock_robot_model, config=config)
        limits = robot.get_joint_limits()

        assert "joint_1" in limits
        assert "joint_2" in limits
        assert limits["joint_1"] == (-3.0, 3.0)
        assert limits["joint_2"] == (-1.5, 1.5)

    def test_get_joint_limits_with_config_override(
        self, mock_robot_model, mock_robot_config
    ):
        """Test joint limits override from config."""
        robot = RobotInstance(model=mock_robot_model, config=mock_robot_config)
        limits = robot.get_joint_limits()

        # Config should override URDF limits
        assert limits["joint_1"] == (-3.14, 3.14)
        assert limits["joint_2"] == (-1.57, 1.57)

    def test_validate_configuration_valid(self, mock_robot_model, mock_robot_config):
        """Test validation of valid joint configuration."""
        robot = RobotInstance(model=mock_robot_model, config=mock_robot_config)

        # Valid configuration
        assert robot.validate_configuration([0.0, 0.0]) is True
        assert robot.validate_configuration([1.0, 0.5]) is True

    def test_validate_configuration_out_of_limits(
        self, mock_robot_model, mock_robot_config
    ):
        """Test validation of configuration out of limits."""
        robot = RobotInstance(model=mock_robot_model, config=mock_robot_config)

        # Out of limits
        assert robot.validate_configuration([4.0, 0.0]) is False  # joint_1 too high
        assert robot.validate_configuration([0.0, 2.0]) is False  # joint_2 too high

    def test_validate_configuration_wrong_size(
        self, mock_robot_model, mock_robot_config
    ):
        """Test validation with wrong number of joints."""
        robot = RobotInstance(model=mock_robot_model, config=mock_robot_config)

        # Wrong number of joints
        assert robot.validate_configuration([0.0]) is False  # Too few
        assert robot.validate_configuration([0.0, 0.0, 0.0]) is False  # Too many

    def test_repr(self, mock_robot_model, mock_robot_config):
        """Test string representation."""
        robot = RobotInstance(model=mock_robot_model, config=mock_robot_config)

        repr_str = repr(robot)

        assert "test_robot" in repr_str
        assert "Test Corp" in repr_str
        assert "joints=2" in repr_str


class TestKinematicsEngine:
    """Tests for KinematicsEngine."""

    def test_initialization(self, mock_robot_model, mock_robot_config):
        """Test kinematics engine initialization."""
        robot = RobotInstance(model=mock_robot_model, config=mock_robot_config)
        engine = KinematicsEngine(robot)

        assert engine.robot is robot

    def test_forward_kinematics_invalid_config(
        self, mock_robot_model, mock_robot_config
    ):
        """Test FK with invalid configuration raises error."""
        robot = RobotInstance(model=mock_robot_model, config=mock_robot_config)
        engine = KinematicsEngine(robot)

        # Configuration out of limits
        with pytest.raises(RobotError, match="Invalid joint configuration"):
            engine.forward_kinematics([10.0, 10.0])

    @patch("compas_robots.Configuration")
    def test_forward_kinematics_valid(
        self, mock_config_class, mock_robot_model, mock_robot_config
    ):
        """Test FK with valid configuration."""
        robot = RobotInstance(model=mock_robot_model, config=mock_robot_config)

        # Mock the robot's forward_kinematics method
        mock_frame = Frame.worldXY()
        robot._robot = MagicMock()
        robot._robot.forward_kinematics.return_value = mock_frame

        engine = KinematicsEngine(robot)

        # Valid configuration
        frame = engine.forward_kinematics([0.0, 0.0])

        assert isinstance(frame, Frame)
        robot._robot.forward_kinematics.assert_called_once()

    def test_inverse_kinematics_not_implemented(
        self, mock_robot_model, mock_robot_config
    ):
        """Test that IK raises NotImplementedError (Phase 2 feature)."""
        robot = RobotInstance(model=mock_robot_model, config=mock_robot_config)
        engine = KinematicsEngine(robot)

        target_frame = Frame.worldXY()

        with pytest.raises(NotImplementedError, match="motion planning backend"):
            engine.inverse_kinematics(target_frame)

    def test_check_collision_not_implemented(
        self, mock_robot_model, mock_robot_config
    ):
        """Test that collision checking raises NotImplementedError (Phase 2 feature)."""
        robot = RobotInstance(model=mock_robot_model, config=mock_robot_config)
        engine = KinematicsEngine(robot)

        with pytest.raises(NotImplementedError, match="backend integration"):
            engine.check_collision([0.0, 0.0])
