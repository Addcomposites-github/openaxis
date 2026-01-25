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

Toolpath generation for various manufacturing processes.

```python
src/slicing/
├── __init__.py
├── base.py            # Abstract Slicer base class
├── ornl_slicer.py     # ORNL Slicer 2 wrapper
├── compas_slicer.py   # compas_slicer integration
├── toolpath.py        # Toolpath data structures
├── infill/
│   ├── contour.py     # Contour/perimeter generation
│   ├── zigzag.py      # Linear infill
│   └── adaptive.py    # Adaptive infill strategies
└── strategies/
    ├── planar.py      # 2.5D planar slicing
    ├── nonplanar.py   # Curved layer slicing
    └── multiaxis.py   # Full multi-axis strategies
```

**Key Classes:**
- `Slicer`: Abstract base for all slicing implementations
- `ORNLSlicerWrapper`: Python interface to ORNL Slicer 2
- `Toolpath`: Sequence of `ToolpathSegment` objects
- `SlicingStrategy`: Configurable slicing approach

### 3. Motion Module (`src/motion/`)

Robot kinematics and motion planning.

```python
src/motion/
├── __init__.py
├── robot.py           # Robot model representation
├── kinematics.py      # FK/IK solvers
├── planner.py         # Motion planning interface
├── trajectory.py      # Trajectory representation
├── moveit_bridge.py   # MoveIt2 integration via ROS2
└── external_axes/
    ├── positioner.py  # 2-axis positioner
    ├── track.py       # Linear track
    └── turntable.py   # Rotary table
```

**Key Classes:**
- `Robot`: Robot model with joints, links, tool
- `MotionPlanner`: Abstract planner interface
- `MoveItPlanner`: MoveIt2 implementation
- `Trajectory`: Time-parameterized joint trajectory

### 4. Simulation Module (`src/simulation/`)

Digital twin and process simulation.

```python
src/simulation/
├── __init__.py
├── world.py           # Simulation world/scene
├── robot_sim.py       # Robot simulation
├── process_sim.py     # Process-specific simulation
├── material.py        # Material deposition/removal
├── collision.py       # Collision detection
└── visualization.py   # Rendering utilities
```

**Key Classes:**
- `SimulationWorld`: pybullet world wrapper
- `RobotSimulator`: Simulated robot controller
- `ProcessSimulator`: Abstract process simulation
- `MaterialSimulator`: Tracks material state

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
