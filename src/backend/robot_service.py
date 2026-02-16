"""
Robot service for OpenAxis backend.

Handles robot configuration, forward/inverse kinematics, and joint limits.

IK Strategy:
  Primary: roboticstoolbox-python (Peter Corke) — production-grade, DH-based,
           30-90µs per solve with C++ backend. Well-tested, URDF-aware.
  Fallback: Custom numerical IK via scipy (IKSolver / JacobianIKSolver).

For large toolpaths (200K+ waypoints), IK is solved in chunks (not all at once)
to keep memory low and enable progressive streaming to the frontend.
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Production IK: roboticstoolbox-python ────────────────────────────────────
try:
    import numpy as np
    from roboticstoolbox import DHRobot, RevoluteDH
    from spatialmath import SE3
    RTB_AVAILABLE = True
except ImportError:
    RTB_AVAILABLE = False
    print("Warning: roboticstoolbox-python not installed. Using fallback IK solver.")

# ── Fallback IK: custom compas-based solvers ─────────────────────────────────
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


def _create_irb6700_dh() -> 'DHRobot':
    """Create ABB IRB 6700 DH model from URDF-derived parameters.

    DH parameters extracted from config/urdf/abb_irb6700.urdf:
      d1=0.780m  a1=0.320m  (base to shoulder)
      a2=1.125m             (upper arm)
      a3=0.200m  d4=1.1425m (forearm with wrist offset)
      d6=0.200m             (wrist to flange)

    This is a standard 6R industrial manipulator with 3 intersecting
    wrist axes — the same kinematic family as most ABB, KUKA, Fanuc robots.
    """
    if not RTB_AVAILABLE:
        return None

    robot = DHRobot([
        RevoluteDH(d=0.780,   a=0.320, alpha=-np.pi / 2),  # J1: base rotation
        RevoluteDH(d=0,       a=1.125, alpha=0),             # J2: shoulder
        RevoluteDH(d=0,       a=0.200, alpha=-np.pi / 2),    # J3: elbow
        RevoluteDH(d=1.1425,  a=0,     alpha=np.pi / 2),     # J4: wrist 1
        RevoluteDH(d=0,       a=0,     alpha=-np.pi / 2),    # J5: wrist 2
        RevoluteDH(d=0.200,   a=0,     alpha=0),              # J6: wrist 3
    ], name='ABB_IRB_6700')

    # Joint limits from URDF (radians)
    robot.qlim = np.array([
        [-2.96706, 2.96706],   # J1
        [-1.13446, 1.48353],   # J2
        [-3.14159, 1.22173],   # J3
        [-5.23599, 5.23599],   # J4
        [-2.26893, 2.26893],   # J5
        [-6.28319, 6.28319],   # J6
    ]).T

    return robot


class RobotService:
    """Service for robot configuration and kinematics operations."""

    def __init__(self, config_dir: Optional[str] = None):
        self._robot_instance: Optional[Any] = None
        self._ik_solver: Optional[Any] = None
        self._jacobian_solver: Optional[Any] = None
        self._config_manager: Optional[Any] = None

        # Production IK: roboticstoolbox DH model (always available, no URDF loading needed)
        self._rtb_robot = _create_irb6700_dh()
        if self._rtb_robot:
            print(f"[RobotService] Production IK ready: {self._rtb_robot.name} (roboticstoolbox)")

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
        tcp_offset: Optional[List[float]] = None, max_waypoints: int = 0,
        chunk_start: int = 0, chunk_size: int = 0,
    ) -> Dict[str, Any]:
        """Solve IK for a sequence of waypoints using roboticstoolbox-python.

        Uses Peter Corke's roboticstoolbox (production-grade, DH-based IK solver)
        with Levenberg-Marquardt optimization. Each solution seeds the next for
        smooth, continuous joint trajectories.

        Supports two modes:
          1. Full batch (default): Solves ALL waypoints. Suitable for <50K points.
          2. Chunked: Set chunk_start + chunk_size to solve a window.
             Frontend requests chunks progressively as simulation advances.

        The tcp_offset [x, y, z, rx, ry, rz] (meters/radians) shifts the IK target
        so the solver finds the flange position that places the tool tip at each waypoint.
        """
        total = len(waypoints)

        # Determine which waypoints to solve
        if chunk_size > 0:
            start = max(0, chunk_start)
            end = min(total, start + chunk_size)
            solve_wps = waypoints[start:end]
        else:
            start = 0
            end = total
            solve_wps = waypoints

        # TCP offset: shift target so flange reaches the right position
        tcp_z = tcp_offset[2] if tcp_offset and len(tcp_offset) >= 3 else 0.0

        # ── Primary: roboticstoolbox-python DH solver ─────────────────────────
        if RTB_AVAILABLE and self._rtb_robot is not None:
            return self._solve_rtb(solve_wps, tcp_z, initial_guess, start, total)

        # ── Fallback: custom compas IK solver ─────────────────────────────────
        if self._ik_solver:
            return self._solve_compas(solve_wps, tcp_z, initial_guess, start, total)

        return {"trajectory": [], "error": "No IK solver available"}

    def _solve_rtb(
        self, waypoints: list, tcp_z: float,
        initial_guess: Optional[list], chunk_start: int, total: int,
    ) -> Dict[str, Any]:
        """Solve IK using roboticstoolbox-python (production-grade DH solver)."""
        t0 = time.perf_counter()
        robot = self._rtb_robot

        # Initial seed: reasonable home pose for ABB IRB 6700
        if initial_guess and len(initial_guess) >= 6:
            q_seed = np.array(initial_guess[:6])
        else:
            q_seed = np.array([0.0, -0.5, 0.5, 0.0, -0.5, 0.0])

        trajectory = []
        reachability = []
        successes = 0

        for wp in waypoints:
            # Build target: tool pointing straight down (-Z in robot frame)
            target = SE3(wp[0], wp[1], wp[2] + tcp_z) * SE3.RPY(0, 180, 0, unit='deg')

            sol = robot.ikine_LM(target, q0=q_seed)

            if sol.success:
                q = sol.q.tolist()
                trajectory.append(q)
                reachability.append(True)
                q_seed = sol.q  # Seed next solve for continuity
                successes += 1
            else:
                # Use previous seed as fallback (maintains continuity)
                trajectory.append(q_seed.tolist())
                reachability.append(False)

        dt = time.perf_counter() - t0
        n = len(waypoints)
        print(
            f"[IK-RTB] Solved {successes}/{n} waypoints in {dt:.2f}s "
            f"({dt/max(n,1)*1000:.1f}ms/pt), chunk_start={chunk_start}"
        )

        return {
            "trajectory": trajectory,
            "reachability": reachability,
            "reachableCount": successes,
            "totalPoints": total,
            "solvedPoints": n,
            "chunkStart": chunk_start,
            "reachabilityPercent": (successes / max(n, 1) * 100),
            "solverTime": round(dt, 3),
            "solver": "roboticstoolbox",
        }

    def _solve_compas(
        self, waypoints: list, tcp_z: float,
        initial_guess: Optional[list], chunk_start: int, total: int,
    ) -> Dict[str, Any]:
        """Fallback IK using custom compas-based solver."""
        t0 = time.perf_counter()

        if initial_guess is None:
            initial_guess = [0.0, 0.0, 0.5, 0.0, -0.5, 0.0]
        current_guess = initial_guess

        trajectory = []
        reachability = []
        successes = 0

        for wp in waypoints:
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
                trajectory.append(joint_vals)
                reachability.append(True)
                current_guess = joint_vals
                successes += 1
            else:
                trajectory.append(current_guess if current_guess else [0.0] * 6)
                reachability.append(False)

        dt = time.perf_counter() - t0
        n = len(waypoints)
        print(
            f"[IK-Compas] Solved {successes}/{n} waypoints in {dt:.2f}s, "
            f"chunk_start={chunk_start}"
        )

        return {
            "trajectory": trajectory,
            "reachability": reachability,
            "reachableCount": successes,
            "totalPoints": total,
            "solvedPoints": n,
            "chunkStart": chunk_start,
            "reachabilityPercent": (successes / max(n, 1) * 100),
            "solverTime": round(dt, 3),
            "solver": "compas",
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
