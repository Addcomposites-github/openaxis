"""
Motion module - Robot kinematics and motion planning.

This module provides:
- IK solving via compas_fab PyBulletClient backend
- Motion planning (Cartesian and joint-space path generation)
- Collision detection (PyBullet-based — working)
- External axes data structures (compute methods raise NotImplementedError)

NOTE: Custom IK solvers and trajectory optimization were deleted (critical
bugs in ungrounded implementations). See docs/UNGROUNDED_CODE.md.
IK now uses compas_fab's PyBulletClient (damped least-squares IK).
"""

from openaxis.motion.collision import CollisionChecker
from openaxis.motion.external_axes import (
    ExternalAxesController,
    ExternalAxisType,
    PositionerConfig,
    create_linear_track,
    create_turntable,
)
from openaxis.motion.kinematics import IKSolver
from openaxis.motion.planner import (
    CartesianPlanner,
    JointPlanner,
    TrajectoryOptimizer,
)

__all__ = [
    "IKSolver",
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
