# OpenAxis System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE LAYER                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Electron + React + Three.js                        │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │  │ Project Mgr │ │ 3D Viewport │ │ Path Editor │ │ Monitoring  │    │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │ IPC                                     │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                           CORE SERVICES LAYER                                │
│                                    │                                         │
│  ┌─────────────────────────────────┴─────────────────────────────────────┐  │
│  │                      Python Core (openaxis)                            │  │
│  │                                                                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐   │  │
│  │  │                    COMPAS Framework                             │   │  │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐               │   │  │
│  │  │  │  compas    │  │ compas_fab │  │compas_slic │               │   │  │
│  │  │  │ (geometry) │  │ (robotics) │  │ (toolpath) │               │   │  │
│  │  │  └────────────┘  └────────────┘  └────────────┘               │   │  │
│  │  └────────────────────────────────────────────────────────────────┘   │  │
│  │                                                                        │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │  │ Process Plugins │  │ Slicing Engine  │  │ Config Management   │   │  │
│  │  │ ├─ WAAM        │  │ (ORNL Slicer 2) │  │                     │   │  │
│  │  │ ├─ Pellet      │  │                 │  │                     │   │  │
│  │  │ ├─ Milling     │  │                 │  │                     │   │  │
│  │  │ └─ Concrete    │  │                 │  │                     │   │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                        MOTION PLANNING LAYER                                 │
│                                    │                                         │
│  ┌─────────────────────────────────┴─────────────────────────────────────┐  │
│  │                         MoveIt2 / ROS2                                 │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐   │  │
│  │  │ Motion Planner │  │   Collision    │  │ Trajectory Execution   │   │  │
│  │  │  (OMPL, Pilz)  │  │   Detection    │  │                        │   │  │
│  │  └────────────────┘  └────────────────┘  └────────────────────────┘   │  │
│  │                                                                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐   │  │
│  │  │              Inverse Kinematics / Forward Kinematics            │   │  │
│  │  └────────────────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                         SIMULATION LAYER                                     │
│                                    │                                         │
│  ┌─────────────────────────────────┴─────────────────────────────────────┐  │
│  │                      pybullet_industrial                               │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐   │  │
│  │  │    Extruder    │  │    Remover     │  │    Physics Engine      │   │  │
│  │  │  (Additive)    │  │ (Subtractive)  │  │                        │   │  │
│  │  └────────────────┘  └────────────────┘  └────────────────────────┘   │  │
│  │                                                                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐   │  │
│  │  │            Digital Twin / Process Validation                    │   │  │
│  │  └────────────────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                    HARDWARE ABSTRACTION LAYER                                │
│                                    │                                         │
│  ┌─────────────────────────────────┴─────────────────────────────────────┐  │
│  │                      Robot Raconteur Middleware                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐   │  │
│  │  │           Standardized Robot/Sensor Interface                   │   │  │
│  │  └────────────────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │   ABB    │ │   KUKA   │ │  FANUC   │ │ Motoman  │ │   Universal      │   │
│  │  Driver  │ │  Driver  │ │  Driver  │ │  Driver  │ │   Robots         │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
│                                    │                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ Fronius  │ │ Lincoln  │ │ Extruder │ │  FLIR    │ │   Laser          │   │
│  │ Welder   │ │ Electric │ │ Control  │ │  Camera  │ │   Scanner        │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Module Descriptions

### 1. Core Module (`src/core/`)

Central utilities and data structures shared across all components.

```python
src/core/
├── __init__.py
├── config.py          # Configuration management (YAML, JSON Schema)
├── logging.py         # Structured logging setup
├── exceptions.py      # Custom exception hierarchy
├── types.py           # Common type definitions
├── plugin.py          # Plugin base classes and registry
└── utils/
    ├── geometry.py    # Geometry utilities (COMPAS wrappers)
    ├── transforms.py  # Transformation utilities
    └── io.py          # File I/O utilities
```

**Key Classes:**
- `ConfigManager`: Loads/validates robot and process configs
- `PluginRegistry`: Discovers and loads process plugins
- `Project`: Represents a manufacturing project

### 2. Slicing Module (`src/slicing/`)

Toolpath generation. **Backend: compas_slicer** (ETH Zurich).

```python
src/slicing/
├── __init__.py
├── planar_slicer.py       # Delegates to compas_slicer PlanarSlicer
├── angled_slicer.py       # NotImplementedError — pending integration
├── radial_slicer.py       # NotImplementedError — pending integration
├── curve_slicer.py        # NotImplementedError — pending integration
├── revolved_slicer.py     # NotImplementedError — pending integration
├── slicer_factory.py      # Factory dispatcher
├── toolpath.py            # Data structures (no custom math)
├── gcode.py               # Vendor-specific G-code generation
├── infill_patterns.py     # NotImplementedError
├── contour_offset.py      # NotImplementedError
├── seam_control.py        # NotImplementedError
├── engage_disengage.py    # NotImplementedError
└── support_generation.py  # NotImplementedError
```

**Key Classes:**
- `PlanarSlicer`: Delegates to `compas_slicer.slicers.PlanarSlicer`
- `Toolpath`: Data structures only (no custom algorithms)
- Other slicers: Stubs raising NotImplementedError

**NOTE:** ORNL Slicer 2 is a C++ desktop app (not pip-installable).
compas_slicer is the Python-native COMPAS ecosystem alternative.
ORNL Slicer 2 integration planned for Phase 2 as subprocess wrapper.

### 3. Motion Module (`src/motion/`)

Robot kinematics and motion planning.
**Pending: compas_fab PyBullet backend** for IK.

```python
src/motion/
├── __init__.py
├── kinematics.py      # IK stubs — raises NotImplementedError (pending compas_fab)
├── planner.py         # CartesianPlanner/JointPlanner (depend on IK), TrajectoryOptimizer deleted
├── collision.py       # PyBullet collision checking
├── external_axes.py   # Data structures + NotImplementedError stubs
```

**Key Classes:**
- `IKSolver`: Stub — pending compas_fab AnalyticalInverseKinematics integration
- `JacobianIKSolver`: Stub — previous version ignored orientation
- `CartesianPlanner`: Frame interpolation (works once IK is integrated)
- `JointPlanner`: Linear joint interpolation (no custom math)
- `TrajectoryOptimizer`: Deleted (smooth_trajectory broke at wrap boundaries)

**NOTE:** MoveIt2 requires ROS2 and is planned for Phase 2 (Docker).
compas_fab with PyBullet backend is the Phase 1 IK solution.
`moveit_bridge.py` does NOT exist — it was a phantom file in previous docs.

### 4. Simulation Module (`src/simulation/`)

PyBullet-based simulation. **Integrating: pybullet_industrial** for manufacturing.

```python
src/simulation/
├── __init__.py
├── environment.py     # PyBullet environment wrapper + pybullet_industrial import
```

**Key Classes:**
- `SimulationEnvironment`: PyBullet world wrapper (URDF loading, collision shapes, mesh loading)
- `create_manufacturing_tool()`: pybullet_industrial integration point (not yet fully implemented)

**NOTE:** Files listed in previous docs (world.py, robot_sim.py, process_sim.py,
material.py, collision.py, visualization.py) do NOT exist. The actual simulation
is in `environment.py` only. Collision checking is in `motion/collision.py`.

### 5. Hardware Module (`src/hardware/`)

Real robot and equipment interfaces.

```python
src/hardware/
├── __init__.py
├── robot_driver.py    # Abstract robot driver
├── sensor.py          # Abstract sensor interface
├── process_equip.py   # Process equipment interface
├── drivers/
│   ├── abb.py         # ABB driver (via Robot Raconteur)
│   ├── kuka.py        # KUKA driver
│   ├── fanuc.py       # Fanuc driver
│   └── motoman.py     # Yaskawa/Motoman driver
├── sensors/
│   ├── flir.py        # FLIR thermal camera
│   ├── scanner.py     # Laser scanner
│   └── force.py       # Force/torque sensor
└── equipment/
    ├── fronius.py     # Fronius welder
    ├── extruder.py    # Pellet extruder
    └── spindle.py     # Milling spindle
```

**Key Classes:**
- `RobotDriver`: Abstract interface for robot control
- `Sensor`: Abstract sensor interface
- `ProcessEquipment`: Abstract equipment interface

### 6. UI Module (`src/ui/`)

Electron/React desktop application.

```
src/ui/
├── electron/
│   ├── main.ts        # Electron main process
│   ├── preload.ts     # Preload script
│   └── ipc.ts         # IPC handlers
├── src/
│   ├── App.tsx        # React root
│   ├── components/
│   │   ├── Viewport3D.tsx
│   │   ├── ProjectPanel.tsx
│   │   ├── ToolpathEditor.tsx
│   │   └── MonitoringDashboard.tsx
│   ├── hooks/
│   ├── store/         # Zustand state
│   └── utils/
└── package.json
```

## Data Flow

### 1. CAD to Toolpath

```
STL/STEP File
     │
     ▼
┌─────────────┐
│  Import     │ (trimesh, OCC)
└─────────────┘
     │
     ▼
┌─────────────┐
│  COMPAS     │ (Mesh/Brep)
│  Geometry   │
└─────────────┘
     │
     ▼
┌─────────────┐
│  Slicing    │ (ORNL Slicer 2)
│  Engine     │
└─────────────┘
     │
     ▼
┌─────────────┐
│  Toolpath   │ (OpenAxis format)
│  Object     │
└─────────────┘
```

### 2. Toolpath to Robot Motion

```
Toolpath
     │
     ▼
┌─────────────┐
│  Cartesian  │ (TCP poses)
│  Path       │
└─────────────┘
     │
     ▼
┌─────────────┐
│  MoveIt2    │ (IK, collision check)
│  Planning   │
└─────────────┘
     │
     ▼
┌─────────────┐
│  Joint      │ (time-parameterized)
│  Trajectory │
└─────────────┘
     │
     ▼
┌─────────────────────────────┐
│      Robot Raconteur        │
│  ┌─────────┐  ┌─────────┐   │
│  │Simulated│  │  Real   │   │
│  │ Robot   │  │ Robot   │   │
│  └─────────┘  └─────────┘   │
└─────────────────────────────┘
```

## Communication Protocols

### Internal (Python ↔ UI)
- **Protocol:** JSON-RPC over IPC (Electron)
- **Events:** WebSocket for real-time updates

### ROS2 Communication
- **Topics:** Joint states, robot status
- **Services:** Motion planning requests
- **Actions:** Trajectory execution

### Robot Raconteur
- **Transport:** TCP, local pipe
- **Discovery:** mDNS-SD
- **Data:** Protobuf-like serialization

## Configuration Schema

### Robot Configuration (`config/robots/`)

```yaml
# config/robots/abb_irb6700.yaml
robot:
  name: "ABB IRB 6700-200/2.60"
  manufacturer: "ABB"
  type: "industrial_arm"
  urdf: "urdf/abb_irb6700.urdf"
  
kinematics:
  type: "6dof"
  base_frame: "base_link"
  tool_frame: "tool0"
  
limits:
  joints:
    - name: "joint_1"
      lower: -170.0
      upper: 170.0
      velocity: 100.0
      acceleration: 50.0
  # ... more joints

communication:
  driver: "robot_raconteur"
  address: "192.168.1.100"
  port: 80
```

### Process Configuration (`config/processes/`)

```yaml
# config/processes/waam_steel.yaml
process:
  name: "Steel WAAM"
  type: "waam"
  
parameters:
  wire_feed_rate: 8.0  # m/min
  travel_speed: 10.0   # mm/s
  voltage: 22.0        # V
  current: 180.0       # A
  
slicing:
  layer_height: 2.5    # mm
  bead_width: 6.0      # mm
  infill_pattern: "zigzag"
  overlap: 0.3         # percentage
  
equipment:
  welder: "fronius_tps500i"
  wire: "er70s-6"
  wire_diameter: 1.2   # mm
  gas: "ar_co2_mix"
  gas_flow: 18.0       # L/min
```

## Extension Points

### Adding a New Process

1. Create plugin in `src/slicing/processes/`
2. Implement `Process` interface
3. Register in `plugin.py`
4. Add configuration schema
5. Implement process-specific slicing

### Adding a New Robot

1. Create URDF model
2. Create configuration YAML
3. Implement driver if needed (Robot Raconteur)
4. Add MoveIt2 configuration
5. Test with simulation

### Adding a New Sensor

1. Implement `Sensor` interface
2. Create Robot Raconteur service definition
3. Add visualization component
4. Integrate with monitoring dashboard
