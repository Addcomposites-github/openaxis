# Troubleshooting

## Installation Issues

### `pip install -e ".[dev]"` fails with compiler errors

Some dependencies (pybullet, opencamlib) require C++ compilation.

**Windows**: Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with "Desktop development with C++" workload.

**macOS**: Install Xcode Command Line Tools: `xcode-select --install`

**Linux**: Install build essentials: `sudo apt install build-essential python3-dev`

### `compas` or `compas_fab` import errors

Ensure you're using Python 3.10+:
```bash
python --version  # Should be 3.10, 3.11, or 3.12
```

If using conda, ensure the environment is activated: `conda activate openaxis`

### `npm ci` fails in `src/ui/`

Ensure Node.js 20+ is installed:
```bash
node --version  # Should be v20.x or later
```

Delete `node_modules` and retry:
```bash
cd src/ui
rm -rf node_modules package-lock.json
npm install
```

---

## Runtime Issues

### Backend won't start

**"Address already in use"**: Another process is using port 8000.
```bash
# Find and kill the process (Windows)
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# macOS/Linux
lsof -i :8000
kill <pid>
```

**Import errors**: Ensure the virtual environment is activated and all dependencies are installed.

### Frontend shows "Backend not reachable"

1. Check that the backend is running: `python src/backend/server.py`
2. Verify it's accessible: open `http://localhost:8000/api/health` in your browser
3. Check for CORS issues in the browser console

### IK solver returns all unreachable

- Verify the toolpath is within the robot's workspace (ABB IRB 6700 reach: ~2.6m)
- Check the TCP offset configuration in the Setup tab
- Try adjusting the work table position to bring the part closer to the robot

### Toolpath generation returns empty

- Ensure a geometry part is loaded and selected
- Check that slicing parameters are reasonable (layer height > 0, infill density > 0)
- If using ORNL Slicer 2, verify it's installed (see [ORNL Slicer Setup](ornl-slicer-setup.md))

### Simulation is choppy or slow

- Large toolpaths (>100K points) may cause performance issues
- Reduce the number of visible layers using the layer slider
- Close browser DevTools (they can slow down Three.js rendering)
- Ensure hardware acceleration is enabled in your browser

---

## Test Issues

### `pytest` shows DeprecationWarnings

These are filtered in `pytest.ini`. If you see new warnings, add them to the `filterwarnings` section:
```ini
filterwarnings =
    error
    ignore::UserWarning
    ignore::DeprecationWarning:pybullet.*
    ignore::DeprecationWarning:compas.*
    ignore::DeprecationWarning:fastapi.*
    ignore::DeprecationWarning:starlette.*
```

### Frontend tests fail with "Cannot find module"

Ensure you've installed dependencies: `cd src/ui && npm ci`

---

## Getting Help

- [GitHub Issues](https://github.com/openaxis/openaxis/issues)
- Check existing issues before filing a new one
- Include your Python version, OS, and the full error traceback
