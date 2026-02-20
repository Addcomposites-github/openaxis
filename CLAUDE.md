# OpenAxis - Open-Source Robotic Hybrid Manufacturing Platform

## Project Overview

OpenAxis is an industry-ready, open-source alternative to Adaxis AdaOne for robotic hybrid manufacturing. It combines additive manufacturing (WAAM, pellet extrusion, concrete), subtractive manufacturing (milling), and scanning into a unified software platform.

**Target:** Production-quality software for multi-axis robotic manufacturing with full process control.

## Tech Stack

- **Language:** Python 3.10+ (core), TypeScript (UI)
- **Core Framework:** COMPAS ecosystem (compas, compas_fab) — Integrated
- **Slicing:** compas_slicer — Integrating (planar_slicer delegates to compas_slicer; other slicers raise NotImplementedError)
- **IK / Motion Planning:** compas_fab with PyBullet backend — Integrating (IK solver stubs raise NotImplementedError pending compas_fab backend)
- **Simulation:** PyBullet (base) + pybullet_industrial (manufacturing) — pybullet_industrial imported, not yet fully integrated
- **Hardware Abstraction:** Robot Raconteur — NOT integrated (Phase 4)
- **Production Motion Planning:** MoveIt2 via ROS2 Humble — NOT integrated (Phase 2, requires Docker)
- **Production Slicing:** ORNL Slicer 2 — NOT integrated (C++ desktop app, Phase 2 subprocess wrapper)
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
│   ├── slicing/        # Toolpath generation (compas_slicer backend, others NotImplementedError)
│   ├── motion/         # Motion planning (IK/planner stubs pending compas_fab integration)
│   ├── simulation/     # PyBullet environment (pybullet_industrial integration pending)
│   ├── hardware/       # Robot drivers, sensors (stubs — Robot Raconteur Phase 4)
│   └── ui/             # Electron/React frontend
├── docs/               # Architecture, API, guides
├── tests/              # Unit, integration, e2e tests
├── config/             # Robot configs, process parameters
└── scripts/            # Dev utilities, setup scripts
```

## Key Design Decisions

1. **Plugin Architecture:** Each process type (WAAM, pellet, milling) is a plugin
2. **Hardware Abstraction:** Robot Raconteur provides vendor-agnostic hardware layer (Phase 4)
3. **IK/Motion Planning:** compas_fab with PyBullet backend (Phase 1); MoveIt2 via ROS2 for production (Phase 2)
4. **Modular Slicing:** compas_slicer for Python-native slicing; ORNL Slicer 2 as production slicer (Phase 2 subprocess)
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

## CRITICAL: No Ungrounded Custom Implementations

When a library integration is specified in the architecture:
1. INTEGRATE the actual library, or
2. Find a PROVEN alternative (pip-installable, research-backed, actively maintained), or
3. STOP and report that the feature cannot be implemented yet
4. NEVER silently substitute custom code

All mathematical algorithms MUST either:
- Call a proven library function (cite the library and function), or
- Cite the specific research paper/textbook/standard the algorithm comes from
- Be explicitly marked as "UNVALIDATED — needs research citation"

LLM-generated math without citations is NOT acceptable. No new math needs to
be invented — proven libraries exist for robotics, slicing, IK, and physics.

If a specified library cannot be pip-installed or integrated:
- Document WHY it can't be integrated (e.g., "C++ desktop app, not a Python library")
- Find a proven pip-installable alternative from the same ecosystem
- If no alternative exists, raise NotImplementedError with a clear message

## CRITICAL: No Ungrounded Tests

A test is only meaningful if its expected outputs were verified by something
other than the LLM that wrote the code being tested.

**NEVER write tests where:**
- The LLM generated both the code AND the expected values
- Expected outputs come from running the code and accepting what it produced
- A trivial geometry (cube, single line) is used to avoid testing real failure modes
- The test passes by checking for zeros or empty lists (that is checking for a stub, not behaviour)

**Tests are only acceptable when the expected values come from:**
1. **Physics-verified results** — output from a real robot run, a real print, measured coordinates
2. **Independently published data** — test fixtures from proven open-source slicers
   (CuraEngine: https://github.com/Ultimaker/CuraEngine/tree/main/tests,
    PrusaSlicer: https://github.com/prusa3d/PrusaSlicer/tree/master/tests/data,
    SlicerTestModels: https://github.com/Ghostkeeper/SlicerTestModels)
3. **Analytically derived values from established standards** — not LLM arithmetic,
   but values you could look up in a textbook or standard (e.g., DH parameters,
   robot joint limits from the manufacturer datasheet)
4. **A human expert who has run the workflow and recorded the real output**

**The cube test anti-pattern:** Writing a test that slices a cube and checks
"layer count = height / layer_height" is circular — an LLM can make that pass
trivially without the slicer doing any real work. Real slicers are tested on
geometries that actually stress them: thin walls, overhangs, non-manifold meshes,
curved surfaces. The cube is the case no slicer ever fails on and therefore
proves nothing about correctness.

**The right question before writing any test:** "Would this test catch a bug that
a real user would experience?" If the answer is no, do not write it.

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
