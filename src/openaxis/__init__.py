"""
OpenAxis - Open-Source Robotic Hybrid Manufacturing Platform

A unified software platform for robotic additive manufacturing (WAAM, pellet extrusion),
subtractive manufacturing (milling), and 3D scanning.
"""

__version__ = "0.1.0"
__author__ = "OpenAxis Contributors"

from openaxis.core.config import ConfigManager
from openaxis.core.project import Project

__all__ = [
    "__version__",
    "ConfigManager",
    "Project",
]
