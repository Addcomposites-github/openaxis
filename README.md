# OpenAxis

**Open-Source Robotic Manufacturing Software**

[![CI](https://github.com/openaxis/openaxis/workflows/CI/badge.svg)](https://github.com/openaxis/openaxis/actions)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

OpenAxis is a free, open-source alternative to commercial robotic manufacturing software (like Adaxis AdaOne). It takes a 3D design file, figures out how a robot arm should move to manufacture it, shows you a 3D preview, and generates the code to run on a real robot.

---

## What It Does

```
📁 Import 3D File  →  ✂️ Slice into Layers  →  🦾 Solve Robot Motion  →  👀 Preview  →  📤 Export Robot Code
    (STL/STEP)           (toolpath)              (inverse kinematics)      (3D viewer)     (RAPID/KRL/G-code)
```

**Three manufacturing processes are supported:**

| Process | What it is | Use case |
|---------|-----------|----------|
| 🔥 **WAAM** | Wire Arc Additive Manufacturing | Metal 3D printing via arc welding |
| 🧴 **Pellet Extrusion** | Large-scale plastic 3D printing | Composite/polymer parts |
| 🪚 **Milling** | Robotic CNC machining | Subtractive finishing |

---

## What Works Today

| Feature | Status |
|---------|--------|
| Import STL/STEP/3MF files | ✅ Working |
| View 3D model in desktop app | ✅ Working |
| Planar slicing (layer-by-layer toolpath) | ✅ Working (needs ORNL Slicer 2 binary) |
| Milling toolpath generation | ✅ Working (OpenCAMLib) |
| Inverse kinematics (robot joint angles) | ✅ Working (~25ms per point) |
| 3D robot motion preview | ✅ Working (kinematic replay) |
| Export to ABB RAPID (.mod) | ✅ Working |
| Export to KUKA KRL (.src) | ✅ Working |
| Export to Fanuc TP (.ls) | ✅ Working |
| Export to G-code (.gcode) | ✅ Working |
| Automated test suite | ✅ 331 tests passing |

## What Is Not Ready Yet

| Feature | Status |
|---------|--------|
| Physics simulation | 🔜 Preview is kinematic replay only — no physics yet |
| Process monitoring (temp, flow, pressure) | 🔜 Dashboard shows placeholder data |
| Non-planar slicing (curved surfaces) | 🔜 Phase 2 — raises NotImplementedError |
| Collision detection | 🔜 Not active |
| KUKA / Fanuc / Yaskawa hardware drivers | 🔜 Phase 4 |
| Real-time hardware connection | 🔜 Phase 4 |

---

## Supported Robots

| Robot | Config file | IK | Post-processor |
|-------|-------------|-----|----------------|
| ABB IRB 6700-200/2.60 | `config/robots/abb_irb6700.yaml` | ✅ | ✅ RAPID |
| KUKA (any) | — | — | ✅ KRL output |
| Fanuc (any) | — | — | ✅ TP output |
| CNC Mills | — | — | ✅ G-code output |

> KUKA and Fanuc post-processors generate correct robot code, but IK and simulation use the ABB model. Full multi-robot IK support is Phase 4.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- [Conda](https://docs.conda.io/en/latest/miniconda.html)
- Git

### Install & Run

```bash
# 1. Clone
git clone https://github.com/openaxis/openaxis.git
cd openaxis

# 2. Set up Python environment
conda create -n openaxis python=3.11
conda activate openaxis
pip install -e .

# 3. Run tests to verify
python -m pytest tests/unit -v

# 4. Start the desktop app
cd src/ui
npm install
npm run dev
```

### For slicing to work (optional)

Download and install [ORNL Slicer 2](https://github.com/ORNLSlicer/Slicer-2) — it is a C++ desktop application, not a Python package. The wrapper in `src/openaxis/slicing/ornl_slicer.py` will call it as a subprocess.

---

## Architecture

```
openaxis/
├── src/
│   ├── backend/        # Python FastAPI server — 50+ API endpoints
│   ├── openaxis/       # Core manufacturing library
│   │   ├── slicing/    # Toolpath generation (ORNL Slicer 2, OpenCAMLib)
│   │   ├── motion/     # Inverse kinematics, path planning
│   │   ├── simulation/ # PyBullet environment (not yet wired to UI)
│   │   ├── processes/  # WAAM, Pellet, Milling plugin definitions
│   │   └── postprocessor/ # Robot code generation (RAPID, KRL, Fanuc, G-code)
│   └── ui/             # Electron + React + Three.js desktop app
├── config/             # Robot URDF + YAML configs, tool definitions
├── tests/              # 331 automated tests
└── docs/               # Architecture, integration status, roadmap
```

**Technology stack:**

| Layer | Technology |
|-------|-----------|
| Desktop app | Electron 28 + React 18 + Three.js |
| Backend server | Python + FastAPI |
| Robotics / IK | roboticstoolbox-python (Peter Corke), compas_fab, PyBullet |
| Milling toolpaths | OpenCAMLib |
| Slicing | ORNL Slicer 2 (subprocess) |
| Geometry | trimesh, COMPAS (ETH Zurich) |

---

## Development Roadmap

| Phase | What | Status |
|-------|------|--------|
| **Phase 1** | Core framework, IK, slicing, export, desktop UI | **Done** (current state) |
| **Phase 2** | MoveIt2 motion planning, non-planar slicing, external axes | Not started |
| **Phase 3** | Real process monitoring, physics simulation, production UI | Partial |
| **Phase 4** | Hardware drivers (Robot Raconteur), KUKA/Fanuc/Yaskawa support | Not started |

See [docs/ROADMAP.md](docs/ROADMAP.md) for detailed milestones.
See [docs/INTEGRATION_STATUS.md](docs/INTEGRATION_STATUS.md) for what is integrated and what is planned.

---

## Development

### Running Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# With coverage report
pytest tests/unit --cov=src/openaxis --cov-report=term-missing
```

### Code Quality

```bash
black src/ tests/          # Format
isort src/ tests/          # Sort imports
flake8 src/ tests/         # Lint
mypy src/                  # Type check
```

### CI Pipeline

Every push runs:
- Code style (black, isort, flake8)
- Type checking (mypy)
- Unit + integration tests on Python 3.10, 3.11, 3.12
- UI build and type check
- Security audit (pip-audit, npm audit)
- Package build validation

---

## Built On

OpenAxis uses proven open-source libraries:

- [COMPAS](https://compas.dev/) — ETH Zurich Block Research Group (geometry framework)
- [roboticstoolbox-python](https://github.com/petercorke/robotics-toolbox-python) — Peter Corke (IK solver)
- [ORNL Slicer 2](https://github.com/ORNLSlicer/Slicer-2) — Oak Ridge National Laboratory (additive slicing)
- [OpenCAMLib](https://github.com/aewallin/opencamlib) — Anders Wallin (milling toolpaths)
- [pybullet_industrial](https://github.com/WBK-Robotics/pybullet_industrial) — KIT WBK-Robotics (manufacturing simulation)
- [MoveIt2](https://moveit.picknik.ai/) — PickNik Robotics (motion planning, Phase 2)
- [Robot Raconteur](https://robotraconteur.github.io/) — Wason Technology (hardware abstraction, Phase 4)

---

## Contributing

Contributions welcome. Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

- Report bugs: [GitHub Issues](https://github.com/openaxis/openaxis/issues)
- Discuss ideas: [GitHub Discussions](https://github.com/openaxis/openaxis/discussions)

## License

[Apache License 2.0](LICENSE)
