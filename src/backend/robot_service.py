"""
Robot service for OpenAxis backend.

Handles robot configuration, forward/inverse kinematics, and joint limits.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from openaxis.core.config import ConfigManager, RobotConfig
    from openaxis.core.robot import RobotLoader, RobotInstance
    from openaxis.motion.kinematics import IKSolver, JacobianIKSolver
    from compas.geometry import Frame, Point, Vector
    from compas_robots import Configuration
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Robot modules not available: {e}")
    CONFIG_AVAILABLE = False


class RobotService:
    """Service for robot configuration and kinematics operations."""

    def __init__(self, config_dir: Optional[str] = None):
        self._robot_instance: Optional[Any] = None
        self._ik_solver: Optional[Any] = None
        self._jacobian_solver: Optional[Any] = None
        self._config_manager: Optional[Any] = None

        if CONFIG_AVAILABLE and config_dir:
            try:
                self._config_manager = ConfigManager(config_dir=Path(config_dir))
                self._config_manager.load()
            except Exception as e:
                print(f"Warning: Failed to load config: {e}")

    def get_available_robots(self) -> List[str]:
        """List available robot configurations."""
        if self._config_manager:
            return self._config_manager.list_robots()
        return []

    def get_robot_config(self, robot_name: str = "abb_irb6700") -> Dict[str, Any]:
        """Get robot configuration data."""
        if not CONFIG_AVAILABLE or not self._config_manager:
            return self._default_robot_config()

        try:
            config = self._config_manager.get_robot(robot_name)
            return {
                "name": config.name,
                "manufacturer": config.manufacturer,
                "type": config.type,
                "baseFrame": config.base_frame,
                "toolFrame": config.tool_frame,
                "urdfPath": config.urdf_path,
                "jointLimits": config.joint_limits,
                "communication": config.communication,
            }
        except Exception as e:
            print(f"Warning: Failed to get robot config: {e}")
            return self._default_robot_config()

    def load_robot(self, robot_name: str = "abb_irb6700") -> bool:
        """Load a robot model for kinematics operations."""
        if not CONFIG_AVAILABLE or not self._config_manager:
            return False

        try:
            config = self._config_manager.get_robot(robot_name)

            # Resolve URDF path relative to config dir
            urdf_path = config.urdf_path
            if urdf_path and not Path(urdf_path).is_absolute():
                urdf_path = str(self._config_manager.config_dir / urdf_path)

            # Update config with resolved absolute path so RobotLoader can find it
            config = config.model_copy(update={"urdf_path": urdf_path})

            self._robot_instance = RobotLoader.load_from_config(config)
            tool_frame = self._robot_instance.config.tool_frame
            self._ik_solver = IKSolver(self._robot_instance.model, tool_frame=tool_frame)
            self._jacobian_solver = JacobianIKSolver(self._robot_instance.model, tool_frame=tool_frame)
            return True
        except Exception as e:
            print(f"Warning: Failed to load robot: {e}")
            return False

    def get_joint_limits(self) -> Dict[str, Any]:
        """Get joint limits for the loaded robot."""
        if self._robot_instance:
            limits = self._robot_instance.get_joint_limits()
            joint_names = self._robot_instance.get_joint_names()
            return {
                "jointNames": joint_names,
                "limits": {
                    name: {"min": float(lims[0]), "max": float(lims[1])}
                    for name, lims in limits.items()
                },
            }
        return self._default_joint_limits()

    def forward_kinematics(self, joint_values: List[float]) -> Dict[str, Any]:
        """Compute forward kinematics."""
        if not self._robot_instance:
            return self._mock_fk(joint_values)

        try:
            joint_names = self._robot_instance.get_joint_names()
            config = Configuration.from_revolute_values(
                joint_values[:len(joint_names)], joint_names
            )

            # Use tool frame from config (default: tool0) as end-effector link
            ee_link = self._robot_instance.config.tool_frame

            frame = self._robot_instance.model.forward_kinematics(config, link_name=ee_link)

            return {
                "position": {
                    "x": float(frame.point.x),
                    "y": float(frame.point.y),
                    "z": float(frame.point.z),
                },
                "orientation": {
                    "xaxis": [float(v) for v in frame.xaxis],
                    "yaxis": [float(v) for v in frame.yaxis],
                    "zaxis": [float(v) for v in frame.zaxis],
                },
                "valid": True,
            }
        except Exception as e:
            return {
                "position": {"x": 0, "y": 0, "z": 0},
                "orientation": {"xaxis": [1, 0, 0], "yaxis": [0, 1, 0], "zaxis": [0, 0, 1]},
                "valid": False,
                "error": str(e),
            }

    def inverse_kinematics(
        self, target_position: List[float], target_orientation: Optional[List[float]] = None,
        initial_guess: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Compute inverse kinematics for a target pose."""
        if not self._ik_solver:
            return {"solution": None, "error": "IK solver not loaded"}

        try:
            # Build target frame
            point = Point(*target_position)
            if target_orientation:
                xaxis = Vector(target_orientation[0], target_orientation[1], target_orientation[2])
                yaxis = Vector(target_orientation[3], target_orientation[4], target_orientation[5])
                target_frame = Frame(point, xaxis, yaxis)
            else:
                # Default: tool pointing down (standard manufacturing orientation)
                target_frame = Frame(point, Vector(1, 0, 0), Vector(0, -1, 0))

            solution = self._ik_solver.solve(
                target_frame,
                initial_guess=initial_guess,
                max_iterations=200,
                tolerance=1e-3,
                orientation_weight=0.1,
            )

            if solution is not None:
                return {
                    "solution": list(solution.joint_values),
                    "jointNames": self._ik_solver.joint_names,
                    "valid": True,
                }
            else:
                return {"solution": None, "valid": False, "error": "No IK solution found"}

        except Exception as e:
            return {"solution": None, "valid": False, "error": str(e)}

    def solve_toolpath_ik(
        self, waypoints: List[List[float]], initial_guess: Optional[List[float]] = None,
        tcp_offset: Optional[List[float]] = None, max_waypoints: int = 500,
    ) -> Dict[str, Any]:
        """Solve IK for a sequence of waypoints (batch operation for simulation).

        Uses full 6-DOF IK with proper tool orientation (torch pointing down
        for WAAM). Each solution seeds the next for smooth joint trajectories.

        When len(waypoints) > max_waypoints, uniformly samples down to
        max_waypoints, solves the sample, then expands results back to full size
        by nearest-neighbor mapping.

        The tcp_offset [x, y, z, rx, ry, rz] (meters/radians) shifts the IK target
        so the solver finds the flange position that places the tool tip at each waypoint.
        """
        if not self._ik_solver:
            return {"trajectory": [], "error": "IK solver not loaded"}

        total = len(waypoints)

        # --- Sampling: pick evenly-spaced indices if too many waypoints ---
        if total > max_waypoints:
            import numpy as _np
            sample_indices = _np.linspace(0, total - 1, max_waypoints, dtype=int).tolist()
            sampled_wps = [waypoints[i] for i in sample_indices]
        else:
            sample_indices = list(range(total))
            sampled_wps = waypoints

        # Solve IK on the (possibly sampled) subset
        sampled_traj = []
        sampled_reach = []
        # Start from a reasonable home pose if no initial guess provided
        if initial_guess is None:
            initial_guess = [0.0, 0.0, 0.5, 0.0, -0.5, 0.0]
        current_guess = initial_guess

        # TCP offset: shift target so flange reaches the right position
        tcp_z = tcp_offset[2] if tcp_offset and len(tcp_offset) >= 3 else 0.0

        for i, wp in enumerate(sampled_wps):
            flange_point = Point(wp[0], wp[1], wp[2] + tcp_z)
            target_frame = Frame(flange_point, Vector(1, 0, 0), Vector(0, -1, 0))

            solution = self._ik_solver.solve(
                target_frame,
                initial_guess=current_guess,
                max_iterations=100,
                tolerance=1e-3,
                orientation_weight=0.1,
            )

            if solution is not None:
                joint_vals = list(solution.joint_values)
                sampled_traj.append(joint_vals)
                sampled_reach.append(True)
                current_guess = joint_vals
            else:
                sampled_traj.append(current_guess if current_guess else [0.0] * self._ik_solver.n_joints)
                sampled_reach.append(False)

        # --- Expand back to full size via nearest-sample mapping ---
        if total > max_waypoints:
            trajectory = []
            reachability = []
            sample_idx_ptr = 0
            for wi in range(total):
                # Advance pointer to nearest sample index
                while (sample_idx_ptr < len(sample_indices) - 1 and
                       abs(sample_indices[sample_idx_ptr + 1] - wi) < abs(sample_indices[sample_idx_ptr] - wi)):
                    sample_idx_ptr += 1
                trajectory.append(sampled_traj[sample_idx_ptr])
                reachability.append(sampled_reach[sample_idx_ptr])
        else:
            trajectory = sampled_traj
            reachability = sampled_reach

        reachable_count = sum(reachability)
        return {
            "trajectory": trajectory,
            "reachability": reachability,
            "reachableCount": reachable_count,
            "totalPoints": total,
            "sampledPoints": len(sampled_wps),
            "reachabilityPercent": (reachable_count / total * 100) if total else 0,
        }

    def _default_robot_config(self) -> Dict[str, Any]:
        """Return default ABB IRB 6700 config when real config unavailable."""
        return {
            "name": "ABB IRB 6700-200/2.60",
            "manufacturer": "ABB",
            "type": "industrial_arm",
            "baseFrame": "base_link",
            "toolFrame": "tool0",
            "dof": 6,
            "maxPayload": 200,
            "maxReach": 2600,
            "jointNames": [f"joint_{i+1}" for i in range(6)],
        }

    def _default_joint_limits(self) -> Dict[str, Any]:
        """Default ABB IRB 6700 joint limits."""
        limits = {
            "joint_1": {"min": -2.967, "max": 2.967},
            "joint_2": {"min": -1.134, "max": 1.4835},
            "joint_3": {"min": -3.142, "max": 1.222},
            "joint_4": {"min": -5.236, "max": 5.236},
            "joint_5": {"min": -2.094, "max": 2.094},
            "joint_6": {"min": -6.283, "max": 6.283},
        }
        return {
            "jointNames": list(limits.keys()),
            "limits": limits,
        }

    def _mock_fk(self, joint_values: List[float]) -> Dict[str, Any]:
        """Simple mock FK for when real robot model isn't loaded."""
        import math
        # Very rough approximation of ABB IRB 6700 geometry
        j1, j2 = joint_values[0] if joint_values else 0, joint_values[1] if len(joint_values) > 1 else 0
        reach = 2.0  # meters
        x = reach * math.cos(j1) * math.cos(j2)
        y = reach * math.sin(j1) * math.cos(j2)
        z = 0.78 + reach * math.sin(j2)
        return {
            "position": {"x": round(x, 4), "y": round(y, 4), "z": round(z, 4)},
            "orientation": {"xaxis": [1, 0, 0], "yaxis": [0, 1, 0], "zaxis": [0, 0, 1]},
            "valid": True,
            "mock": True,
        }
