"""
Build the OpenAxis backend as a standalone executable using PyInstaller.

This script creates a frozen (standalone) version of the FastAPI backend
that can be bundled with the Electron app. The output goes to dist-backend/
and is picked up by electron-builder's extraResources config.

Usage::

    pip install pyinstaller
    python scripts/build_backend.py

Output::

    dist-backend/
    ├── openaxis-server.exe   (Windows)
    └── openaxis-server       (macOS/Linux)

The frozen backend includes:
- FastAPI server (uvicorn)
- All backend services (robot, geometry, toolpath, simulation, etc.)
- COMPAS ecosystem (compas, compas_fab)
- roboticstoolbox-python (IK solver)
- Config files (URDF, robot configs, process configs)
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
BACKEND_DIR = SRC_DIR / "backend"
SERVER_SCRIPT = BACKEND_DIR / "server.py"
CONFIG_DIR = PROJECT_ROOT / "config"
OUTPUT_DIR = PROJECT_ROOT / "dist-backend"


def build() -> None:
    """Run PyInstaller to freeze the backend server."""
    if not SERVER_SCRIPT.exists():
        print(f"Error: server.py not found at {SERVER_SCRIPT}")
        sys.exit(1)

    # PyInstaller arguments
    args = [
        sys.executable, "-m", "PyInstaller",
        str(SERVER_SCRIPT),
        "--name", "openaxis-server",
        "--onedir",
        "--noconfirm",
        "--clean",

        # Output directory
        "--distpath", str(OUTPUT_DIR),

        # Hidden imports that PyInstaller may not detect
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "structlog",
        "--hidden-import", "pydantic",
        "--hidden-import", "compas",
        "--hidden-import", "compas_fab",
        "--hidden-import", "trimesh",
        "--hidden-import", "numpy",
        "--hidden-import", "scipy",

        # Add source directories as data
        "--add-data", f"{SRC_DIR / 'openaxis'}{os.pathsep}openaxis",
        "--add-data", f"{SRC_DIR / 'backend'}{os.pathsep}backend",

        # Add config files
        "--add-data", f"{CONFIG_DIR}{os.pathsep}config",

        # Path includes
        "--paths", str(SRC_DIR),
    ]

    print(f"Building backend executable...")
    print(f"  Source: {SERVER_SCRIPT}")
    print(f"  Output: {OUTPUT_DIR}")
    print()

    result = subprocess.run(args, cwd=str(PROJECT_ROOT))

    if result.returncode == 0:
        print()
        print(f"Build successful! Output: {OUTPUT_DIR}")
        print()
        print("To bundle with Electron:")
        print("  cd src/ui && npm run build && npx electron-builder")
    else:
        print(f"Build failed with exit code {result.returncode}")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
