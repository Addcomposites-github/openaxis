# Performance Benchmarks

## IK Solver Performance

The primary IK solver uses **roboticstoolbox-python** (Peter Corke), a production-grade DH-based solver running Levenberg-Marquardt optimization.

### Measured Performance (ABB IRB 6700)

| Waypoints | Time (s) | ms/point | Solver |
|-----------|----------|----------|--------|
| 100       | ~2.7     | ~27      | roboticstoolbox (ikine_LM) |
| 1,000     | ~24.8    | ~25      | roboticstoolbox (ikine_LM) |
| 10,000    | ~256     | ~26      | roboticstoolbox (ikine_LM) |

**Note**: Actual times vary by hardware. Measured on Windows 11 with Python 3.11. The Levenberg-Marquardt solver (`ikine_LM`) runs at approximately 25ms per waypoint. Each IK solution seeds the next for smooth joint trajectories. Performance scales linearly with waypoint count.

FK (forward kinematics) is significantly faster at ~0.2ms per call.

### Fallback Solver (compas_fab PyBullet)

| Waypoints | Time (s) | ms/point | Solver |
|-----------|----------|----------|--------|
| 100       | ~0.5     | ~5.0     | compas_fab |
| 1,000     | ~5.0     | ~5.0     | compas_fab |

The fallback solver is ~50x slower and should only be used when roboticstoolbox is unavailable.

## Running Benchmarks

```bash
# Install benchmark dependencies
pip install pytest-benchmark

# Run benchmarks
python -m pytest tests/benchmarks/ -v --benchmark-sort=name

# Save results as JSON
python -m pytest tests/benchmarks/ --benchmark-json=benchmark-results.json
```

## Minimum System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU       | 4 cores | 8+ cores    |
| RAM       | 8 GB    | 16 GB       |
| GPU       | Integrated (for Three.js) | Discrete GPU (for large models) |
| Storage   | 2 GB free | 5 GB free |
| Python    | 3.10    | 3.11        |
| Node.js   | 20      | 20 LTS      |
| OS        | Windows 10, Ubuntu 22.04, macOS 13 | Latest stable |

## Scaling Notes

- **Toolpath size**: Up to 200K waypoints tested without issues. Memory usage is linear (~50 bytes per waypoint for joint trajectory).
- **Geometry size**: STL files up to 500MB supported (configurable `MAX_UPLOAD_SIZE`). Three.js viewport performance degrades above ~2M triangles.
- **Simulation playback**: Smooth at 60fps for toolpaths up to 100K points. Larger toolpaths benefit from layer-based rendering.
