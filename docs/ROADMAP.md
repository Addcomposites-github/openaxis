# OpenAxis Development Roadmap

## Vision

Build an industry-ready, open-source robotic hybrid manufacturing platform that rivals commercial solutions like Adaxis AdaOne, using proven open-source components.

---

## Phase 1: Foundation (Months 1-3)

### Objective
Establish core architecture and demonstrate end-to-end WAAM workflow.

### Milestones

#### 1.1 Project Setup (Week 1-2)
- [ ] Repository structure with proper packaging
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Development environment (conda + Docker)
- [ ] Documentation framework (MkDocs)
- [ ] Contribution guidelines

#### 1.2 Core Framework (Week 3-6)
- [ ] Configuration management system
- [ ] Plugin architecture for processes
- [ ] Logging and telemetry framework
- [ ] Error handling patterns
- [ ] Basic CLI interface

#### 1.3 COMPAS Integration (Week 4-8)
- [ ] Geometry data structures (mesh, brep handling)
- [ ] Robot model loading (URDF parsing)
- [ ] Basic forward/inverse kinematics
- [ ] compas_fab backend setup

#### 1.4 ORNL Slicer 2 Integration (Week 6-10)
- [ ] Python bindings/wrapper for Slicer 2
- [ ] STL/STEP import pipeline
- [ ] Basic planar slicing
- [ ] G-code generation for WAAM
- [ ] Toolpath visualization

#### 1.5 Simulation Environment (Week 8-12)
- [ ] pybullet_industrial integration
- [ ] Basic robot visualization
- [ ] Material deposition simulation
- [ ] Collision detection setup

### Deliverables
- Working CLI that takes STL → generates WAAM toolpath → simulates in pybullet
- Documentation: Architecture overview, setup guide
- Test coverage: >70% for core modules

### Dependencies to Install
```
compas>=2.0
compas_fab>=0.28
pybullet>=3.2
pybullet_industrial>=1.0
numpy
scipy
trimesh
python-fcl
```

---

## Phase 2: Multi-Process & Motion (Months 4-6)

### Objective
Add pellet extrusion, milling, and proper motion planning with external axes.

### Milestones

#### 2.1 MoveIt2 Integration (Week 1-4)
- [ ] ROS2 Humble workspace setup
- [ ] MoveIt2 configuration generator
- [ ] Cartesian path planning
- [ ] Joint trajectory execution
- [ ] compas_fab ↔ MoveIt2 bridge

#### 2.2 External Axes Support (Week 3-6)
- [ ] Positioner (2-axis) modeling
- [ ] Linear track modeling
- [ ] Coordinated motion planning
- [ ] Multi-group trajectory synchronization

#### 2.3 Pellet Extrusion Process (Week 4-8)
- [ ] Process plugin implementation
- [ ] Extrusion parameters (temp, flow, speed)
- [ ] Layer-by-layer toolpath generation
- [ ] Adaptive layer height support

#### 2.4 Milling Process (Week 6-10)
- [ ] Subtractive toolpath generation
- [ ] Tool library management
- [ ] Roughing/finishing strategies
- [ ] Force estimation (basic)

#### 2.5 Process Sequencing (Week 8-12)
- [ ] Multi-process job definition
- [ ] Additive → Subtractive workflow
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

## Phase 3: Production UI & Monitoring (Months 7-9)

### Objective
Create user-friendly interface with real-time monitoring capabilities.

### Milestones

#### 3.1 Desktop Application Shell (Week 1-3)
- [ ] Electron + React setup
- [ ] Python backend communication (IPC)
- [ ] Theme and layout system
- [ ] State management (Redux/Zustand)

#### 3.2 3D Visualization (Week 2-6)
- [ ] Three.js scene setup
- [ ] Robot model rendering
- [ ] Toolpath visualization
- [ ] Interactive camera controls
- [ ] Real-time simulation playback

#### 3.3 Project Management (Week 4-8)
- [ ] Project create/load/save
- [ ] Part import (STL, STEP, 3MF)
- [ ] Process configuration UI
- [ ] Robot cell configuration UI

#### 3.4 Toolpath Editor (Week 6-10)
- [ ] Interactive toolpath modification
- [ ] Region-based parameter editing
- [ ] Preview with collision checking
- [ ] Undo/redo system

#### 3.5 Monitoring Dashboard (Week 8-12)
- [ ] Real-time robot state display
- [ ] Process parameter monitoring
- [ ] Sensor data visualization
- [ ] Job progress tracking
- [ ] Data logging to file/database

### Deliverables
- Desktop application (Windows, Linux, macOS)
- Interactive 3D visualization
- Complete workflow UI
- Real-time monitoring

### UI Dependencies
```json
{
  "electron": "^28.0.0",
  "react": "^18.2.0",
  "three": "^0.160.0",
  "@react-three/fiber": "^8.15.0",
  "@react-three/drei": "^9.92.0",
  "zustand": "^4.4.0",
  "tailwindcss": "^3.4.0"
}
```

---

## Phase 4: Industrial Hardening (Months 10-12)

### Objective
Production-ready reliability, multi-vendor support, and deployment tools.

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
