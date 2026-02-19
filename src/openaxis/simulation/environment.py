"""
Simulation environment for robotic manufacturing.

This module provides a wrapper around PyBullet for simulating
robotic manufacturing processes including visualization, collision
detection, and physics-based simulation.

The spec calls for pybullet_industrial for manufacturing-specific
simulation (material deposition/removal, force modeling). The base
PyBullet environment is retained for robot loading and physics,
with pybullet_industrial extending it for manufacturing processes.

Library: https://pybullet-industrial.readthedocs.io/
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pybullet as p

try:
    import pybullet_data
    PYBULLET_DATA_AVAILABLE = True
except ImportError:
    PYBULLET_DATA_AVAILABLE = False

try:
    import pybullet_industrial as pbi
    PYBULLET_INDUSTRIAL_AVAILABLE = True
except ImportError:
    PYBULLET_INDUSTRIAL_AVAILABLE = False


class SimulationMode(Enum):
    """Simulation modes."""

    GUI = "GUI"  # Graphical interface
    DIRECT = "DIRECT"  # Headless mode (no visualization)


class SimulationEnvironment:
    """
    Manages the PyBullet simulation environment.

    This class provides a high-level interface for creating and managing
    simulation environments for robotic manufacturing.
    """

    def __init__(
        self,
        mode: SimulationMode = SimulationMode.GUI,
        time_step: float = 0.001,
        gravity: Tuple[float, float, float] = (0, 0, -9.81),
    ):
        """
        Initialize simulation environment.

        Args:
            mode: Simulation mode (GUI or DIRECT)
            time_step: Physics simulation time step (seconds)
            gravity: Gravity vector (x, y, z)
        """
        self.mode = mode
        self.time_step = time_step
        self.gravity = gravity
        self.client_id: Optional[int] = None
        self.is_running = False
        self._loaded_objects = {}  # body_id -> object_info

    def start(self) -> None:
        """Start the simulation environment."""
        if self.is_running:
            raise RuntimeError("Simulation already running")

        # Connect to PyBullet
        if self.mode == SimulationMode.GUI:
            self.client_id = p.connect(p.GUI)
        else:
            self.client_id = p.connect(p.DIRECT)

        if self.client_id < 0:
            raise RuntimeError("Failed to connect to PyBullet")

        # Configure simulation
        p.setGravity(*self.gravity, physicsClientId=self.client_id)
        p.setTimeStep(self.time_step, physicsClientId=self.client_id)

        # Set up search path for built-in models
        if PYBULLET_DATA_AVAILABLE:
            p.setAdditionalSearchPath(pybullet_data.getDataPath())

        # Configure camera (for GUI mode)
        if self.mode == SimulationMode.GUI:
            p.resetDebugVisualizerCamera(
                cameraDistance=2.0,
                cameraYaw=45,
                cameraPitch=-30,
                cameraTargetPosition=[0, 0, 0.5],
                physicsClientId=self.client_id,
            )

        self.is_running = True

    def stop(self) -> None:
        """Stop and disconnect from simulation."""
        if not self.is_running:
            return

        if self.client_id is not None:
            p.disconnect(physicsClientId=self.client_id)
            self.client_id = None

        self.is_running = False
        self._loaded_objects.clear()

    def step(self) -> None:
        """
        Advance simulation by one time step.

        This performs physics simulation for one time step.
        """
        if not self.is_running:
            raise RuntimeError("Simulation not running")

        p.stepSimulation(physicsClientId=self.client_id)

    def add_ground_plane(self) -> int:
        """
        Add a ground plane to the simulation.

        Creates a large flat box to act as the ground plane.

        Returns:
            Body ID of the ground plane
        """
        if not self.is_running:
            raise RuntimeError("Simulation not running")

        # Create ground plane as a large flat box
        # This is more reliable than loading plane.urdf
        collision_shape = p.createCollisionShape(
            shapeType=p.GEOM_BOX,
            halfExtents=[50, 50, 0.1],  # Large flat box
            physicsClientId=self.client_id,
        )

        visual_shape = p.createVisualShape(
            shapeType=p.GEOM_BOX,
            halfExtents=[50, 50, 0.1],
            rgbaColor=[0.7, 0.7, 0.7, 1.0],  # Gray
            physicsClientId=self.client_id,
        )

        plane_id = p.createMultiBody(
            baseMass=0,  # Static
            baseCollisionShapeIndex=collision_shape,
            baseVisualShapeIndex=visual_shape,
            basePosition=[0, 0, -0.1],
            physicsClientId=self.client_id,
        )

        self._loaded_objects[plane_id] = {
            "type": "ground",
            "name": "plane",
        }

        return plane_id

    def load_urdf(
        self,
        urdf_path: Path | str,
        base_position: Tuple[float, float, float] = (0, 0, 0),
        base_orientation: Optional[Tuple[float, float, float, float]] = None,
        fixed_base: bool = True,
    ) -> int:
        """
        Load a URDF model into the simulation.

        Args:
            urdf_path: Path to URDF file
            base_position: Initial position (x, y, z)
            base_orientation: Initial orientation as quaternion (x, y, z, w)
            fixed_base: Whether the base should be fixed in space

        Returns:
            Body ID of the loaded model
        """
        if not self.is_running:
            raise RuntimeError("Simulation not running")

        urdf_path = Path(urdf_path)
        if not urdf_path.exists():
            raise FileNotFoundError(f"URDF file not found: {urdf_path}")

        # Default orientation (no rotation)
        if base_orientation is None:
            base_orientation = p.getQuaternionFromEuler([0, 0, 0])

        body_id = p.loadURDF(
            str(urdf_path),
            basePosition=base_position,
            baseOrientation=base_orientation,
            useFixedBase=fixed_base,
            physicsClientId=self.client_id,
        )

        self._loaded_objects[body_id] = {
            "type": "urdf",
            "path": str(urdf_path),
            "name": urdf_path.stem,
        }

        return body_id

    def load_mesh(
        self,
        mesh_path: Path | str,
        position: Tuple[float, float, float] = (0, 0, 0),
        orientation: Optional[Tuple[float, float, float, float]] = None,
        scale: float = 1.0,
        color: Optional[Tuple[float, float, float, float]] = None,
    ) -> int:
        """
        Load a mesh file (STL, OBJ) as a visual shape.

        Note: PyBullet on Windows has issues with STL files. STL files will be
        automatically converted to OBJ format for loading.

        Args:
            mesh_path: Path to mesh file
            position: Position (x, y, z)
            orientation: Orientation as quaternion (x, y, z, w)
            scale: Uniform scale factor
            color: RGBA color (0-1 range)

        Returns:
            Body ID of the loaded mesh
        """
        if not self.is_running:
            raise RuntimeError("Simulation not running")

        mesh_path = Path(mesh_path)
        if not mesh_path.exists():
            raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

        # PyBullet on Windows has issues with STL files - convert to OBJ
        if mesh_path.suffix.lower() == ".stl":
            # Check if OBJ version exists
            obj_path = mesh_path.with_suffix(".obj")
            if not obj_path.exists():
                # Convert STL to OBJ using trimesh
                import trimesh

                stl_mesh = trimesh.load(str(mesh_path))
                stl_mesh.export(str(obj_path))

            mesh_path = obj_path

        if orientation is None:
            orientation = p.getQuaternionFromEuler([0, 0, 0])

        # Create collision shape
        collision_shape = p.createCollisionShape(
            shapeType=p.GEOM_MESH,
            fileName=str(mesh_path),
            meshScale=[scale, scale, scale],
            physicsClientId=self.client_id,
        )

        # Create visual shape
        visual_shape = p.createVisualShape(
            shapeType=p.GEOM_MESH,
            fileName=str(mesh_path),
            meshScale=[scale, scale, scale],
            rgbaColor=color if color else [0.7, 0.7, 0.7, 1.0],
            physicsClientId=self.client_id,
        )

        # Create multi-body
        body_id = p.createMultiBody(
            baseMass=0,  # Static object
            baseCollisionShapeIndex=collision_shape,
            baseVisualShapeIndex=visual_shape,
            basePosition=position,
            baseOrientation=orientation,
            physicsClientId=self.client_id,
        )

        self._loaded_objects[body_id] = {
            "type": "mesh",
            "path": str(mesh_path),
            "name": mesh_path.stem,
        }

        return body_id

    def get_loaded_objects(self) -> dict:
        """Get dictionary of all loaded objects."""
        return self._loaded_objects.copy()

    def remove_object(self, body_id: int) -> None:
        """
        Remove an object from the simulation.

        Args:
            body_id: Body ID to remove
        """
        if not self.is_running:
            raise RuntimeError("Simulation not running")

        if body_id in self._loaded_objects:
            p.removeBody(body_id, physicsClientId=self.client_id)
            del self._loaded_objects[body_id]

    def reset(self) -> None:
        """Reset the simulation to initial state."""
        if not self.is_running:
            raise RuntimeError("Simulation not running")

        p.resetSimulation(physicsClientId=self.client_id)
        self._loaded_objects.clear()

        # Reapply configuration
        p.setGravity(*self.gravity, physicsClientId=self.client_id)
        p.setTimeStep(self.time_step, physicsClientId=self.client_id)

    # ── pybullet_industrial integration ──────────────────────────────────
    #
    # pybullet_industrial provides manufacturing-specific simulation:
    # - Extruder: Material deposition (FDM, WAAM, pellet, concrete)
    # - MillingTool: Material removal with force modeling
    # - Remover: Generic material removal
    # - RobotBase: Robot loading with end-effector management
    #
    # Library: https://pybullet-industrial.readthedocs.io/
    # Install: pip install pybullet-industrial

    def create_robot_base(
        self,
        urdf_path: Path | str,
        position: Tuple[float, float, float] = (0, 0, 0),
        orientation: Optional[Tuple[float, float, float, float]] = None,
        end_effector_link: str = "link_6",
    ) -> object:
        """
        Create a pybullet_industrial RobotBase from a URDF.

        The RobotBase wraps PyBullet's loadURDF and provides end-effector
        management, tool coupling, and joint control.

        NOTE: Must be called after start() — the SimulationEnvironment's
        PyBullet connection is shared with pybullet_industrial.

        Args:
            urdf_path: Path to robot URDF file
            position: Robot base position (x, y, z) in meters
            orientation: Base orientation as quaternion (x, y, z, w).
                         Defaults to identity (no rotation).
            end_effector_link: Name of the default end-effector link

        Returns:
            pbi.RobotBase object

        Raises:
            RuntimeError: If simulation not running
            ImportError: If pybullet_industrial is not installed
        """
        if not PYBULLET_INDUSTRIAL_AVAILABLE:
            raise ImportError(
                "pybullet_industrial not installed. "
                "Install with: pip install pybullet-industrial"
            )
        if not self.is_running:
            raise RuntimeError("Simulation not running — call start() first")

        if orientation is None:
            orientation = (0, 0, 0, 1)

        robot_base = pbi.RobotBase(
            urdf_model=str(Path(urdf_path).resolve()),
            start_position=np.array(position),
            start_orientation=np.array(orientation),
            default_endeffector=end_effector_link,
        )
        return robot_base

    def create_manufacturing_tool(
        self,
        tool_type: str,
        tool_urdf_path: Path | str,
        position: Tuple[float, float, float] = (0, 0, 0),
        orientation: Optional[Tuple[float, float, float, float]] = None,
        properties: Optional[dict] = None,
        coupled_robot: Optional[object] = None,
        end_effector_link: Optional[str] = None,
        tool_config: Optional[object] = None,
    ) -> object:
        """
        Create a manufacturing tool using pybullet_industrial.

        Dispatches to the appropriate pbi tool class based on tool_type.
        The tool can optionally be coupled to a robot immediately.

        Supported tool types:
        - 'extruder': pbi.Extruder for material deposition
        - 'milling': pbi.MillingTool for material removal with force
        - 'remover': pbi.Remover for generic material removal

        Args:
            tool_type: Type of tool ('extruder', 'milling', 'remover')
            tool_urdf_path: Path to tool URDF file
            position: Initial tool position (x, y, z) in meters
            orientation: Initial orientation as quaternion (x, y, z, w)
            properties: Tool-specific properties dictionary.
                For 'extruder': {'material': pbi.Plastic, ...}
                For 'milling': {'diameter': 6.0, 'rotation speed': 10000, ...}
                For 'remover': {'opening angle': 0, ...}
            coupled_robot: Optional pbi.RobotBase to couple to immediately
            end_effector_link: End-effector link name for coupling
            tool_config: Optional ToolConfig from the tool library. When
                provided, its properties are used as defaults (can be
                overridden by the ``properties`` argument). Also uses
                tool_config.type as tool_type if tool_type is empty, and
                tool_config.urdf_path for the URDF if tool_urdf_path is empty.

        Returns:
            pybullet_industrial tool object (Extruder, MillingTool, or Remover)

        Raises:
            ImportError: If pybullet_industrial is not installed
            RuntimeError: If simulation not running
            ValueError: If tool_type is not recognized
        """
        if not PYBULLET_INDUSTRIAL_AVAILABLE:
            raise ImportError(
                "pybullet_industrial not installed. "
                "Install with: pip install pybullet-industrial"
            )
        if not self.is_running:
            raise RuntimeError("Simulation not running — call start() first")

        # Merge tool_config defaults (if provided from tool library)
        if tool_config is not None:
            if not tool_type and hasattr(tool_config, "type"):
                tool_type = tool_config.type
            if not tool_urdf_path and hasattr(tool_config, "urdf_path") and tool_config.urdf_path:
                tool_urdf_path = tool_config.urdf_path
            # Tool library properties as defaults, explicit properties override
            if hasattr(tool_config, "properties") and tool_config.properties:
                merged_props = dict(tool_config.properties)
                if properties:
                    merged_props.update(properties)
                properties = merged_props

        if orientation is None:
            orientation = (0, 0, 0, 1)

        tool_urdf = str(Path(tool_urdf_path).resolve())
        pos = np.array(position)
        orn = np.array(orientation)

        if tool_type == "extruder":
            default_props = {
                "material": pbi.Plastic,
                "material properties": {
                    "particle size": 0.03,
                    "color": [0.2, 0.4, 0.8, 1.0],
                },
            }
            if properties:
                default_props.update(properties)

            tool = pbi.Extruder(
                urdf_model=tool_urdf,
                start_position=pos,
                start_orientation=orn,
                extruder_properties=default_props,
            )

        elif tool_type == "milling":
            default_props = {
                "diameter": 6.0,
                "rotation speed": 10000,
                "number of teeth": 4,
                "height": 50.0,
                "number of rays": 1,
            }
            if properties:
                default_props.update(properties)

            tool = pbi.MillingTool(
                urdf_model=tool_urdf,
                start_position=pos,
                start_orientation=orn,
                milling_properties=default_props,
            )

        elif tool_type == "remover":
            default_props = {
                "opening angle": 0,
                "number of rays": 1,
                "maximum distance": 0.2,
            }
            if properties:
                default_props.update(properties)

            tool = pbi.Remover(
                urdf_model=tool_urdf,
                start_position=pos,
                start_orientation=orn,
                remover_properties=default_props,
            )

        else:
            raise ValueError(
                f"Unknown tool type '{tool_type}'. "
                f"Supported: 'extruder', 'milling', 'remover'"
            )

        # Optionally couple to robot
        if coupled_robot is not None:
            tool.couple(
                coupled_robot,
                endeffector_name=end_effector_link,
            )

        return tool

    def couple_tool(
        self,
        tool: object,
        robot: object,
        end_effector_link: str = "link_6",
    ) -> None:
        """
        Couple a manufacturing tool to a robot.

        Args:
            tool: pybullet_industrial tool (Extruder, MillingTool, etc.)
            robot: pybullet_industrial RobotBase
            end_effector_link: Robot end-effector link name
        """
        if not PYBULLET_INDUSTRIAL_AVAILABLE:
            raise ImportError("pybullet_industrial not installed")
        tool.couple(robot, endeffector_name=end_effector_link)

    def decouple_tool(self, tool: object) -> None:
        """
        Decouple a manufacturing tool from its robot.

        Args:
            tool: pybullet_industrial tool to decouple
        """
        if not PYBULLET_INDUSTRIAL_AVAILABLE:
            raise ImportError("pybullet_industrial not installed")
        tool.decouple()

    @staticmethod
    def is_pybullet_industrial_available() -> bool:
        """Check if pybullet_industrial is available."""
        return PYBULLET_INDUSTRIAL_AVAILABLE

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
