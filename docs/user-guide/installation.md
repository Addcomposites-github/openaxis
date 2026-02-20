# Installation Guide

## Prerequisites

- **Python 3.10+** (3.11 recommended)
- **Node.js 20+** and npm
- **Git**

### Optional

- **ORNL Slicer 2** for production-grade slicing (see [ORNL Slicer Setup](ornl-slicer-setup.md))
- **conda** (recommended for managing Python environments)

---

## Quick Install (Development)

```bash
# Clone the repository
git clone https://github.com/openaxis/openaxis.git
cd openaxis

# Create and activate a Python environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install Python package in editable mode with dev dependencies
pip install -e ".[dev]"

# Install frontend dependencies
cd src/ui
npm ci
cd ../..
```

## Verify Installation

```bash
# Run backend tests
python -m pytest tests/unit/ -v

# Run frontend tests
cd src/ui && npx vitest run && cd ../..

# Start the backend server
python src/backend/server.py

# In another terminal, start the frontend dev server
cd src/ui && npm run dev
```

The UI should be available at `http://localhost:5173`.

---

## Conda Environment (Recommended)

```bash
conda create -n openaxis python=3.11
conda activate openaxis
pip install -e ".[dev]"
cd src/ui && npm ci && cd ../..
```

---

## Desktop Application (Electron)

For a native desktop experience:

```bash
# Build the frontend
cd src/ui
npm run build

# Run as Electron app (dev mode)
npm run dev
```

For distributable installers, see the [Packaging Guide](../PACKAGING.md).

---

## Troubleshooting

See [Troubleshooting](troubleshooting.md) for common installation issues.
