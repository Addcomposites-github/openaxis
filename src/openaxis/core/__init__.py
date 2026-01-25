"""
Core module - Shared utilities, configuration, and base classes.
"""

from openaxis.core.config import ConfigManager
from openaxis.core.exceptions import (
    OpenAxisError,
    ConfigurationError,
    HardwareError,
    GeometryError,
    RobotError,
)
from openaxis.core.geometry import (
    GeometryConverter,
    GeometryLoader,
    BoundingBox,
    TransformationUtilities,
)
from openaxis.core.plugin import Plugin, PluginRegistry
from openaxis.core.project import Project
from openaxis.core.robot import RobotLoader, RobotInstance, KinematicsEngine

__all__ = [
    # Config
    "ConfigManager",
    # Exceptions
    "OpenAxisError",
    "ConfigurationError",
    "HardwareError",
    "GeometryError",
    "RobotError",
    # Geometry
    "GeometryConverter",
    "GeometryLoader",
    "BoundingBox",
    "TransformationUtilities",
    # Plugin
    "Plugin",
    "PluginRegistry",
    # Project
    "Project",
    # Robot
    "RobotLoader",
    "RobotInstance",
    "KinematicsEngine",
]
