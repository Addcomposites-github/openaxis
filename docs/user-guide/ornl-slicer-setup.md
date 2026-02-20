# ORNL Slicer 2 Setup

OpenAxis uses [ORNL Slicer 2](https://github.com/ORNLSlicer/Slicer-2) as its production slicing engine. ORNL Slicer 2 is a C++ desktop application developed at Oak Ridge National Laboratory, used by 50+ equipment manufacturers for FDM, WAAM, LFAM, MFAM, and concrete 3D printing.

## Why ORNL Slicer 2?

- Production-grade, used in real manufacturing environments
- Supports multi-axis toolpath generation
- Handles large-scale parts (WAAM, concrete)
- Active development with industry backing

## Installation

### Windows

1. Download the latest release from [GitHub Releases](https://github.com/ORNLSlicer/Slicer-2/releases).
2. Run the installer or extract the portable ZIP.
3. Note the installation path (e.g., `C:\Program Files\Slicer2\slicer2.exe`).

### macOS / Linux

1. Build from source following the [ORNL Slicer 2 build instructions](https://github.com/ORNLSlicer/Slicer-2#building-from-source).
2. Note the path to the built binary.

## Configuration

Set the `ORNL_SLICER2_PATH` environment variable to point to the Slicer 2 binary:

```bash
# Windows (PowerShell)
$env:ORNL_SLICER2_PATH = "C:\Program Files\Slicer2\slicer2.exe"

# macOS/Linux
export ORNL_SLICER2_PATH=/usr/local/bin/slicer2
```

To make this permanent, add it to your shell profile (`.bashrc`, `.zshrc`, or Windows environment variables).

## Verifying the Setup

```python
from openaxis.slicing.ornl_slicer import ORNLSlicer

if ORNLSlicer.is_available():
    print("ORNL Slicer 2 is ready!")
else:
    print("ORNL Slicer 2 not found. Check ORNL_SLICER2_PATH.")
```

## Without ORNL Slicer 2

If ORNL Slicer 2 is not installed, calling `PlanarSlicer.slice()` will raise an `ImportError` with installation instructions. The rest of OpenAxis (geometry, simulation, robot control, post-processing) works without it.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "ORNL Slicer 2 binary not found" | Set `ORNL_SLICER2_PATH` environment variable |
| Permission denied on Linux/macOS | Run `chmod +x /path/to/slicer2` |
| Slicing produces empty toolpath | Check that the STL file is valid (watertight mesh) |
| Slicer crashes on large files | Ensure sufficient RAM (8GB+ recommended) |
