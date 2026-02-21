"""
Robot service for OpenAxis backend.

Handles robot configuration, forward/inverse kinematics, and joint limits.

IK Strategy:
  Primary: roboticstoolbox-python (Peter Corke) — production-grade, DH-based,
           30-90us per solve with C++ backend. Well-tested, URDF-aware.
  Fallback: compas_fab PyBulletClient IK (damped least-squares via PyBullet).

For large toolpaths (200K+ waypoints), IK is solved in chunks (not all at once)
to keep memory low and enable progressive streaming to the frontend.
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from openaxis.core.logging import get_logger

logger = get_logger(__name__)

# ── Production IK: roboticstoolbox-python ────────────────────────────────────
try:
    import numpy as np
    from roboticstoolbox import ERobot, ETS, ET
    from spatialmath import SE3
    RTB_AVAILABLE = True
except ImportError:
    RTB_AVAILABLE = False
    logger.warning("rtb_unavailable", msg="roboticstoolbox-python not installed, using fallback IK solver")

# ── Fallback IK: compas_fab PyBulletClient ───────────────────────────────────
try:
    from openaxis.core.config import ConfigManager, RobotConfig
    from openaxis.core.robot import RobotLoader, RobotInstance
    from openaxis.motion.kinematics import IKSolver
    from compas.geometry import Frame, Point, Vector
    from compas_robots import Configuration
    CONFIG_AVAILABLE = True
except ImportError as e:
    logger.warning("robot_modules_unavailable", error=str(e))
    CONFIG_AVAILABLE = False


def _create_irb6700_ets() -> 'ERobot':
    """Create ABB IRB 6700 kinematic model as an ETS matching the URDF exactly.

    Each joint is: fixed translation to child-frame origin, then revolute rotation
    about the joint axis — read directly from config/urdf/abb_irb6700.urdf:

        joint_1: origin (0, 0, 0.780) m,  axis Z  (0 0 1)
        joint_2: origin (0.320, 0, 0) m,  axis Y  (0 1 0)
        joint_3: origin (0, 0, 1.125) m,  axis Y  (0 1 0)
        joint_4: origin (0, 0, 0.200) m,  axis X  (1 0 0)
        joint_5: origin (1.1425, 0, 0) m, axis Y  (0 1 0)
        joint_6: origin (0.200, 0, 0) m,  axis X  (1 0 0)

    Verified against independent SE3 chain:
        FK(q=zeros) == (1662.5, 0, 2105.0) mm  [arm straight up, full reach forward]
        FK(J1=90°)  == (0, 1662.5, 2105.0) mm  [arm swung 90° left, same height]

    Reference: abb_irb6700.urdf <joint> origin/axis elements.
    Library:   roboticstoolbox-python ERobot / ETS (Peter Corke, Springer 2023).
    """
    if not RTB_AVAILABLE:
        return None

    e = ETS([
        ET.tz(0.780), ET.Rz(),    # joint_1: base rotation around Z
        ET.tx(0.320), ET.Ry(),    # joint_2: shoulder around Y
        ET.tz(1.125), ET.Ry(),    # joint_3: elbow around Y
        ET.tz(0.200), ET.Rx(),    # joint_4: wrist-1 around X
        ET.tx(1.1425), ET.Ry(),   # joint_5: wrist-2 around Y
        ET.tx(0.200), ET.Rx(),    # joint_6: wrist-3 around X
    ])

    return ERobot(e, name='ABB_IRB6700')


class RobotService:
    """Service for robot configuration and kinematics operations."""

    def __init__(self, config_dir: Optional[str] = None):
        self._robot_instance: Optional[Any] = None
        self._ik_solver: Optional[Any] = None
        self._config_manager: Optional[Any] = None

        # Production IK: roboticstoolbox ETS model (URDF-derived, always available)
        self._rtb_robot = _create_irb6700_ets()
        if self._rtb_robot:
            logger.info("production_ik_ready", robot=self._rtb_robot.name, solver="roboticstoolbox")

        if CONFIG_AVAILABLE and config_dir:
            try:
                self._config_manager = ConfigManager(config_dir=Path(config_dir))
                self._config_manager.load()
            except Exception as e:
                logger.warning("config_load_failed", error=str(e))

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
                "homePosition": config.home_position,
                "urdfPath": config.urdf_path,
                "jointLimits": config.joint_limits,
                "communication": config.communication,
            }
        except Exception as e:
            logger.warning("robot_config_failed", error=str(e))
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
            # IKSolver uses compas_fab PyBulletClient for IK solving.
            # Use 'link_6' for IK (tool0 has a fixed rotation that confuses
            # PyBullet's numerical IK solver).
            self._ik_solver = IKSolver(
                self._robot_instance.model,
                urdf_path=urdf_path,
                tool_frame="link_6",
            )
            return True
        except Exception as e:
            logger.warning("robot_load_failed", error=str(e))
            return False

    def _get_home_position(self, n_joints: int = 6) -> list[float]:
        """Get home position from robot config, or use default.

        The home position is used as the initial IK seed for predictable
        sim-to-reality behavior. Users can set it per-robot via YAML config.

        Args:
            n_joints: Expected number of joints (for validation/padding).

        Returns:
            Home joint configuration in radians.
        """
        default_home = [0.0, -0.5, 0.5, 0.0, -0.5, 0.0]

        if self._robot_instance and hasattr(self._robot_instance, 'config'):
            home = self._robot_instance.config.home_position
            if home and len(home) >= n_joints:
                return list(home[:n_joints])

        if self._config_manager:
            try:
                config = self._config_manager.get_robot("abb_irb6700")
                if config.home_position and len(config.home_position) >= n_joints:
                    return list(config.home_position[:n_joints])
            except Exception:
                pass

        return default_home[:n_joints]

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

    def forward_kinematics(
        self, joint_values: List[float], tcp_offset: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Compute forward kinematics using roboticstoolbox-python DHRobot.fkine().

        Uses the SAME DH model as the IK solver (self._rtb_robot) for
        consistency. When tcp_offset is provided, robot.tool is set so
        fkine() returns the TCP position (not just the flange).

        Library: roboticstoolbox-python (Peter Corke)
        fkine() computes T = base * L1*L2*...*L6 * tool
        Reference: Peter Corke, "Robotics, Vision and Control", Springer 2023.
        """
        if not RTB_AVAILABLE or self._rtb_robot is None:
            return {
                "valid": False,
                "error": "roboticstoolbox-python not available",
                "solver": "none",
            }

        robot = self._rtb_robot
        original_tool = robot.tool
        try:
            # Set full 6DOF tool transform if tcp_offset provided.
            # Convention: [tx, ty, tz] meters + [rx, ry, rz] degrees ZYX Euler, in flange frame.
            # Matches ABB tooldata, KUKA $TOOL, Fanuc UTOOL conventions.
            if tcp_offset and len(tcp_offset) >= 6:
                tx, ty, tz = tcp_offset[0], tcp_offset[1], tcp_offset[2]
                rx, ry, rz = tcp_offset[3], tcp_offset[4], tcp_offset[5]
                robot.tool = SE3(tx, ty, tz) * SE3.RPY(rx, ry, rz, unit='deg')
            elif tcp_offset and len(tcp_offset) >= 3:
                tx, ty, tz = tcp_offset[0], tcp_offset[1], tcp_offset[2]
                robot.tool = SE3(tx, ty, tz)

            q = np.array(joint_values[:6])
            T = robot.fkine(q)

            # SE3.t = translation [x,y,z], SE3.R = 3x3 rotation matrix
            pos = T.t
            R = T.R

            return {
                "position": {
                    "x": float(pos[0]),
                    "y": float(pos[1]),
                    "z": float(pos[2]),
                },
                "orientation": {
                    "xaxis": [float(R[0, 0]), float(R[1, 0]), float(R[2, 0])],
                    "yaxis": [float(R[0, 1]), float(R[1, 1]), float(R[2, 1])],
                    "zaxis": [float(R[0, 2]), float(R[1, 2]), float(R[2, 2])],
                },
                "valid": True,
                "solver": "roboticstoolbox",
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "solver": "roboticstoolbox",
            }
        finally:
            robot.tool = original_tool

    def inverse_kinematics(
        self, target_position: List[float], target_orientation: Optional[List[float]] = None,
        initial_guess: Optional[List[float]] = None,
        tcp_offset: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Compute inverse kinematics for a target pose (single point).

        Input frame: meters, Z-up, robot base frame (same as solve_toolpath_ik).
        target_orientation: optional [rx_deg, ry_deg, rz_deg] Euler RPY in degrees.
        If omitted, defaults to tool pointing straight down (-Z), the standard
        WAAM/manufacturing posture (RPY = [0, 180, 0] deg).

        tcp_offset: [x, y, z, rx, ry, rz] (meters, degrees) — same convention as
        solve_toolpath_ik. Sets robot.tool so the solver places the TCP (not the
        flange) at target_position. The target position is the desired TCP location.

        Uses roboticstoolbox DHRobot.ikine_LM() (same solver as solve_toolpath_ik)
        when available.  Falls back to compas_fab IK if RTB is not installed.

        Reference: Peter Corke, "Robotics, Vision and Control", Springer 2023.
        ABB IRB 6700 base frame: Z-up, X forward (ABB Product Manual 3HAC044266).
        """
        # ── Primary: roboticstoolbox (same path as solve_toolpath_ik) ──────────
        if RTB_AVAILABLE and self._rtb_robot is not None:
            try:
                robot = self._rtb_robot
                original_tool = robot.tool

                # Apply TCP offset (same 6DOF convention as solve_toolpath_ik).
                if tcp_offset and len(tcp_offset) >= 6:
                    tx, ty, tz = tcp_offset[0], tcp_offset[1], tcp_offset[2]
                    rx_t, ry_t, rz_t = tcp_offset[3], tcp_offset[4], tcp_offset[5]
                    robot.tool = SE3(tx, ty, tz) * SE3.RPY(rx_t, ry_t, rz_t, unit='deg')
                elif tcp_offset and len(tcp_offset) >= 3:
                    tx, ty, tz = tcp_offset[0], tcp_offset[1], tcp_offset[2]
                    robot.tool = SE3(tx, ty, tz)
                else:
                    robot.tool = SE3()  # identity — TCP = flange

                if initial_guess and len(initial_guess) >= 6:
                    q0 = np.array(initial_guess[:6])
                else:
                    q0 = np.array(self._get_home_position(6))

                x, y, z = target_position[0], target_position[1], target_position[2]

                if target_orientation and len(target_orientation) >= 3:
                    # [rx, ry, rz] in degrees
                    rx, ry, rz = target_orientation[0], target_orientation[1], target_orientation[2]
                    target = SE3(x, y, z) * SE3.RPY(rx, ry, rz, unit='deg')
                else:
                    # Default: tool pointing straight down (-Z), standard WAAM posture
                    target = SE3(x, y, z) * SE3.RPY(0, 180, 0, unit='deg')

                sol = robot.ikine_LM(target, q0=q0)
                robot.tool = original_tool

                if sol.success:
                    joint_names = [f'joint_{i+1}' for i in range(len(sol.q))]
                    return {
                        "solution": sol.q.tolist(),
                        "jointNames": joint_names,
                        "valid": True,
                        "solver": "roboticstoolbox",
                    }
                else:
                    return {
                        "solution": None,
                        "valid": False,
                        "error": "IK solver found no solution — target may be unreachable or outside joint limits",
                        "solver": "roboticstoolbox",
                    }
            except Exception as e:
                return {"solution": None, "valid": False, "error": str(e), "solver": "roboticstoolbox"}

        # ── Fallback: compas_fab PyBullet IK ───────────────────────────────────
        if not self._ik_solver:
            return {"solution": None, "valid": False, "error": "No IK solver available (roboticstoolbox not installed)"}

        try:
            point = Point(*target_position)
            if target_orientation and len(target_orientation) >= 6:
                # Legacy 6-float format: [xaxis.x, xaxis.y, xaxis.z, yaxis.x, yaxis.y, yaxis.z]
                xaxis = Vector(target_orientation[0], target_orientation[1], target_orientation[2])
                yaxis = Vector(target_orientation[3], target_orientation[4], target_orientation[5])
                target_frame = Frame(point, xaxis, yaxis)
            else:
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
                    "solver": "compas_fab",
                }
            else:
                return {"solution": None, "valid": False, "error": "No IK solution found", "solver": "compas_fab"}

        except Exception as e:
            return {"solution": None, "valid": False, "error": str(e)}

    def solve_toolpath_ik(
        self, waypoints: List[List[float]], initial_guess: Optional[List[float]] = None,
        tcp_offset: Optional[List[float]] = None, max_waypoints: int = 0,
        chunk_start: int = 0, chunk_size: int = 0,
        normals: Optional[List[List[float]]] = None,
    ) -> Dict[str, Any]:
        """Solve IK for a sequence of waypoints using roboticstoolbox-python.

        Uses Peter Corke's roboticstoolbox (production-grade, DH-based IK solver)
        with Levenberg-Marquardt optimization. Each solution seeds the next for
        smooth, continuous joint trajectories.

        Supports two modes:
          1. Full batch (default): Solves ALL waypoints. Suitable for <50K points.
          2. Chunked: Set chunk_start + chunk_size to solve a window.
             Frontend requests chunks progressively as simulation advances.

        tcp_offset: [x, y, z, rx, ry, rz] (meters, degrees) sets robot.tool so the
        solver finds the flange position that places the TCP at each waypoint.
        tcp_offset is expressed in the flange frame (standard for all robot brands:
        ABB tooldata, KUKA $TOOL, Fanuc UTOOL).

        normals: optional list of [nx, ny, nz] unit vectors (one per waypoint) in
        the robot base frame (meters, Z-up). Each normal defines the slicing plane
        normal — the tool Z-axis is aligned to this direction (tool approaches the
        print surface along the plane normal). For planar slicing, all normals are
        [0, 0, 1] (tool pointing straight down from above). For angled/non-planar
        slicing the normals will vary per waypoint. If omitted, defaults to [0, 0, 1].
        """
        total = len(waypoints)

        # Determine which waypoints to solve
        if chunk_size > 0:
            start = max(0, chunk_start)
            end = min(total, start + chunk_size)
            solve_wps = waypoints[start:end]
            solve_normals = normals[start:end] if normals else None
        else:
            start = 0
            end = total
            solve_wps = waypoints
            solve_normals = normals

        # TCP offset passed to solver — it sets robot.tool = SE3(...) per
        # roboticstoolbox-python standard API (Peter Corke, "Robotics, Vision
        # and Control", Springer 2023). The library's ikine_LM automatically
        # accounts for robot.tool via the ETS chain.

        # ── Primary: roboticstoolbox-python DH solver ─────────────────────────
        if RTB_AVAILABLE and self._rtb_robot is not None:
            return self._solve_rtb(solve_wps, tcp_offset, initial_guess, start, total, solve_normals)

        # ── Fallback: compas IK solver ────────────────────────────────────────
        if self._ik_solver:
            return self._solve_compas(solve_wps, tcp_offset, initial_guess, start, total)

        return {"trajectory": [], "error": "No IK solver available"}

    def _solve_rtb(
        self, waypoints: list, tcp_offset: Optional[List[float]],
        initial_guess: Optional[list], chunk_start: int, total: int,
        normals: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Solve IK using roboticstoolbox-python (production-grade DH solver).

        Uses robot.tool = SE3(...) to set the full 6DOF TCP transform.
        ikine_LM automatically accounts for robot.tool via the ETS chain.

        TCP convention (matches all robot OLP standards):
          - robot.tool is expressed in the flange frame
          - Translation: [tx, ty, tz] in meters from flange origin to TCP
          - Rotation: SE3.RPY(rx, ry, rz, unit='deg') — ZYX Euler, flange frame
          - Same definition as ABB tooldata, KUKA $TOOL, Fanuc UTOOL

        Target frame orientation:
          - Derived from the slicing plane normal (per-waypoint)
          - The tool Z-axis (approach direction) aligns with the plane normal
          - For planar Z-up slicing: normal = [0,0,1], tool points straight down
          - For angled/non-planar slicing: normal varies per waypoint
          - Method: build a rotation matrix with Z=normal, then find minimal rotation
            Reference: Peter Corke, "Robotics, Vision and Control", Springer 2023, §2.1

        Library: roboticstoolbox-python DHRobot.ikine_LM()
        """
        t0 = time.perf_counter()
        robot = self._rtb_robot

        # Set full 6DOF tool transform (standard roboticstoolbox API).
        # robot.tool is post-multiplied in fkine() and baked into ETS for ikine_LM().
        # Convention: [tx, ty, tz] meters + [rx, ry, rz] degrees ZYX Euler, all in flange frame.
        original_tool = robot.tool
        if tcp_offset and len(tcp_offset) >= 6:
            tx, ty, tz = tcp_offset[0], tcp_offset[1], tcp_offset[2]
            rx, ry, rz = tcp_offset[3], tcp_offset[4], tcp_offset[5]
            robot.tool = SE3(tx, ty, tz) * SE3.RPY(rx, ry, rz, unit='deg')
        elif tcp_offset and len(tcp_offset) >= 3:
            tx, ty, tz = tcp_offset[0], tcp_offset[1], tcp_offset[2]
            robot.tool = SE3(tx, ty, tz)
        else:
            robot.tool = SE3()  # identity = no tool offset

        # Initial seed: use configured home position for predictable behavior
        if initial_guess and len(initial_guess) >= 6:
            q_seed = np.array(initial_guess[:6])
        else:
            q_seed = np.array(self._get_home_position(6))

        trajectory = []
        reachability = []
        successes = 0

        for i, wp in enumerate(waypoints):
            # Build target SE3 from waypoint position + slicing plane normal.
            # The normal defines which direction the tool should approach from:
            # tool Z-axis = plane normal (the slicer tells us which way is "up"
            # for each print layer). We build a full rotation from the normal.
            if normals and i < len(normals):
                target = SE3(wp[0], wp[1], wp[2]) * self._normal_to_SE3(normals[i])
            else:
                # Default: planar Z-up slicing → tool points straight down (-Z in world)
                # RPY(0, 180, 0) flips the robot Z-axis to point downward.
                target = SE3(wp[0], wp[1], wp[2]) * SE3.RPY(0, 180, 0, unit='deg')

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

        # Restore original tool to avoid side effects on other calls
        robot.tool = original_tool

        dt = time.perf_counter() - t0
        n = len(waypoints)
        logger.info(
            "ik_solve_complete",
            solver="roboticstoolbox",
            successes=successes,
            total=n,
            time_s=round(dt, 2),
            ms_per_point=round(dt / max(n, 1) * 1000, 1),
            chunk_start=chunk_start,
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

    def _normal_to_SE3(self, normal: List[float]) -> 'SE3':
        """Build a rotation SE3 from a slicing plane normal vector.

        The normal defines the "up" direction of the print layer — the tool
        Z-axis must align with (oppose) this direction so the tool approaches
        perpendicular to the print plane.

        Convention:
          - Input: [nx, ny, nz] — unit vector in robot base frame (Z-up)
          - Output: SE3 rotation where Z-axis = -normal (tool Z points INTO surface)
            i.e. approach direction opposes the normal (tool comes from above the layer)

        For planar Z-up slicing: normal = [0,0,1] → tool Z = [0,0,-1]
        → equivalent to RPY(0, 180, 0) which is the original hardcoded default.

        Algorithm: Rodrigues' rotation formula to align [0,0,1] with -normal.
        Reference: Peter Corke, "Robotics, Vision and Control", Springer 2023, §2.1.
        """
        n = np.array(normal, dtype=float)
        norm = np.linalg.norm(n)
        if norm < 1e-9:
            # Degenerate normal — fall back to straight-down
            return SE3.RPY(0, 180, 0, unit='deg')
        n = n / norm

        # Tool Z axis should oppose the normal (approach from above the layer)
        tool_z = -n

        # Build an orthonormal frame: pick an arbitrary X that is not parallel to tool_z
        if abs(tool_z[0]) < 0.9:
            arb = np.array([1.0, 0.0, 0.0])
        else:
            arb = np.array([0.0, 1.0, 0.0])

        tool_y = np.cross(tool_z, arb)
        tool_y /= np.linalg.norm(tool_y)
        tool_x = np.cross(tool_y, tool_z)
        tool_x /= np.linalg.norm(tool_x)

        # Rotation matrix: columns are [tool_x, tool_y, tool_z] in robot base frame
        R = np.column_stack([tool_x, tool_y, tool_z])
        return SE3(R)

    def _solve_compas(
        self, waypoints: list, tcp_offset: Optional[List[float]],
        initial_guess: Optional[list], chunk_start: int, total: int,
    ) -> Dict[str, Any]:
        """Fallback IK using compas-based solver.

        Note: COMPAS IK solver does not support robot.tool transforms.
        TCP offset is applied as a manual Z shift (limited to Z only).
        """
        t0 = time.perf_counter()

        # COMPAS IK has no robot.tool equivalent — apply Z offset manually
        tcp_z = 0.0
        if tcp_offset and len(tcp_offset) >= 3:
            tcp_z = tcp_offset[2]
            if tcp_offset[0] != 0 or tcp_offset[1] != 0:
                logger.warning(
                    "compas_ik_partial_tcp_offset",
                    msg="COMPAS IK only supports Z TCP offset",
                    ignored_x=tcp_offset[0],
                    ignored_y=tcp_offset[1],
                )

        if initial_guess is None:
            initial_guess = self._get_home_position(6)
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
        logger.info(
            "ik_solve_complete",
            solver="compas",
            successes=successes,
            total=n,
            time_s=round(dt, 2),
            chunk_start=chunk_start,
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

