"""
Integration tests for pybullet_industrial manufacturing simulation.

Tests tool creation, robot-tool coupling, and basic simulation
using pybullet_industrial's Extruder and MillingTool classes.

Library under test: pybullet_industrial v1.0.4
"""

import os
from pathlib import Path

import numpy as np
import pytest

try:
    import pybullet_industrial as pbi

    PBI_AVAILABLE = True
except ImportError:
    PBI_AVAILABLE = False

from openaxis.simulation.environment import SimulationEnvironment, SimulationMode

PROJECT_ROOT = Path(__file__).parent.parent.parent
ROBOT_URDF = str(PROJECT_ROOT / "config" / "urdf" / "abb_irb6700.urdf")
EXTRUDER_URDF = str(PROJECT_ROOT / "config" / "urdf" / "tools" / "extruder.urdf")
MILLING_URDF = str(PROJECT_ROOT / "config" / "urdf" / "tools" / "milling_tool.urdf")

pytestmark = pytest.mark.skipif(
    not PBI_AVAILABLE, reason="pybullet_industrial not installed"
)


@pytest.fixture
def sim_env():
    """Create a simulation environment in DIRECT mode."""
    env = SimulationEnvironment(mode=SimulationMode.DIRECT)
    env.start()
    yield env
    env.stop()


class TestPybulletIndustrialAvailability:
    """Test pybullet_industrial availability checks."""

    def test_is_available(self):
        """pybullet_industrial should be detected as available."""
        assert SimulationEnvironment.is_pybullet_industrial_available()


class TestRobotBase:
    """Test pbi.RobotBase creation from our URDF."""

    def test_create_robot_base(self, sim_env):
        """Create a RobotBase from the ABB IRB 6700 URDF."""
        robot = sim_env.create_robot_base(
            ROBOT_URDF, end_effector_link="link_6"
        )
        assert robot is not None
        assert isinstance(robot, pbi.RobotBase)

    def test_robot_base_with_position(self, sim_env):
        """RobotBase should accept custom position."""
        robot = sim_env.create_robot_base(
            ROBOT_URDF,
            position=(1.0, 2.0, 0.0),
            end_effector_link="link_6",
        )
        assert robot is not None


class TestExtruder:
    """Test pbi.Extruder creation and coupling."""

    def test_create_extruder(self, sim_env):
        """Create an Extruder tool from our tool URDF."""
        tool = sim_env.create_manufacturing_tool(
            tool_type="extruder",
            tool_urdf_path=EXTRUDER_URDF,
        )
        assert tool is not None
        assert isinstance(tool, pbi.Extruder)

    def test_create_extruder_with_properties(self, sim_env):
        """Create an Extruder with custom material properties."""
        tool = sim_env.create_manufacturing_tool(
            tool_type="extruder",
            tool_urdf_path=EXTRUDER_URDF,
            properties={
                "material": pbi.Plastic,
                "material properties": {
                    "particle size": 0.05,
                    "color": [1, 0, 0, 1],
                },
            },
        )
        assert tool is not None

    def test_extruder_couple_decouple(self, sim_env):
        """Test coupling/decoupling Extruder to robot."""
        robot = sim_env.create_robot_base(
            ROBOT_URDF, end_effector_link="link_6"
        )
        tool = sim_env.create_manufacturing_tool(
            tool_type="extruder",
            tool_urdf_path=EXTRUDER_URDF,
        )

        # Couple
        sim_env.couple_tool(tool, robot, end_effector_link="link_6")
        assert tool.is_coupled()

        # Decouple
        sim_env.decouple_tool(tool)
        assert not tool.is_coupled()

    def test_extruder_couple_at_creation(self, sim_env):
        """Test creating Extruder pre-coupled to robot."""
        robot = sim_env.create_robot_base(
            ROBOT_URDF, end_effector_link="link_6"
        )
        tool = sim_env.create_manufacturing_tool(
            tool_type="extruder",
            tool_urdf_path=EXTRUDER_URDF,
            coupled_robot=robot,
            end_effector_link="link_6",
        )
        assert tool.is_coupled()


class TestMillingTool:
    """Test pbi.MillingTool creation and coupling."""

    def test_create_milling_tool(self, sim_env):
        """Create a MillingTool from our tool URDF."""
        tool = sim_env.create_manufacturing_tool(
            tool_type="milling",
            tool_urdf_path=MILLING_URDF,
        )
        assert tool is not None
        assert isinstance(tool, pbi.MillingTool)

    def test_milling_tool_with_properties(self, sim_env):
        """Create MillingTool with custom cutting parameters."""
        tool = sim_env.create_manufacturing_tool(
            tool_type="milling",
            tool_urdf_path=MILLING_URDF,
            properties={
                "diameter": 10.0,
                "rotation speed": 15000,
                "number of teeth": 6,
            },
        )
        assert tool is not None

    def test_milling_tool_couple(self, sim_env):
        """Test coupling MillingTool to robot."""
        robot = sim_env.create_robot_base(
            ROBOT_URDF, end_effector_link="link_6"
        )
        tool = sim_env.create_manufacturing_tool(
            tool_type="milling",
            tool_urdf_path=MILLING_URDF,
            coupled_robot=robot,
            end_effector_link="link_6",
        )
        assert tool.is_coupled()


class TestToolTypeValidation:
    """Test tool type validation."""

    def test_invalid_tool_type(self, sim_env):
        """Unknown tool type should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown tool type"):
            sim_env.create_manufacturing_tool(
                tool_type="laser_welder",
                tool_urdf_path=EXTRUDER_URDF,
            )

    def test_not_running(self):
        """Creating tools before start() should raise RuntimeError."""
        env = SimulationEnvironment(mode=SimulationMode.DIRECT)
        with pytest.raises(RuntimeError, match="not running"):
            env.create_manufacturing_tool(
                tool_type="extruder",
                tool_urdf_path=EXTRUDER_URDF,
            )
