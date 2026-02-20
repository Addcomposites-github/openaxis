# OpenAxis Integration Status

Single source of truth for what is actually integrated, what is planned, and what has been deleted.

Last updated: 2026-02-20

---

## Library Integration Status

| Library | Spec Role | pyproject.toml | Actually Working | Notes |
|---------|-----------|---------------|-----------------|-------|
| compas 2.15.0 | Core geometry | `compas>=2.0` | **Yes** | Mesh, Frame, Transformation, Point, Vector |
| compas_fab 1.1.4 | IK / Motion | `compas_fab>=0.28` | **Yes** | IKSolver uses PyBulletClient backend; FK-IK roundtrip < 1mm error |
| compas_robots | Robot models | via compas_fab | **Yes** | URDF loading, joint info, FK |
| pybullet | Physics sim | `pybullet>=3.2` | **Yes** | Simulation environment, IK backend, collision detection |
| pybullet_industrial 1.0.4 | Mfg simulation | `pybullet-industrial>=1.0` | **Yes** | Extruder, MillingTool, Remover creation + robot coupling |
| opencamlib 2023.1.11 | Milling toolpaths | `opencamlib>=2023.1` | **Yes** | Waterline roughing + drop-cutter finishing, 4 cutter types |
| ORNL Slicer 2 v1.3.001 | Additive slicing | External binary | **Wrapper ready** | Subprocess wrapper + G-code parser written; requires binary install |
| trimesh | Mesh I/O | `trimesh>=4.0` | **Yes** | STL/OBJ loading, mesh conversion |
| scipy | Numerics | `scipy>=1.10` | **Yes** | SLERP rotation interpolation in planner |
| numpy | Arrays | `numpy>=1.24` | **Yes** | Standard numerical arrays |

### Dropped Libraries

| Library | Reason |
|---------|--------|
| compas_slicer | Requires `compas<2.0.0` and `numpy<=1.23.2` — incompatible with our stack |
| FullControl | Different paradigm (parametric G-code, not mesh-to-layer slicing) |

---

## Module Status

### Slicing (`src/openaxis/slicing/`)

| File | Status | Backend |
|------|--------|---------|
| `planar_slicer.py` | **Integrated** | Delegates to ORNL Slicer 2 via subprocess wrapper |
| `ornl_slicer.py` | **Integrated** | Subprocess wrapper + JSON config builder + G-code parser |
| `milling_toolpath.py` | **Integrated** | OpenCAMLib waterline (roughing) + drop-cutter (finishing) |
| `toolpath.py` | **Working** | Data structures (Toolpath, ToolpathSegment, ToolpathType) |
| `slicer_factory.py` | **Working** | Factory dispatcher |
| `gcode.py` | **Working** | Vendor-specific G-code output (Marlin, KUKA KRL, ABB RAPID) |
| `angled_slicer.py` | NotImplementedError | Phase 2 |
| `radial_slicer.py` | NotImplementedError | Phase 2 |
| `curve_slicer.py` | NotImplementedError | Phase 2 |
| `revolved_slicer.py` | NotImplementedError | Phase 2 |
| `infill_patterns.py` | NotImplementedError | Handled by ORNL Slicer 2 config |
| `contour_offset.py` | NotImplementedError | Handled by ORNL Slicer 2 config |
| `seam_control.py` | NotImplementedError | Handled by ORNL Slicer 2 config |
| `engage_disengage.py` | NotImplementedError | Phase 2 |
| `support_generation.py` | NotImplementedError | Handled by ORNL Slicer 2 config |

### Motion (`src/openaxis/motion/`)

| File | Status | Backend |
|------|--------|---------|
| `kinematics.py` | **Integrated** | compas_fab PyBulletClient IK; 0.000mm FK-IK roundtrip with seed |
| `planner.py` | **Partial** | CartesianPlanner works (SLERP + IK at each waypoint); TrajectoryOptimizer is Phase 2 |
| `collision.py` | **Working** | PyBullet collision checking |
| `external_axes.py` | Data structures only | Pending compas_fab coordinated motion (Phase 2) |

### Processes (`src/openaxis/processes/`)

| File | Status | Notes |
|------|--------|-------|
| `base.py` | **Working** | Abstract base classes, ProcessType enum |
| `waam.py` | **Partial** | Parameters + validation work; physics formulas are Phase 2 |
| `pellet.py` | **Partial** | Parameters + validation work; physics formulas are Phase 2 |
| `milling.py` | **Partial** | Parameters + validation work; now has real milling toolpaths via OpenCAMLib |

### Simulation (`src/openaxis/simulation/`)

| File | Status | Backend |
|------|--------|---------|
| `environment.py` | **Integrated** | PyBullet environment + pybullet_industrial tool creation/coupling |

### Core (`src/openaxis/core/`)

| File | Status | Notes |
|------|--------|-------|
| `robot.py` | **Working** | RobotLoader, RobotInstance, KinematicsEngine (delegates IK to IKSolver) |
| `config.py` | **Working** | ConfigManager, RobotConfig, ProcessConfig |
| `geometry.py` | **Working** | GeometryLoader, BoundingBox, GeometryConverter |
| `project.py` | **Working** | Project management (create, save, load) |

### Frontend (`src/ui/`)

| File | Status | Notes |
|------|--------|-------|
| `analyticalIK.ts` | **Stub** | Returns unreachable until backend API endpoint wired |
| UI components | **Working** | React + Three.js renders; backend API for IK not yet wired |

---

## Test Results

```
286 unit tests passed, 45 integration tests passed (as of 2026-02-20)
Frontend: 110 passed, 13 failed (pre-existing analyticalIK stub failures — expected)
```

### Frontend failure note:
The 13 frontend failures are all in `analyticalIK.test.ts`. The client-side IK function was intentionally stubbed to force all IK through the backend API. These test failures are expected and document a known gap — not regressions.

---

## What Works End-to-End

- **IK solving**: Load ABB IRB6700 URDF → FK → target frame → IK → solution (< 1mm error)
- **Multiple IK solutions**: solve_multiple() finds distinct valid solutions with random seeds
- **Milling toolpaths**: Load STL → OpenCAMLib waterline roughing (Z-level contours) + drop-cutter finishing
- **Manufacturing tools**: Create Extruder/MillingTool/Remover in PyBullet → couple to robot → decouple
- **Slicing pipeline**: PlanarSlicer → ORNL Slicer 2 config → subprocess → G-code parse → Toolpath (when binary installed)
- **Project management**: Create → add parts → save → load → round-trip

## What Doesn't Work (Honest)

- **Slicing without ORNL binary**: PlanarSlicer raises ImportError if ORNL Slicer 2 not installed
- **IK for all poses**: PyBullet numerical IK is not globally convergent — near singularities may fail
- **Trajectory optimization**: Needs ruckig/toppra (Phase 2)
- **5-axis milling**: OpenCAMLib is 3-axis only; for 5-axis need Noether/ROS-Industrial (Phase 2)
- **Non-planar slicing**: Research-level, not available in any open-source slicer
- **External axes**: Data structures exist, coordinated motion not implemented (Phase 2)
- **Frontend IK**: Backend API endpoint not wired to new IK solver yet
- **Full simulation loop**: IK + toolpath + tool into a single automated pipeline not yet orchestrated

---

## What Was Deleted and Why

See [UNGROUNDED_CODE.md](UNGROUNDED_CODE.md) for the full registry.

---

## Phase Dependencies

| Feature | Requires | Status |
|---------|----------|--------|
| IK solving | compas_fab PyBullet backend | **Done** |
| Milling toolpaths | OpenCAMLib | **Done** |
| Manufacturing tools | pybullet_industrial | **Done** |
| Planar slicing | ORNL Slicer 2 subprocess wrapper | **Done** (needs binary) |
| Cartesian planning | IK solving (done) + trajectory opt | Partial |
| Trajectory optimization | ruckig or topp-ra | Phase 2 |
| MoveIt2 motion | ROS2 Docker container | Phase 2 |
| External axes | compas_fab coordinated motion | Phase 2 |
| 5-axis milling | Noether / ROS-Industrial | Phase 2 |
| Hardware drivers | Robot Raconteur | Phase 4 |
