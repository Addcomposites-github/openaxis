# OpenAxis - Open-Source Robotic Hybrid Manufacturing Platform

## Project Overview

OpenAxis is an industry-ready, open-source alternative to Adaxis AdaOne for robotic hybrid manufacturing. It combines additive manufacturing (WAAM, pellet extrusion, concrete), subtractive manufacturing (milling), and scanning into a unified software platform.

**Target:** Production-quality software for multi-axis robotic manufacturing with full process control.

## Tech Stack

- **Language:** Python 3.10+ (core), TypeScript (UI)
- **Core Framework:** COMPAS ecosystem (compas, compas_fab, compas_slicer)
- **Motion Planning:** MoveIt2 via ROS2 Humble
- **Simulation:** pybullet_industrial
- **Slicing:** ORNL Slicer 2 integration
- **Hardware Abstraction:** Robot Raconteur
- **UI:** Electron + React + Three.js

## Commands

```bash
# Development
python -m pytest tests/                    # Run all tests
python -m pytest tests/ -k "unit"          # Run unit tests only
python -m pytest tests/ -k "integration"   # Run integration tests
python scripts/lint.py                     # Run linting
python scripts/typecheck.py                # Run type checking

# Environment
conda activate openaxis                    # Activate conda environment
./scripts/setup_dev.sh                     # Setup development environment
./scripts/setup_ros2.sh                    # Setup ROS2 workspace

# Build
python -m build                            # Build package
python -m pip install -e .                 # Install in editable mode

# Docker (for ROS2 components)
docker compose -f docker/docker-compose.yml up   # Start full stack
docker compose -f docker/docker-compose.yml up simulation  # Simulation only
```

## Architecture

```
openaxis/
├── src/
│   ├── core/           # Core data structures, utilities, config
│   ├── slicing/        # Toolpath generation (ORNL Slicer 2, custom)
│   ├── motion/         # Motion planning (MoveIt2, IK, trajectory)
│   ├── simulation/     # Digital twin (pybullet_industrial)
│   ├── hardware/       # Robot drivers, sensors (Robot Raconteur)
│   └── ui/             # Electron/React frontend
├── docs/               # Architecture, API, guides
├── tests/              # Unit, integration, e2e tests
├── config/             # Robot configs, process parameters
└── scripts/            # Dev utilities, setup scripts
```

## Key Design Decisions

1. **Plugin Architecture:** Each process type (WAAM, pellet, milling) is a plugin
2. **Hardware Abstraction:** Robot Raconteur provides vendor-agnostic hardware layer
3. **ROS2 for Motion:** MoveIt2 handles all motion planning via ROS2
4. **Modular Slicing:** ORNL Slicer 2 as primary, custom slicers as plugins
5. **Offline-First:** All simulation/planning works without hardware connected

## Development Phases

See @docs/ROADMAP.md for detailed phase breakdown:
- **Phase 1:** Core framework + single-process demo (WAAM)
- **Phase 2:** Multi-process + external axes
- **Phase 3:** Production UI + monitoring
- **Phase 4:** Industrial hardening

## Code Patterns

- Use type hints everywhere
- Async/await for hardware communication
- Dataclasses for configuration objects
- Factory pattern for process/robot instantiation
- Follow COMPAS conventions for geometry operations

## Testing Strategy

- Unit tests: `tests/unit/` - Pure logic, no hardware
- Integration: `tests/integration/` - With simulation
- E2E: `tests/e2e/` - Full stack with mock hardware
- Hardware: `tests/hardware/` - Requires physical setup (manual)

## Important Notes

- NEVER commit credentials or API keys
- Robot configs in `config/robots/` follow URDF + custom YAML schema
- Process parameters in `config/processes/` are JSON Schema validated
- See `docs/architecture/hardware-abstraction.md` before adding robot support
- All geometry uses COMPAS data structures (not raw numpy)

## External Documentation

- COMPAS: https://compas.dev/compas/latest/
- compas_fab: https://gramaziokohler.github.io/compas_fab/
- ORNL Slicer 2: https://github.com/ORNLSlicer/Slicer-2
- MoveIt2: https://moveit.picknik.ai/main/index.html
- Robot Raconteur: https://robotraconteur.github.io/robotraconteur/
- pybullet_industrial: https://pybullet-industrial.readthedocs.io/
