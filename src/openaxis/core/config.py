"""
Configuration management for OpenAxis.

Handles loading, validation, and access to robot and process configurations.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from openaxis.core.exceptions import ConfigurationError


class RobotConfig(BaseModel):
    """Robot configuration model."""

    name: str
    manufacturer: str
    type: str = "industrial_arm"
    urdf_path: str | None = None
    base_frame: str = "base_link"
    tool_frame: str = "tool0"
    joint_limits: dict[str, dict[str, float]] = Field(default_factory=dict)
    communication: dict[str, Any] = Field(default_factory=dict)


class ProcessConfig(BaseModel):
    """Manufacturing process configuration model."""

    name: str
    type: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    slicing: dict[str, Any] = Field(default_factory=dict)
    equipment: dict[str, Any] = Field(default_factory=dict)


@dataclass
class ConfigManager:
    """
    Central configuration manager for OpenAxis.

    Loads and validates configurations from YAML files.
    Supports hierarchical configuration with defaults and overrides.

    Example:
        >>> config = ConfigManager(config_dir=Path("config"))
        >>> robot = config.get_robot("abb_irb6700")
        >>> process = config.get_process("waam_steel")
    """

    config_dir: Path
    _robots: dict[str, RobotConfig] = field(default_factory=dict, init=False)
    _processes: dict[str, ProcessConfig] = field(default_factory=dict, init=False)
    _loaded: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        """Initialize configuration manager."""
        self.config_dir = Path(self.config_dir)
        if not self.config_dir.exists():
            raise ConfigurationError(
                f"Configuration directory not found: {self.config_dir}"
            )

    def load(self) -> None:
        """Load all configurations from disk."""
        self._load_robots()
        self._load_processes()
        self._loaded = True

    def _load_robots(self) -> None:
        """Load robot configurations."""
        robots_dir = self.config_dir / "robots"
        if not robots_dir.exists():
            return

        for config_file in robots_dir.glob("*.yaml"):
            try:
                with open(config_file) as f:
                    data = yaml.safe_load(f)

                if data and "robot" in data:
                    robot_data = data["robot"]
                    # Merge with other sections
                    if "kinematics" in data:
                        robot_data.update(data["kinematics"])
                    if "limits" in data:
                        robot_data["joint_limits"] = data["limits"].get("joints", {})
                    if "communication" in data:
                        robot_data["communication"] = data["communication"]

                    robot = RobotConfig(**robot_data)
                    self._robots[config_file.stem] = robot
            except (yaml.YAMLError, ValidationError) as e:
                raise ConfigurationError(
                    f"Failed to load robot config: {config_file}",
                    details={"error": str(e)},
                )

    def _load_processes(self) -> None:
        """Load process configurations."""
        processes_dir = self.config_dir / "processes"
        if not processes_dir.exists():
            return

        for config_file in processes_dir.glob("*.yaml"):
            try:
                with open(config_file) as f:
                    data = yaml.safe_load(f)

                if data and "process" in data:
                    process_data = data["process"]
                    if "parameters" in data:
                        process_data["parameters"] = data["parameters"]
                    if "slicing" in data:
                        process_data["slicing"] = data["slicing"]
                    if "equipment" in data:
                        process_data["equipment"] = data["equipment"]

                    process = ProcessConfig(**process_data)
                    self._processes[config_file.stem] = process
            except (yaml.YAMLError, ValidationError) as e:
                raise ConfigurationError(
                    f"Failed to load process config: {config_file}",
                    details={"error": str(e)},
                )

    def get_robot(self, name: str) -> RobotConfig:
        """
        Get robot configuration by name.

        Args:
            name: Robot configuration name (without .yaml extension)

        Returns:
            RobotConfig instance

        Raises:
            ConfigurationError: If robot not found
        """
        if not self._loaded:
            self.load()

        if name not in self._robots:
            available = list(self._robots.keys())
            raise ConfigurationError(
                f"Robot configuration not found: {name}",
                details={"available": available},
            )
        return self._robots[name]

    def get_process(self, name: str) -> ProcessConfig:
        """
        Get process configuration by name.

        Args:
            name: Process configuration name (without .yaml extension)

        Returns:
            ProcessConfig instance

        Raises:
            ConfigurationError: If process not found
        """
        if not self._loaded:
            self.load()

        if name not in self._processes:
            available = list(self._processes.keys())
            raise ConfigurationError(
                f"Process configuration not found: {name}",
                details={"available": available},
            )
        return self._processes[name]

    def list_robots(self) -> list[str]:
        """List available robot configurations."""
        if not self._loaded:
            self.load()
        return list(self._robots.keys())

    def list_processes(self) -> list[str]:
        """List available process configurations."""
        if not self._loaded:
            self.load()
        return list(self._processes.keys())
