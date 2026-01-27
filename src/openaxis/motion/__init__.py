"""
Motion module - Robot kinematics and motion planning.

This module provides:
- Inverse kinematics solvers (numerical and Jacobian-based)
- Motion planning (Cartesian and joint-space)
- Collision detection (PyBullet-based)
- Trajectory optimization
- External axes support (positioners, linear tracks)
"""

from openaxis.motion.collision import CollisionChecker
from openaxis.motion.external_axes import (
    ExternalAxesController,
    ExternalAxisType,
    PositionerConfig,
    create_linear_track,
    create_turntable,
)
from openaxis.motion.kinematics import IKSolver, JacobianIKSolver
from openaxis.motion.planner import (
    CartesianPlanner,
    JointPlanner,
    TrajectoryOptimizer,
)

__all__ = [
    "IKSolver",
    "JacobianIKSolver",
    "CartesianPlanner",
    "JointPlanner",
    "TrajectoryOptimizer",
    "CollisionChecker",
    "ExternalAxesController",
    "ExternalAxisType",
    "PositionerConfig",
    "create_turntable",
    "create_linear_track",
]
