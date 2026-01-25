"""
Pytest configuration and shared fixtures.
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_dir(temp_dir):
    """Create a sample configuration directory structure."""
    config_dir = temp_dir / "config"
    (config_dir / "robots").mkdir(parents=True)
    (config_dir / "processes").mkdir(parents=True)

    # Create sample robot config
    robot_config = """
robot:
  name: "Test Robot"
  manufacturer: "Test Manufacturer"
  type: "industrial_arm"

kinematics:
  base_frame: "base_link"
  tool_frame: "tool0"

limits:
  joints:
    joint_1:
      lower: -180
      upper: 180
"""
    (config_dir / "robots" / "test_robot.yaml").write_text(robot_config)

    # Create sample process config
    process_config = """
process:
  name: "Test Process"
  type: "waam"

parameters:
  wire_feed_rate: 8.0
  travel_speed: 10.0

slicing:
  layer_height: 2.5
  bead_width: 6.0
"""
    (config_dir / "processes" / "test_waam.yaml").write_text(process_config)

    return config_dir


@pytest.fixture
def sample_project(temp_dir):
    """Create a sample project."""
    from openaxis.core.project import Project

    project_dir = temp_dir / "test_project"
    project = Project.create(
        name="Test Project",
        path=project_dir,
        description="A test project",
        author="Test Author",
    )
    return project
