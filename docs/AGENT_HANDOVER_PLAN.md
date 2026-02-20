# OpenAxis: Agent Handover Plan
# Benchmark-Driven Honesty Fixes + Workflow Verification

**Date:** 2026-02-20
**For:** Next LLM agent session
**Context:** This document is the complete briefing. Read it fully before writing a single line of code.

---

## 1. WHAT YOU ARE INHERITING

OpenAxis is a robotic hybrid-manufacturing platform (open-source alternative to Adaxis AdaOne). The core pipeline is **real and works**:

```
STL file → ORNL Slicer 2 → Toolpath → IK Solver → Three.js preview → G-code/RAPID/KRL export
```

**What actually works (when ORNL Slicer 2 binary is installed):**
- Load STL, centre geometry ✅
- Slice with planar slicer (ORNL Slicer 2 subprocess) ✅
- Solve IK with roboticstoolbox-python (Levenberg-Marquardt, ~25ms/waypoint) ✅
- Replay trajectory in Three.js ✅
- Export to G-code, RAPID (ABB), KRL (KUKA), Fanuc ✅
- 286 Python unit tests pass, 45 integration tests pass ✅

**What is broken or dishonest:**
- "Simulation" is a trajectory replay — no physics, PyBullet code exists but is disconnected
- Monitoring dashboard shows random numbers dressed as sensor data (fabricated)
- Process status panel shows hardcoded 220°C / 10 mm³/s (static HTML)
- Non-planar slicer options (Angled, Radial, Curve, Revolved) appear in UI dropdown but crash backend
- Several endpoints return HTTP 200 with empty/mock data when services are unavailable
- 13 frontend tests permanently fail (tests for a function that was deliberately gutted to return zeros)
- No end-to-end workflow test that verifies correct coordinates/outputs (only unit tests)

---

## 2. THE TWO THINGS YOU MUST DO (IN ORDER)

### PRIORITY 1: Build the Workflow Benchmark Test

**File to create:** `tests/integration/test_workflow_benchmark.py`

This is your self-verification tool. It tests the real user journey — not "does the code run" but "does the code produce correct results for known geometry." Once this file exists and all 7 test cases pass, you have a reliable way to know if your other changes broke something.

### PRIORITY 2: Apply the Honesty Fixes

Six targeted changes that make the UI accurate. None of them add features — they remove false impressions.

Do not add new features. Do not invent new architecture. Do not generalise. Just fix what is wrong.

---

## 3. THE WORKFLOW BENCHMARK (FULL SPECIFICATION)

### The Ground Truth Problem — Read This Before Writing Any Test

There is a fundamental trap here: **an LLM cannot verify its own output.**

If you write code that slices a cube and produces layer Z = 2.0 mm, then write a test
that checks `assert layer.z == 2.0`, you have proved nothing. You generated both the
expected value and the actual value. Any bug that makes the slicer produce the wrong
Z will also make you write the wrong assertion, and the test will still pass.

The only way a test is meaningful is if the expected values came from somewhere that
is independent of the code being tested:

1. **Physics-verified results** — a real robot ran the path, coordinates were measured
2. **Published open-source slicer test data** — e.g., CuraEngine's known-good outputs for their test geometry
3. **A human expert ran the full workflow and recorded what they got**

**The cube is the worst possible benchmark geometry.** A cube has 4 corners per layer,
all axis-aligned. Every slicer passes on a cube. The failures happen on overhangs,
non-manifold geometry, thin walls, curved surfaces — things that are genuinely hard
to slice. Testing on a cube gives false confidence that the slicer works on real parts.

### What the Benchmark Should Actually Be

**Current state (honest):** We do not yet have physics-verified expected outputs for
any geometry. We do not have published CuraEngine/PrusaSlicer test fixtures adapted
to our pipeline. Until a human runs the full workflow on real geometry and records
the real outputs, we cannot write meaningful coordinate-level assertions.

**What we CAN test without ground truth (structural tests, not correctness tests):**
These are not benchmarks — they are sanity checks. They catch crashes, NaN values,
and type errors. They do NOT verify that the slicer is computing the right geometry.

- Does the pipeline return a non-empty toolpath? (not correctness, just liveness)
- Are all coordinates finite? (catches NaN/Inf bugs)
- Are waypoint times monotonically increasing? (catches timing logic errors)
- Does IK return non-zero joint angles? (catches stub/mock detection)
- Does FK(IK(target)) ≈ target within tolerance? (this IS a real correctness check — it's library math)
- Does G-code export contain movement commands? (catches empty-output bugs)
- Do error paths fail loudly rather than silently? (catches mock fallback bugs)

**The FK-IK roundtrip is the one test with real ground truth:** it is a mathematical
identity — FK(IK(x)) must equal x within solver tolerance. This is not LLM-generated,
it is the definition of what IK means. This is the one test worth asserting a numeric
tolerance on.

**Future: how to get real ground truth**
- Slice a known geometry in ORNL Slicer 2, save the actual G-code output, commit it
  as a fixture, and compare future slicing output against that file
- Or: use CuraEngine/PrusaSlicer test fixtures and compare outputs with ours
- Or: have a human run a real path on the robot and record the joint values

Until one of those exists, be honest that the benchmark is a liveness/structural
check, not a physics correctness check. Do not claim it verifies correctness.

### What the Test File Actually Is

The file below is a **structural/liveness test suite**, not a physics benchmark.
It checks that the pipeline runs without crashing, produces non-empty output,
and that the FK-IK roundtrip holds (the one mathematically grounded assertion).
It does NOT verify that sliced coordinates are geometrically correct — that
requires physics-verified ground truth which does not yet exist.

Label it honestly in the file header. Do not call it a benchmark.

```python
# tests/integration/test_pipeline_liveness.py

"""
Pipeline liveness and structural tests.

These tests verify that the pipeline runs, produces non-empty results,
and that the IK/FK libraries are correctly integrated. They do NOT
verify geometric correctness of sliced coordinates — that requires
physics-verified ground truth data which is not yet available.

The FK-IK roundtrip test (TestCase4) is the only assertion with real
mathematical ground truth: FK(IK(x)) must equal x within solver tolerance.

Run: pytest tests/integration/test_pipeline_liveness.py -v
"""

import math
import pytest

# The mock_ornl_slicer fixture is defined in conftest.py — already exists.
# It patches the ORNL subprocess to return a 2-layer 10×10 mm square G-code.


@pytest.mark.integration
class TestCase1_CubeSlicingVerification:
    """
    Slice a 10×10×10 mm cube at 2 mm layer height.
    Verify layer count, Z-heights, and coordinate bounds.
    """

    def test_toolpath_has_segments(self, mock_ornl_slicer, tmp_path):
        from openaxis.slicing.ornl_slicer import ORNLSlicer, ORNLSlicerConfig

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        slicer = ORNLSlicer()
        config = ORNLSlicerConfig("FDM")
        config.set_layer_height(2.0)

        toolpath = slicer.slice(stl_path, config)

        assert toolpath is not None
        assert len(toolpath.segments) > 0, "Toolpath has no segments"
        assert toolpath.total_layers >= 2, "Expected at least 2 layers"

    def test_all_coordinates_are_finite(self, mock_ornl_slicer, tmp_path):
        from openaxis.slicing.ornl_slicer import ORNLSlicer

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        toolpath = ORNLSlicer().slice(stl_path)

        for seg in toolpath.segments:
            for pt in seg.points:
                assert math.isfinite(pt.x), f"Non-finite X: {pt.x}"
                assert math.isfinite(pt.y), f"Non-finite Y: {pt.y}"
                assert math.isfinite(pt.z), f"Non-finite Z: {pt.z}"

    def test_z_heights_are_positive(self, mock_ornl_slicer, tmp_path):
        from openaxis.slicing.ornl_slicer import ORNLSlicer

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        toolpath = ORNLSlicer().slice(stl_path)

        for seg in toolpath.segments:
            for pt in seg.points:
                assert pt.z > 0, f"Z should be positive, got {pt.z}"

    def test_coordinates_within_cube_bounds(self, mock_ornl_slicer, tmp_path):
        """Mock G-code is a 10×10 mm square — all XY coords within [-1, 11]."""
        from openaxis.slicing.ornl_slicer import ORNLSlicer

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        toolpath = ORNLSlicer().slice(stl_path)

        for seg in toolpath.segments:
            for pt in seg.points:
                assert -1.0 <= pt.x <= 11.0, f"X out of bounds: {pt.x}"
                assert -1.0 <= pt.y <= 11.0, f"Y out of bounds: {pt.y}"
                assert 0.0 <= pt.z <= 1.0, f"Z out of bounds: {pt.z}"


@pytest.mark.integration
class TestCase2_WaypointConversion:
    """
    Convert sliced toolpath to timed waypoints.
    Verify waypoint bounds and monotonically increasing time.
    """

    def test_waypoints_generated(self, mock_ornl_slicer, tmp_path):
        from openaxis.slicing.ornl_slicer import ORNLSlicer
        from openaxis.simulation.service import SimulationService

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        toolpath = ORNLSlicer().slice(stl_path)
        service = SimulationService()
        waypoints = service.create_simulation(toolpath)

        assert len(waypoints) > 0, "No waypoints generated"

    def test_waypoint_times_monotonically_increasing(self, mock_ornl_slicer, tmp_path):
        from openaxis.slicing.ornl_slicer import ORNLSlicer
        from openaxis.simulation.service import SimulationService

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        toolpath = ORNLSlicer().slice(stl_path)
        service = SimulationService()
        waypoints = service.create_simulation(toolpath)

        times = [w["time"] for w in waypoints]
        for i in range(1, len(times)):
            assert times[i] >= times[i - 1], \
                f"Time went backwards at index {i}: {times[i-1]} → {times[i]}"

    def test_waypoint_positions_are_finite(self, mock_ornl_slicer, tmp_path):
        from openaxis.slicing.ornl_slicer import ORNLSlicer
        from openaxis.simulation.service import SimulationService

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        toolpath = ORNLSlicer().slice(stl_path)
        waypoints = SimulationService().create_simulation(toolpath)

        for w in waypoints:
            pos = w["position"]
            for coord in pos:
                assert math.isfinite(coord), f"Non-finite waypoint coordinate: {coord}"

    def test_total_time_is_positive(self, mock_ornl_slicer, tmp_path):
        from openaxis.slicing.ornl_slicer import ORNLSlicer
        from openaxis.simulation.service import SimulationService

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        toolpath = ORNLSlicer().slice(stl_path)
        waypoints = SimulationService().create_simulation(toolpath)

        total_time = waypoints[-1]["time"] if waypoints else 0
        assert total_time > 0, "Total trajectory time must be > 0"


@pytest.mark.integration
class TestCase3_IKForReachablePositions:
    """
    Solve IK for waypoints placed within ABB IRB 6700 workspace.
    Waypoints offset to [1.5, 0, 0.5] metres — well within 2.6 m reach.
    Reachability must be ≥ 95%.
    """

    def test_ik_reachability_above_95_percent(self, mock_ornl_slicer, tmp_path):
        pytest.importorskip("roboticstoolbox", reason="roboticstoolbox-python not installed")

        from openaxis.slicing.ornl_slicer import ORNLSlicer
        from openaxis.simulation.service import SimulationService
        from openaxis.motion.kinematics import IKSolver

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        toolpath = ORNLSlicer().slice(stl_path)
        waypoints = SimulationService().create_simulation(toolpath)

        # Scale mm→m and offset to workspace centre
        OFFSET = [1.5, 0.0, 0.5]
        targets = []
        for w in waypoints:
            pos = w["position"]
            targets.append([
                pos[0] / 1000.0 + OFFSET[0],
                pos[1] / 1000.0 + OFFSET[1],
                pos[2] / 1000.0 + OFFSET[2],
            ])

        solver = IKSolver()
        with solver:
            result = solver.solve_trajectory(targets)

        reachability = result.get("reachabilityPercent", 0)
        assert reachability >= 95.0, \
            f"Expected ≥95% reachability, got {reachability:.1f}%"

    def test_ik_joint_angles_not_all_zeros(self, mock_ornl_slicer, tmp_path):
        """Joint angles must not all be zero — that indicates a stub/mock."""
        pytest.importorskip("roboticstoolbox", reason="roboticstoolbox-python not installed")

        from openaxis.slicing.ornl_slicer import ORNLSlicer
        from openaxis.simulation.service import SimulationService
        from openaxis.motion.kinematics import IKSolver

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        toolpath = ORNLSlicer().slice(stl_path)
        waypoints = SimulationService().create_simulation(toolpath)

        OFFSET = [1.5, 0.0, 0.5]
        targets = [
            [w["position"][0] / 1000.0 + OFFSET[0],
             w["position"][1] / 1000.0 + OFFSET[1],
             w["position"][2] / 1000.0 + OFFSET[2]]
            for w in waypoints[:5]  # just check first 5
        ]

        solver = IKSolver()
        with solver:
            result = solver.solve_trajectory(targets)

        trajectory = result.get("trajectory", [])
        assert len(trajectory) > 0, "No trajectory returned"

        # At least one waypoint must have non-zero joint angles
        has_nonzero = any(
            any(abs(j) > 0.01 for j in wp.get("joints", []))
            for wp in trajectory
        )
        assert has_nonzero, "All joint angles are zero — IK solver is stubbed or broken"

    def test_joint_angles_within_limits(self, mock_ornl_slicer, tmp_path):
        """All joint angles must be within ±360° (physical limit sanity check)."""
        pytest.importorskip("roboticstoolbox", reason="roboticstoolbox-python not installed")

        from openaxis.slicing.ornl_slicer import ORNLSlicer
        from openaxis.simulation.service import SimulationService
        from openaxis.motion.kinematics import IKSolver
        import math as _math

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        toolpath = ORNLSlicer().slice(stl_path)
        waypoints = SimulationService().create_simulation(toolpath)

        OFFSET = [1.5, 0.0, 0.5]
        targets = [
            [w["position"][0] / 1000.0 + OFFSET[0],
             w["position"][1] / 1000.0 + OFFSET[1],
             w["position"][2] / 1000.0 + OFFSET[2]]
            for w in waypoints
        ]

        solver = IKSolver()
        with solver:
            result = solver.solve_trajectory(targets)

        for wp in result.get("trajectory", []):
            for j in wp.get("joints", []):
                assert abs(j) <= 2 * _math.pi, \
                    f"Joint angle {_math.degrees(j):.1f}° exceeds physical limit"


@pytest.mark.integration
class TestCase4_FKIKRoundtrip:
    """
    FK(IK(target)) ≈ target.
    Position error must be < 2 mm (2e-3 m) for all reachable waypoints.
    This validates the IK solver is correct, not just non-crashing.
    """

    def test_fk_ik_roundtrip_error_under_2mm(self, mock_ornl_slicer, tmp_path):
        pytest.importorskip("roboticstoolbox", reason="roboticstoolbox-python not installed")

        from openaxis.slicing.ornl_slicer import ORNLSlicer
        from openaxis.simulation.service import SimulationService
        from openaxis.motion.kinematics import IKSolver
        import math as _math

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        toolpath = ORNLSlicer().slice(stl_path)
        waypoints = SimulationService().create_simulation(toolpath)

        OFFSET = [1.5, 0.0, 0.5]
        targets = [
            [w["position"][0] / 1000.0 + OFFSET[0],
             w["position"][1] / 1000.0 + OFFSET[1],
             w["position"][2] / 1000.0 + OFFSET[2]]
            for w in waypoints
        ]

        # Take 5 evenly spaced samples
        step = max(1, len(targets) // 5)
        samples = targets[::step][:5]
        sample_indices = list(range(0, len(targets), step))[:5]

        solver = IKSolver()
        with solver:
            ik_result = solver.solve_trajectory(targets)
            trajectory = ik_result.get("trajectory", [])

        errors = []
        for i, sample_idx in enumerate(sample_indices):
            if sample_idx >= len(trajectory):
                continue
            joints = trajectory[sample_idx].get("joints", [])
            if not joints or all(abs(j) < 1e-6 for j in joints):
                continue  # unreachable point, skip

            fk_result = solver.forward_kinematics(joints)
            fk_pos = fk_result.get("position", [0, 0, 0])
            target = samples[i]

            error = _math.sqrt(sum((a - b) ** 2 for a, b in zip(fk_pos, target)))
            errors.append(error)
            assert error < 0.002, \
                f"FK-IK roundtrip error {error*1000:.2f}mm > 2mm tolerance at sample {i}"

        assert len(errors) > 0, "No reachable samples found for FK-IK roundtrip check"


@pytest.mark.integration
class TestCase5_GCodeExportVerification:
    """
    Export toolpath to each supported format.
    Verify non-empty output with correct movement commands.
    """

    def test_gcode_export_contains_movement_commands(self, mock_ornl_slicer, tmp_path):
        from openaxis.slicing.ornl_slicer import ORNLSlicer
        from openaxis.slicing.postprocessor import PostProcessor

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        toolpath = ORNLSlicer().slice(stl_path)
        pp = PostProcessor()
        gcode = pp.export(toolpath, format="gcode")

        assert len(gcode) > 0, "G-code output is empty"
        lines = gcode.splitlines()
        assert len(lines) > 10, f"G-code too short: {len(lines)} lines"
        assert any(line.startswith("G1") or line.startswith("G0") for line in lines), \
            "G-code has no movement commands (G0/G1)"

    def test_rapid_export_contains_movel(self, mock_ornl_slicer, tmp_path):
        from openaxis.slicing.ornl_slicer import ORNLSlicer
        from openaxis.slicing.postprocessor import PostProcessor

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        toolpath = ORNLSlicer().slice(stl_path)
        pp = PostProcessor()
        rapid = pp.export(toolpath, format="rapid")

        assert len(rapid) > 0, "RAPID output is empty"
        assert "MoveL" in rapid or "MoveJ" in rapid, \
            "RAPID output has no MoveL/MoveJ commands"

    def test_krl_export_contains_lin(self, mock_ornl_slicer, tmp_path):
        from openaxis.slicing.ornl_slicer import ORNLSlicer
        from openaxis.slicing.postprocessor import PostProcessor

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        toolpath = ORNLSlicer().slice(stl_path)
        pp = PostProcessor()
        krl = pp.export(toolpath, format="krl")

        assert len(krl) > 0, "KRL output is empty"
        assert "LIN" in krl or "PTP" in krl, "KRL output has no LIN/PTP commands"

    def test_no_export_format_contains_todo(self, mock_ornl_slicer, tmp_path):
        """No format should contain placeholder text like TODO or NotImplemented."""
        from openaxis.slicing.ornl_slicer import ORNLSlicer
        from openaxis.slicing.postprocessor import PostProcessor

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        toolpath = ORNLSlicer().slice(stl_path)
        pp = PostProcessor()

        for fmt in ["gcode", "rapid", "krl"]:
            output = pp.export(toolpath, format=fmt)
            assert "TODO" not in output, f"{fmt} output contains 'TODO'"
            assert "NotImplemented" not in output, f"{fmt} output contains 'NotImplemented'"


@pytest.mark.integration
class TestCase6_FullPipelineE2E:
    """
    Run Pipeline.execute() end-to-end with mock slicer.
    All 3 steps must complete. Results must have real data, not zeros.
    """

    def test_pipeline_executes_all_steps(self, mock_ornl_slicer, tmp_path):
        from openaxis.pipeline import Pipeline, PipelineConfig

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        config = PipelineConfig(
            geometry_path=stl_path,
            layer_height=2.0,
            wall_count=1,
        )
        pipeline = Pipeline()
        result = pipeline.execute(config)

        assert result.success, f"Pipeline failed: {result.error}"
        assert result.toolpath_data is not None, "No toolpath data"
        assert result.simulation_data is not None, "No simulation data"

    def test_pipeline_toolpath_has_segments(self, mock_ornl_slicer, tmp_path):
        from openaxis.pipeline import Pipeline, PipelineConfig

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        result = Pipeline().execute(PipelineConfig(geometry_path=stl_path))

        assert result.success
        toolpath = result.toolpath_data
        # Accept either a Toolpath object or a dict with 'segments' key
        if hasattr(toolpath, "segments"):
            assert len(toolpath.segments) > 0
        elif isinstance(toolpath, dict):
            assert len(toolpath.get("segments", [])) > 0

    def test_pipeline_completes_within_30_seconds(self, mock_ornl_slicer, tmp_path):
        import time
        from openaxis.pipeline import Pipeline, PipelineConfig

        stl_path = str(tmp_path / "cube.stl")
        with open(stl_path, "w") as f:
            f.write("solid cube\nendsolid cube\n")

        start = time.time()
        result = Pipeline().execute(PipelineConfig(geometry_path=stl_path))
        elapsed = time.time() - start

        assert elapsed < 30.0, f"Pipeline took {elapsed:.1f}s, expected < 30s"


@pytest.mark.integration
class TestCase7_ErrorPathsAreHonest:
    """
    Failures must be explicit, not silent.
    No endpoint should return success with empty/mock data on error.
    """

    def test_nonexistent_file_causes_pipeline_failure(self):
        from openaxis.pipeline import Pipeline, PipelineConfig

        config = PipelineConfig(geometry_path="/nonexistent/path/model.stl")
        result = Pipeline().execute(config)

        assert not result.success, "Pipeline should fail for nonexistent file"
        assert result.error is not None and len(result.error) > 0, \
            "Error message should be non-empty"

    def test_nonplanar_strategy_raises_not_implemented(self, tmp_path):
        """Non-planar slicers raise NotImplementedError — they must NOT return empty data."""
        from openaxis.slicing.angled_slicer import AngledSlicer

        slicer = AngledSlicer()
        with pytest.raises(NotImplementedError):
            slicer.slice("/any/path.stl")

    def test_unreachable_position_gives_low_reachability(self):
        """IK for position 100 m away must return low reachability, not success."""
        pytest.importorskip("roboticstoolbox", reason="roboticstoolbox-python not installed")

        from openaxis.motion.kinematics import IKSolver

        # Positions 100 m away — completely unreachable
        targets = [[100.0, 100.0, 100.0]] * 5

        solver = IKSolver()
        with solver:
            result = solver.solve_trajectory(targets)

        reachability = result.get("reachabilityPercent", 100)
        assert reachability < 10.0, \
            f"Expected < 10% reachability for 100m targets, got {reachability:.1f}%"
```

### Import Paths You Need to Verify

Before running the benchmark, check the actual import paths in the codebase:

```bash
# Find where SimulationService lives
grep -r "class SimulationService" src/

# Find where IKSolver lives
grep -r "class IKSolver" src/

# Find where PostProcessor lives (for export)
grep -r "class PostProcessor" src/
grep -r "def export" src/backend/postprocessor_service.py

# Find Pipeline
grep -r "class Pipeline" src/openaxis/pipeline.py
```

**Adapt the imports in the benchmark to match what's actually in the codebase.** The test cases above use logical names — fix them to use real class/module names before running.

---

## 4. THE HONESTY FIXES (IN ORDER)

### Fix 1: Rename "Simulation" → "Trajectory Preview" in UI

**Why:** The backend computes waypoint timing from distance/speed and plays it back. No physics. Calling it simulation is misleading.

**Files to change:**
- `src/ui/src/components/panels/SimulationPanel.tsx` — all user-visible text
- `src/ui/src/pages/WorkspaceView.tsx` — mode selector labels
- Any other UI file that shows the word "Simulation" to the user

**Do NOT rename:** API endpoint paths, Python class names, code identifiers — those are internal and changing them is a large refactor with no user benefit.

**Verify:** After the change, `grep -r "Simulation" src/ui/src/` should return NO results in display strings. It can still appear in code comments and identifiers.

### Fix 2: Remove Fake Monitoring Data

**File:** `src/backend/server.py`

**Find these lines** (around line 1557–1577):
```python
"temperature": round(220 + random.uniform(-5, 5), 1),
"flowRate": round(10 + random.uniform(-1, 1), 2),
"pressure": round(5 + random.uniform(-0.5, 0.5), 2),
"networkLatency": round(psutil.cpu_times().idle % 50, 1),  # THIS IS FABRICATED
```

**Replace with:**
```python
"status": "unavailable",
"message": "No sensors connected — hardware integration in Phase 4"
```

**Frontend:** Update whatever component renders this data to show "No sensors connected" when status is "unavailable."

**The `networkLatency` metric using `cpu_idle % 50` must be deleted.** It is not a measurement of anything.

### Fix 3: Remove Hardcoded Process Status Values

**File:** `src/ui/src/components/panels/SimulationPanel.tsx` (around lines 715–726)

**Find:** hardcoded `<span>220°C</span>` and `<span>10 mm³/s</span>` HTML

**Replace with:** Show "N/A" or hide the section entirely. The values should only appear when real data from the backend is available.

### Fix 4: Disable Non-Planar Slicer Options in UI

**Why:** Angled, Radial, Curve, and Revolved slicers all raise `NotImplementedError`. They appear in the dropdown as if they work.

**Action:** In the slicer strategy dropdown component, mark all non-Planar options as disabled:
- Grey them out visually
- Add a tooltip: "Not available — planned for Phase 2"
- Do NOT just catch the NotImplementedError silently — let the error propagate if user somehow triggers it

**Find the component:** `grep -r "Radial\|Angled\|Revolved\|CurveSlicer" src/ui/src/`

### Fix 5: Change Silent Mock Fallbacks to Honest Errors

**File:** `src/backend/server.py`

These endpoints currently return HTTP 200 with empty/mock data when services are unavailable. Change them to return HTTP 503:

| Endpoint | Current | Should be |
|----------|---------|-----------|
| `/api/toolpath/generate` when slicer unavailable | 200 + empty toolpath | 503 + "Slicing module not available. Install ORNL Slicer 2." |
| `/api/simulation/create` with no data | 200 + mock sim | 400 + "No toolpath data provided" |

**Exception:** The `/api/robot/fk` mock that returns `"mock": True` is acceptable during development. Keep it but add a warning field: `"warning": "Using approximate FK — install roboticstoolbox-python for accuracy"`. The frontend should show this as a yellow banner.

### Fix 6: Delete the Permanently-Failing Frontend Tests

**File:** `src/ui/src/utils/__tests__/analyticalIK.test.ts` (or wherever the 13 failing tests are)

These 13 tests fail because `solveIK6DOF` was deliberately gutted to return `[0,0,0,0,0,0]`. Tests for a function that is designed to not work are noise.

**Action:** Delete the test file. If the function is ever re-implemented properly, write new tests then.

**Verify:** After deletion, `npx vitest run` should show 0 failures.

---

## 5. WHAT THE SLICER SITUATION ACTUALLY IS

ORNL Slicer 2 is a Windows desktop application. It is NOT a Python package. It CANNOT be pip-installed or Docker-containerised. The integration is a subprocess wrapper — it works when the binary is manually installed.

**The UI currently shows these slicer options:** Planar, Angled, Radial, Curve, Revolved

**The truth:**
- Planar → ORNL Slicer 2 subprocess → works when binary is installed
- Angled, Radial, Curve, Revolved → all raise `NotImplementedError` immediately

**What to do with the UI:**
- Keep Planar enabled
- Grey out everything else with tooltip "Phase 2 — not yet implemented"
- Do NOT add a built-in demo slicer — that is a new feature, not a fix

**What NOT to do:**
- Do NOT add a compas_slicer backend, a Slicer3D integration, or any other slicer library
- Do NOT invent a "simple grid pattern slicer" from scratch
- The ORNL Slicer 2 integration is the right approach per CLAUDE.md — just make the UI honest about what works

---

## 6. WHAT NOT TO TOUCH

These things work correctly. Do not modify them:

- `src/openaxis/slicing/ornl_slicer.py` — the ORNL Slicer 2 wrapper (~1000 lines, production grade)
- `src/openaxis/slicing/planar_slicer.py` — delegates to ORNL
- `src/backend/robot_service.py` — IK with roboticstoolbox-python
- `src/openaxis/motion/kinematics.py` — IK solver
- `src/openaxis/pipeline.py` — pipeline orchestrator
- `src/backend/postprocessor_service.py` — G-code/RAPID/KRL/Fanuc export
- All 286 unit tests and 45 integration tests — they pass; don't break them
- Any COMPAS geometry data structures

---

## 7. EXECUTION ORDER

```
Step 1: Build tests/integration/test_workflow_benchmark.py
        - Adapt imports to real class names in the codebase
        - Run: pytest tests/integration/test_workflow_benchmark.py -v
        - Note which tests pass and which fail
        - Do NOT move on until the file exists and runs (even if some fail)

Step 2: Run the full test suite to get a baseline
        - pytest tests/ -v --tb=short   → record pass/fail count
        - cd src/ui && npx vitest run   → record pass/fail count

Step 3: Apply Fix 6 first (delete analyticalIK tests)
        - Immediately reduces frontend failure noise
        - Verify: npx vitest run shows 0 failures

Step 4: Apply Fix 4 (disable non-planar in UI)
        - This is a UI-only change, no backend impact
        - Test Case 7b in benchmark should still pass (NotImplementedError still raises)

Step 5: Apply Fix 1 (rename Simulation → Trajectory Preview in UI)
        - UI text only — no code logic changes
        - grep to verify no user-visible "Simulation" text remains

Step 6: Apply Fix 3 (remove hardcoded process status)
        - Replace static HTML values with N/A or hidden section

Step 7: Apply Fix 2 (remove fake monitoring data)
        - Backend server.py change
        - Frontend component update to handle "unavailable" status

Step 8: Apply Fix 5 (honest errors from backend)
        - server.py: change 200+empty to 503+message for unavailable services

Step 9: Run benchmark again
        - pytest tests/integration/test_workflow_benchmark.py -v
        - All 7 cases must pass

Step 10: Run full test suite
        - pytest tests/ — 0 failures
        - npx vitest run — 0 failures
```

---

## 8. ACCEPTANCE CRITERIA

You are done when ALL of the following are true:

1. `pytest tests/integration/test_workflow_benchmark.py -v` — all test cases pass
2. `pytest tests/ -v` — 0 failures (unit + integration)
3. `cd src/ui && npx vitest run` — 0 failures
4. The word "Simulation" does not appear in any user-visible UI text
5. The monitoring dashboard shows "No sensors connected" (not random numbers)
6. Non-planar slicer options are visually disabled with a tooltip
7. No backend endpoint returns HTTP 200 with empty/mock data when the service is unavailable
8. No benchmark test contains fabricated assertions (i.e., tests that pass by checking for zeros)

---

## 9. HOW TO GET REAL GROUND TRUTH (FUTURE WORK)

The liveness tests above are the right starting point. To turn them into real
correctness tests, one of the following must happen first:

**Option A: Commit real ORNL Slicer 2 output as a fixture**
- Slice a specific STL (e.g., `test-geometry/test_box.stl`) with ORNL Slicer 2
- Commit the resulting `.gcode` file to `tests/fixtures/test_box_expected.gcode`
- Future tests compare new slicing output against this file line-by-line
- When ORNL Slicer 2 changes behaviour, a human reviews the diff and updates the fixture

**Option B: Use published slicer test data**
- CuraEngine: https://github.com/Ultimaker/CuraEngine/tree/main/tests — has known
  expected outputs for specific geometries, verified by the CuraEngine team
- SlicerTestModels: https://github.com/Ghostkeeper/SlicerTestModels — community-
  tested geometries designed specifically to stress slicers (overhangs, thin walls, curves)
- Adapt one of these geometries + their known outputs to compare against our pipeline

**Option C: Human-in-the-loop verification**
- A manufacturing engineer runs the full workflow on a real part
- Records the actual ORNL Slicer 2 output, the actual IK joint values, the actual
  robot code, and commits all of it as fixtures
- The test suite checks that we reproduce the same output

Until one of these is done, the liveness tests are the honest boundary of what
automated testing can verify. Do not expand them with assertions that were derived
by running the code — that is not testing, that is just recording what the code does.

---

## 10. WHY THE PREVIOUS AGENT BUILT THEATER (AVOID THESE PATTERNS)

1. **No verification loop** — Agent ran unit tests (which pass with mocks) but never verified real data flow. The benchmark fixes this.

2. **Optimises for perceived completeness** — When the agent saw empty UI panels, it filled them with plausible-looking content (random ±5°C around 220°C). The instruction is: if data doesn't exist, show nothing or say "unavailable."

3. **Confused "simulation" meaning** — In robotics, simulation means physics (PyBullet, collision, deposition). In web dev, it means animated replay. The agent used the web-dev definition.

4. **Silent mock fallbacks** — When services weren't available, the agent returned HTTP 200 with empty data so the frontend said "Success!" This hides real errors.

5. **Permanent test failures treated as acceptable** — 13 failing tests left in place. Never acceptable.

**The rule:** If something doesn't work, say so. Honest software that does less is more valuable than impressive-looking software that lies.

---

*Load this document into your context at the start of the session. Build the benchmark first. Fix the dishonesty. Run the full suite. Do not add features.*
