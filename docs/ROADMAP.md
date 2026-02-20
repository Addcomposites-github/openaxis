# OpenAxis Development Roadmap

## Vision

Build an industry-ready, open-source robotic hybrid manufacturing platform that rivals commercial solutions like Adaxis AdaOne, using proven open-source components.

---

## Current Status Summary (as of 2026-02-20)

| Phase | Status |
|-------|--------|
| Phase 1 — Foundation | ✅ Complete |
| Phase 2 — Motion Planning & Multi-Process | 🔜 Not started |
| Phase 3 — Production UI & Monitoring | 🟡 Partial (~40%) |
| Phase 4 — Industrial Hardening | 🔜 Not started |

**What works end-to-end right now:** Import STL → Slice → Solve IK → Preview in 3D → Export RAPID/KRL/G-code/Fanuc.

**Known gaps:** Simulation is kinematic replay (not physics), monitoring shows placeholder data, non-planar slicers raise NotImplementedError, no hardware drivers yet.

---

## Phase 1: Foundation ✅ COMPLETE

### Objective
Establish core architecture and demonstrate end-to-end WAAM workflow.

### Milestones

#### 1.1 Project Setup
- [x] Repository structure with proper packaging
- [x] CI/CD pipeline (GitHub Actions)
- [x] Development environment (conda)
- [x] Contribution guidelines

#### 1.2 Core Framework
- [x] Configuration management system
- [x] Plugin architecture for processes (WAAM, Pellet, Milling)
- [x] Logging framework (structlog)
- [x] Error handling patterns
- [ ] Basic CLI interface — not yet, UI only

#### 1.3 COMPAS Integration
- [x] Geometry data structures (trimesh + COMPAS)
- [x] Robot model loading (URDF parsing via compas_robots)
- [x] Forward/inverse kinematics (roboticstoolbox-python + compas_fab PyBullet backend)
- [x] compas_fab backend setup

#### 1.4 ORNL Slicer 2 Integration
- [x] Subprocess wrapper for Slicer 2 (`src/openaxis/slicing/ornl_slicer.py`)
- [x] STL/STEP import pipeline
- [x] Basic planar slicing
- [x] G-code generation for WAAM
- [ ] Toolpath visualization

#### 1.5 Simulation Environment
- [x] pybullet_industrial integration (PyBullet environment + tool creation)
- [x] Robot visualization (Three.js kinematic replay in UI)
- [ ] Material deposition simulation — PyBullet code exists but not wired to UI (Phase 3)
- [ ] Collision detection — not active

### Deliverables — Achieved
- Desktop app: STL → Slice → IK → 3D preview → Export robot code
- 4 post-processors: RAPID, KRL, Fanuc TP, G-code
- 331 automated tests passing
- ABB IRB 6700 fully configured (URDF + IK)

---

## Phase 2: Motion Planning & Advanced Slicing 🔜 NOT STARTED

### Objective
Production-grade motion planning with ROS2/MoveIt2, non-planar slicing, external axes.

### Milestones

#### 2.1 MoveIt2 Integration
- [ ] ROS2 Humble workspace setup (requires Docker)
- [ ] MoveIt2 configuration generator
- [ ] Cartesian path planning with trajectory optimization (ruckig/topp-ra)
- [ ] compas_fab ↔ MoveIt2 bridge

#### 2.2 External Axes Support
- [ ] Positioner (2-axis) coordinated motion
- [ ] Linear track modeling
- [ ] Multi-group trajectory synchronization

#### 2.3 Non-Planar Slicing
- [ ] Angled slicer (currently raises NotImplementedError)
- [ ] Radial slicer (currently raises NotImplementedError)
- [ ] Curve slicer (currently raises NotImplementedError)
- [ ] 5-axis milling (needs Noether/ROS-Industrial — OpenCAMLib is 3-axis only)

#### 2.4 Process Sequencing
- [ ] Multi-process job definition (additive → subtractive workflow)
- [ ] Tool change handling
- [ ] Process parameter handoff

### Deliverables
- Support for 3 processes: WAAM, Pellet, Milling
- External axis coordination
- ROS2/MoveIt2 motion planning
- Process sequencing demo

### Additional Dependencies
```
# ROS2 packages (via rosdep)
moveit
ros2_control
robot_state_publisher
joint_state_publisher
```

---

## Phase 3: Production UI & Monitoring 🟡 PARTIAL (~40%)

### Objective
Full real-time monitoring, physics simulation wired to UI, production-ready application.

### Milestones

#### 3.1 Desktop Application Shell
- [x] Electron + React setup (Electron 28, React 18)
- [x] Python backend communication (REST API over localhost)
- [x] Theme and layout system (Tailwind CSS)
- [x] State management (Zustand)

#### 3.2 3D Visualization
- [x] Three.js scene setup
- [x] Robot model rendering (ABB IRB 6700)
- [x] Toolpath visualization (layer-by-layer)
- [x] Interactive camera controls
- [x] Kinematic trajectory playback (robot follows waypoints)
- [ ] True physics simulation — PyBullet code exists but not connected to UI

#### 3.3 Project Management
- [x] Part import (STL, STEP, 3MF via trimesh)
- [x] Process configuration UI (slicing parameters panel)
- [x] Robot cell configuration UI (position, orientation)
- [ ] Project create/load/save — not yet

#### 3.4 Toolpath Editor
- [x] Toolpath visualization
- [ ] Interactive toolpath modification — not yet
- [ ] Collision checking UI — not yet (backend check exists but returns "Not Active")

#### 3.5 Monitoring Dashboard
- [x] Dashboard UI exists (Recharts panels)
- [ ] Real-time robot state from hardware — placeholder data only
- [ ] Real process parameter monitoring (temp, flow, pressure) — shows fake numbers
- [ ] Sensor data — not connected
- [ ] Data logging — not yet

---

## Phase 4: Industrial Hardening 🔜 NOT STARTED

### Objective
Production-ready reliability, multi-vendor robot support, and real hardware drivers.

### Milestones

#### 4.1 Robot Raconteur Integration (Week 1-4)
- [ ] Hardware abstraction layer
- [ ] ABB driver integration
- [ ] KUKA driver integration
- [ ] Fanuc driver integration
- [ ] Yaskawa/Motoman driver integration

#### 4.2 Sensor Integration (Week 3-6)
- [ ] Thermal camera (FLIR)
- [ ] Laser scanner
- [ ] Force/torque sensor
- [ ] Generic sensor plugin API

#### 4.3 Process Control (Week 4-8)
- [ ] Welding power source integration (Fronius)
- [ ] Extruder control interface
- [ ] Spindle control interface
- [ ] Adaptive process feedback

#### 4.4 Error Handling & Recovery (Week 6-10)
- [ ] Graceful error handling
- [ ] Emergency stop integration
- [ ] Job pause/resume
- [ ] Automatic recovery procedures

#### 4.5 Deployment & Documentation (Week 8-12)
- [ ] Installer packages (Windows, Linux)
- [ ] Docker deployment option
- [ ] Comprehensive user manual
- [ ] API documentation
- [ ] Tutorial videos

### Deliverables
- Multi-vendor robot support
- Production-grade reliability
- Complete documentation
- Installer packages

---

## Future Phases (Post v1.0)

### Phase 5: Advanced Features
- AI-enhanced path planning
- Digital twin with thermal simulation
- Cloud deployment option
- Multi-robot coordination
- Wire Laser AM support

### Phase 6: Enterprise Features
- User authentication/authorization
- Audit logging
- ERP integration
- MES integration
- Advanced analytics

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Test Coverage | >80% |
| Build Time | <5 min |
| Startup Time | <10 sec |
| Supported Robots | 4+ brands |
| Processes | 5+ types |
| Documentation | 100% API coverage |

---

## Resource Requirements

### Team (Ideal)
- 2 Robotics Engineers
- 2 Software Engineers
- 1 Manufacturing Engineer
- 0.5 DevOps Engineer

### Infrastructure
- Development machines with GPU
- Robot cell for testing (optional initially)
- CI/CD runners
- Documentation hosting

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| ORNL Slicer 2 integration complexity | Start with Python subprocess wrapper, refine later |
| MoveIt2 learning curve | Leverage compas_fab abstraction layer |
| Robot vendor lock-in | Robot Raconteur abstraction from start |
| UI performance with large toolpaths | Web Worker + progressive loading |
| Scope creep | Strict phase gates, MVP focus |

---

## Getting Started

1. Clone repository
2. Run `./scripts/setup_dev.sh`
3. Activate environment: `conda activate openaxis`
4. Run tests: `pytest tests/`
5. Start with Phase 1.1 tasks

See `docs/guides/contributing.md` for contribution guidelines.
