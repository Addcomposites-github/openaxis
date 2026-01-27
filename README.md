# OpenAxis

**Open-Source Robotic Hybrid Manufacturing Platform**

[![CI](https://github.com/openaxis/openaxis/workflows/CI/badge.svg)](https://github.com/openaxis/openaxis/actions)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

OpenAxis is an industry-ready, open-source alternative to commercial robotic manufacturing software. It combines additive manufacturing (WAAM, pellet extrusion, concrete), subtractive manufacturing (milling), and 3D scanning into a unified platform.

## 🎯 Vision

Democratize robotic hybrid manufacturing by providing:
- **Multi-process support**: WAAM, pellet extrusion, milling, scanning
- **Multi-robot support**: ABB, KUKA, FANUC, Yaskawa/Motoman
- **Complete workflow**: CAD → Toolpath → Simulation → Production
- **On-premise deployment**: Full data sovereignty

## 🏗️ Architecture

OpenAxis is built on proven open-source foundations:

| Component | Technology |
|-----------|------------|
| Robotic Framework | [COMPAS](https://compas.dev/) (ETH Zurich) |
| Slicing Engine | [ORNL Slicer 2](https://github.com/ORNLSlicer/Slicer-2) (Oak Ridge National Lab) |
| Motion Planning | [MoveIt2](https://moveit.picknik.ai/) (ROS2) |
| Simulation | [pybullet_industrial](https://github.com/WBK-Robotics/pybullet_industrial) (KIT) |
| Hardware Abstraction | [Robot Raconteur](https://robotraconteur.github.io/) |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ (for backend)
- Node.js 20+ (for desktop UI)
- [Conda](https://docs.conda.io/en/latest/miniconda.html) (recommended)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/openaxis/openaxis.git
cd openaxis

# Setup Python backend
conda create -n openaxis python=3.11
conda activate openaxis
pip install -e .

# Verify installation
python -m pytest tests/

# Setup Desktop UI (optional)
cd src/ui
npm install
npm run dev  # Starts Electron app with Python backend
```

### Desktop Application

OpenAxis includes a modern desktop application built with Electron:

```bash
cd src/ui

# Development mode
npm run dev

# Build for production
npm run build
npm run build:electron
```

See [src/ui/README.md](src/ui/README.md) for detailed UI documentation.

## 📖 Documentation

- [Architecture Overview](docs/architecture/system-architecture.md)
- [Development Roadmap](docs/ROADMAP.md)
- [Contributing Guide](CONTRIBUTING.md)
- [API Reference](https://openaxis.github.io/openaxis/) (coming soon)

## 🛠️ Development

### Running Tests

```bash
# All unit tests
pytest tests/unit -v

# With coverage
pytest tests/unit --cov=src/openaxis --cov-report=term-missing

# Specific module
pytest tests/unit/core/test_config.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
flake8 src/ tests/

# Type check
mypy src/
```

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## 🗺️ Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Complete | Core framework + WAAM demo |
| Phase 2 | ✅ Complete | Multi-process + external axes |
| Phase 3 | ✅ Complete | Production UI + monitoring |
| Phase 4 | 📋 Next | Industrial hardening |

See [ROADMAP.md](docs/ROADMAP.md) for detailed milestones and [PHASE3_COMPLETE.md](docs/PHASE3_COMPLETE.md) for the latest completion status.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Ways to Contribute

- 🐛 Report bugs and issues
- 💡 Suggest features
- 📖 Improve documentation
- 🔧 Submit pull requests

## 📄 License

OpenAxis is licensed under the [Apache License 2.0](LICENSE).

## 🙏 Acknowledgments

OpenAxis builds upon the excellent work of:

- [COMPAS](https://compas.dev/) - ETH Zurich Block Research Group
- [ORNL Slicer 2](https://github.com/ORNLSlicer/Slicer-2) - Oak Ridge National Laboratory
- [MoveIt2](https://moveit.picknik.ai/) - PickNik Robotics & Community
- [Robot Raconteur](https://robotraconteur.github.io/) - Wason Technology
- [pybullet_industrial](https://github.com/WBK-Robotics/pybullet_industrial) - KIT WBK-Robotics
- [RPI WAAM Project](https://github.com/rpiRobotics/Welding_Motoman) - Rensselaer Polytechnic Institute

## 📞 Contact

- GitHub Issues: [Report a bug](https://github.com/openaxis/openaxis/issues)
- Discussions: [Join the conversation](https://github.com/openaxis/openaxis/discussions)
