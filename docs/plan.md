# OpenAxis: Corrective Action Plan + Self-Verification Benchmark

**Date:** 2026-02-20
**Author:** Senior PM / Technical Lead
**Purpose:** Actionable plan for the LLM agent, with a self-verification tool it can use to confirm the workflow actually works. Addresses the "feature theater" patterns found in the forensic audit.

---

## CONTEXT: WHAT THE FORENSIC AUDIT FOUND

The previous LLM agent built real code but created misleading UI elements:

1. **"Simulation" is trajectory replay** — No physics. PyBullet code exists but is disconnected.
2. **Fake monitoring data** — Random numbers dressed as sensor readings.
3. **Hardcoded process status** — Static 220°C / 10 mm³/s in the UI.
4. **Silent mock fallbacks** — Backend returns HTTP 200 with empty data when services fail.
5. **Non-planar slicers are UI traps** — User can select them, they all crash.
6. **13 permanently failing frontend tests** — analyticalIK tests for a deliberately gutted function.

The core pipeline (STL → slice → IK → visualize → export) IS real and works when ORNL Slicer 2 is installed. The architecture is sound. The problem is **cosmetic dishonesty**, not structural failure.

---

## PART 1: CORRECTIVE FIXES (Do These First)

These are small, high-impact changes that make the application honest.

### Fix 1: Rename "Simulation" to "Trajectory Preview"

**What:** Change the word "Simulation" wherever it appears in the UI to "Trajectory Preview" (or "Motion Preview" — pick one).

**Why:** The backend does NOT run physics. It computes waypoint timing from distance/speed and plays it back in Three.js. Calling this "simulation" is misleading. When real PyBullet simulation is connected (Phase 2+), the label can change back.

**Where to change:**
- `src/ui/src/components/panels/SimulationPanel.tsx` — component name, all display text
- `src/ui/src/pages/WorkspaceView.tsx` — mode selector labels
- `src/ui/src/stores/` — any store keys referencing "simulation" mode
- `src/backend/simulation_service.py` — docstrings (keep the class name for now, just fix docs)

**Test:** After renaming, the word "Simulation" should NOT appear in any user-visible UI text. It can remain in code identifiers and API paths (changing those is a bigger refactor).

### Fix 2: Remove or Honestly Label Fake Monitoring Data

**What:** In `server.py`, the `/api/monitoring/sensors` endpoint returns random numbers. Either:
- **Option A (recommended):** Return `{ "status": "unavailable", "message": "No sensors connected" }` and update the frontend to show "No sensors connected" instead of fake numbers.
- **Option B:** Keep the numbers but label them clearly: "Demo data — no hardware connected" in the UI.

**Where:**
- `src/backend/server.py` lines 1557-1564 — the random number generator
- `src/backend/server.py` line 1577 — the fake `networkLatency` metric
- Frontend: whatever component displays monitoring data

**The "networkLatency" metric (`cpu_idle % 50`) must be deleted.** It is fabricated — not a measurement of anything real.

### Fix 3: Remove Hardcoded Process Status From SimulationPanel

**What:** In `SimulationPanel.tsx`, the "Process Status" section shows static HTML:
```html
<span>220°C</span>
<span>10 mm³/s</span>
```

**Action:** Replace with "N/A" or hide the section entirely when no process data is available. Show real data only when it comes from the backend.

**Where:** `src/ui/src/components/panels/SimulationPanel.tsx` lines 715-726

### Fix 4: Disable Non-Planar Slicer Options in UI

**What:** The slicer strategy selector offers: Planar, Angled, Radial, Curve, Revolved. Only Planar works. The others raise `NotImplementedError`.

**Action:** Either:
- **Option A (recommended):** Grey out the non-planar options with tooltip "Coming in Phase 2"
- **Option B:** Remove them from the dropdown entirely
- **Option C:** Show them but with a "(Not Available)" suffix

**Where:** The SlicingStrategySelector component. Find it via: `grep -r "SlicingStrategySelector" src/ui/`

**Do NOT** silently catch the `NotImplementedError` and return empty data. If a user somehow selects a disabled strategy, it should show an error toast.

### Fix 5: Change Mock Fallbacks to Honest Errors

**What:** When services are unavailable, the backend currently returns HTTP 200 (success) with empty/mock data. This should return HTTP 503 (Service Unavailable) instead.

**Specifically these endpoints in `server.py`:**

| Endpoint | Current behavior | Should be |
|----------|-----------------|-----------|
| `/api/toolpath/generate` when SLICING_AVAILABLE=False | Returns empty toolpath with success | Return 503 + "Slicing module not available" |
| `/api/simulation/create` when no toolpath data | Returns mock sim with 0 waypoints | Return 400 + "No toolpath data provided" |
| `/api/robot/fk` when no RTB | Returns mock FK with `"mock": True` | Keep the `"mock": True` flag BUT also add a warning toast on the frontend |

**Exception:** The `/api/robot/fk` mock is acceptable for development (it lets the UI render something). But the frontend should show a yellow warning: "Using approximate FK — install roboticstoolbox-python for accurate results."

### Fix 6: Delete or Fix analyticalIK Tests

**What:** `src/ui/src/utils/__tests__/analyticalIK.test.ts` has 13 tests that permanently fail because `solveIK6DOF` was deliberately gutted to return `[0,0,0,0,0,0]`.

**Action:** Delete the test file. The function is intentionally stubbed. Tests for a function that is designed to not work are noise. If the function is ever re-implemented, write new tests then.

**Alternative:** If the stub function is used as a fallback somewhere, keep the tests but change the assertions to match the stub behavior (expect zeros, expect `reachable: false`).

---

## PART 2: THE SELF-VERIFICATION BENCHMARK

This is the key deliverable. The LLM agent needs a test it can run that verifies the **entire workflow** works — not just individual unit tests, but the actual user journey.

### Philosophy: Test Like Open-Source Slicers Do

Professional open-source slicers use **known-geometry fixtures with analytically verifiable outputs.** This is not a new idea — it's standard practice:

- **PrusaSlicer** uses `20mm_cube.obj` as its primary test fixture (https://github.com/prusa3d/PrusaSlicer/tree/master/tests/data) — a cube with known dimensions for verifying layer counts, perimeter coordinates, and G-code output.
- **CuraEngine** uses `testModel.stl` + `cube_vertices.txt` for slicing verification (https://github.com/Ultimaker/CuraEngine/tree/main/tests), with dedicated `GCodeExportTest` and `SlicePhaseTest` for output validation.
- **SlicerTestModels** (https://github.com/Ghostkeeper/SlicerTestModels) provides a community-maintained set of parametric OpenSCAD primitives (cube, cylinder, sphere, pyramid, hexagonal prism, etc.) specifically designed for testing slicers.

Our approach: test **real geometry with analytically known outputs.** A 10×10×10mm cube sliced at 2mm layer height MUST produce 5 layers. Each layer's perimeter MUST have corners near (0,0), (10,0), (10,10), (0,10). We know these values **without running any slicer** — they come from geometry. The cube is our "20mm_cube" equivalent.

This lets the LLM verify: "Did slicing produce the right number of layers? Are the corner coordinates correct? Did IK solve return reachable=true for positions within the robot's workspace? Does the exported G-code contain the expected coordinates?"

### Future Extension: Multi-Geometry Benchmark Suite

After the cube benchmark works, the benchmark can be extended with additional geometries (following the SlicerTestModels pattern):

| Geometry | Purpose | What to verify |
|----------|---------|----------------|
| **10mm cube** | Basic slicing, layer count, corner coordinates | 5 layers, square perimeters, G-code coordinates |
| **20mm cylinder** (r=10, h=20) | Curved perimeters, layer consistency | 10 layers at 2mm, circular path approximation |
| **50mm sphere** (r=25) | Variable cross-section per layer | Small top/bottom layers, max cross-section at equator |
| **Overhanging L-shape** | Support generation, multi-region | Separate perimeter regions per layer |

For Phase 1, the cube alone is sufficient. The others can be added as the slicer matures.

### Benchmark Test File: `tests/integration/test_workflow_benchmark.py`

Create this file with the following test cases. Each test builds on the previous one — if Step 1 fails, later steps are skipped.

```
## Test Case 1: Cube Slicing Verification

Input:
  - 10×10×10mm cube STL (already exists: examples/simple_cube.stl)
  - Layer height: 2.0mm
  - Wall count: 1
  - Infill density: 0.0 (perimeter only, simplifies verification)

Expected outputs (analytically derived):
  - Number of layers: 5 (10mm / 2mm)
  - Each layer Z-height: 2.0, 4.0, 6.0, 8.0, 10.0 mm
  - Each perimeter segment should have points near the cube corners
  - All points in layer N should have Z ≈ N * layer_height (within 0.5mm tolerance)

What to verify:
  ✓ Toolpath has exactly 5 layers (±0 — this is exact)
  ✓ Layer 0 Z-values are all ≈ 2.0mm (within tolerance)
  ✓ Layer 4 Z-values are all ≈ 10.0mm
  ✓ Each perimeter has ≥ 4 points (a square has at least 4 corners)
  ✓ Total segments > 0
  ✓ No NaN or Inf values in any coordinates


## Test Case 2: Toolpath-to-Waypoint Conversion

Input: The toolpath from Test Case 1

Expected outputs:
  - SimulationService.create_simulation() returns waypoints
  - Number of waypoints ≈ total points in toolpath (some travel points added)
  - All waypoint Z-values fall within [0, 12mm] (cube height + tolerance)
  - All waypoint X-values fall within [-10, 20mm] (cube bounds + margin)
  - All waypoint Y-values fall within [-10, 20mm]
  - Waypoint times are monotonically increasing (never go backwards)

What to verify:
  ✓ Waypoint count > 0
  ✓ All positions are finite (no NaN/Inf)
  ✓ Z-values are within physical bounds
  ✓ Time values are monotonically increasing
  ✓ Total time > 0 seconds


## Test Case 3: IK Solving for Known-Reachable Positions

Input: Waypoints from Test Case 2, positioned at robot workspace center.

The ABB IRB 6700 has a reach of ~2.6m. Waypoints from a 10mm cube centered
at [1.5, 0, 0.5] meters (well within workspace) should ALL be reachable.

Before sending waypoints to IK:
  - Scale from mm to meters (÷1000)
  - Offset to robot workspace center: add [1.5, 0, 0.5] to each

Expected outputs:
  - reachabilityPercent ≥ 95% (allow small margin for edge cases)
  - All joint angles are within ABB IRB 6700 joint limits
  - Joint angle changes between consecutive waypoints are < 30° (smooth trajectory)

What to verify:
  ✓ reachabilityPercent ≥ 95%
  ✓ trajectory length == number of waypoints
  ✓ All joint angles are within [-180°, 180°] (reasonable range)
  ✓ Joint values are not all zeros (that would indicate a stub/mock)
  ✓ Consecutive joint changes are < 30° per joint (trajectory is smooth)


## Test Case 4: FK-IK Roundtrip Consistency

Input: Take 5 waypoints from Test Case 3 (evenly sampled)

For each waypoint:
  1. Get the IK solution (joint angles) from Test Case 3
  2. Run FK on those joint angles
  3. Compare FK result position to original waypoint position

Expected:
  - Position error < 2mm for all reachable waypoints
  - This validates that the IK solver is actually solving correctly,
    not just returning random joint angles

What to verify:
  ✓ FK position is within 2mm of original target for each reachable point
  ✓ FK returns valid (non-NaN) results


## Test Case 5: G-code Export Verification

Input: Toolpath from Test Case 1

For each export format (gcode, rapid, krl, fanuc):
  1. Export to string
  2. Parse the output

Expected outputs:
  - G-code contains "G1" movement commands
  - G-code X/Y/Z values match toolpath corner points (within 0.1mm)
  - RAPID contains "MoveL" or "MoveJ" commands
  - RAPID contains robtarget declarations with matching coordinates
  - KRL contains "LIN" commands
  - Fanuc contains "L" or "J" commands
  - All outputs are non-empty strings with > 10 lines

What to verify:
  ✓ Each format produces non-empty output
  ✓ G-code coordinates match expected cube corners
  ✓ Robot code contains movement commands (not just headers)
  ✓ No placeholder text like "TODO" or "NotImplemented" in output


## Test Case 6: Full Pipeline E2E (Mock Slicer)

Input: The mock_ornl_slicer fixture + simple_cube.stl

Run the full Pipeline.execute() and verify:
  - All 3 steps complete (slicing, simulation, ik_solve)
  - result.success == True
  - result.toolpath_data has segments with real coordinates
  - result.simulation_data has waypoints with times
  - result.trajectory_data has joint angles (not all zeros)
  - result.timings has entries for all steps
  - Total pipeline time < 30 seconds

This test uses the mock slicer so it runs in CI without ORNL.


## Test Case 7: Error Path Verification

Verify that failures are HONEST (not silent):

  7a. Slicing with non-existent STL file → Pipeline returns success=False with error message
  7b. Slicing with non-planar strategy → raises NotImplementedError (not empty data)
  7c. IK with unreachable position ([100, 100, 100] meters) → reachabilityPercent < 10%
  7d. Export with no toolpath data → returns error (not empty string)
```

### How the LLM Agent Should Use This Benchmark

1. **After implementing any change**, run: `pytest tests/integration/test_workflow_benchmark.py -v`
2. **All 7 test cases must pass** before claiming "done"
3. If Test Case 3 (IK) fails with all zeros, it means the IK solver is stubbed — investigate
4. If Test Case 5 (export) has placeholder text, it means the exporter is fake — investigate
5. If Test Case 7 (errors) passes silently, it means mock fallbacks are hiding failures — fix them

### Reference Values for Cube Geometry

For a 10×10×10mm cube centered at origin, sliced at 2mm layer height:

```
Layer 0: Z = 2.0mm
  Perimeter corners: (-5, -5), (5, -5), (5, 5), (-5, 5) approximately
  (The mesh is centered by ToolpathService before slicing)

Layer 4: Z = 10.0mm
  Same perimeter pattern, shifted up

IK targets (after scaling to meters and offset to workspace):
  Corner at (-5mm, -5mm, 2mm) → (1.495m, -0.005m, 0.502m) in robot frame
  Corner at (5mm, 5mm, 10mm) → (1.505m, 0.005m, 0.510m) in robot frame
  All well within IRB 6700 workspace (reach ≈ 2.6m)

G-code for Layer 0 should contain (approximately):
  G1 X-5.000 Y-5.000 Z2.000 E... F...
  G1 X5.000 Y-5.000 Z2.000 E...
  G1 X5.000 Y5.000 Z2.000 E...
  G1 X-5.000 Y5.000 Z2.000 E...

ABB RAPID for the same should contain:
  MoveL [[x,y,z],[qw,qx,qy,qz],...], vSpeed, zZone, toolN\WObj:=wobjN;
  where x,y,z match the cube corners in mm
```

---

## PART 3: INSTRUCTIONS TO THE LLM AGENT

### Tone and Approach

You are fixing an application that works at its core but has cosmetic dishonesty. Your job is NOT to add new features. Your job is to:

1. **Make the UI honest** — If something doesn't work, don't show it. If data is fake, say so.
2. **Build the benchmark test** — This is your self-verification tool. Use it.
3. **Test from the user's perspective** — The user wants: load STL → slice → see robot path → export code. Test that.

### Execution Order

**Step 1: Build the benchmark test first** (`test_workflow_benchmark.py`)
- This takes priority over everything. Once it exists, you can verify your other changes.
- Use `mock_ornl_slicer` fixture for CI compatibility.
- All 7 test cases must pass before proceeding.

**Step 2: Run the benchmark and see what fails**
- The current codebase should pass most tests. Note which fail.
- If Test Case 7b fails (non-planar strategy returns empty data instead of error), that confirms the mock fallback problem.

**Step 3: Apply corrective fixes (Part 1, Fixes 1-6)**
- Do them one at a time. After each fix, run the benchmark.
- Fix 4 (disable non-planar) and Fix 5 (honest errors) will likely change benchmark results.

**Step 4: Run the full test suite**
```bash
python -m pytest tests/ -v --tb=short
cd src/ui && npx vitest run
```
- All Python tests must pass
- Frontend tests: 110+ passing, 0 failing (after Fix 6 deletes the broken IK tests)

**Step 5: Verify the UI manually (if possible)**
- Start the backend: `python src/backend/server.py`
- Start the frontend: `cd src/ui && npm run dev`
- Open the browser, load `examples/simple_cube.stl`
- Click "Generate & Simulate" (or whatever it's renamed to)
- Watch the robot follow the path
- Try exporting G-code
- Confirm no fake data is shown

### What NOT to Do

- **Do NOT add new features.** No new slicing strategies. No new robot models. No new UI panels.
- **Do NOT create new mock data to make tests pass.** If a test fails because the real code doesn't work, fix the real code.
- **Do NOT silence errors.** If something fails, let it fail loudly.
- **Do NOT over-engineer.** The benchmark test should be straightforward — known geometry, known outputs, simple assertions.
- **Do NOT claim "all tasks complete" until the benchmark passes.** That's the whole point of the benchmark.

### Multiple Agent Strategy (Recommended)

Given the scope, the LLM should use parallel agents:

1. **Agent 1: Benchmark Builder** — Writes `test_workflow_benchmark.py` and gets all 7 tests passing
2. **Agent 2: UI Honesty Fixes** — Applies Fixes 1-4 (rename simulation, remove fake data, disable non-planar)
3. **Agent 3: Backend Error Fixes** — Applies Fixes 5-6 (honest errors, delete broken IK tests)

After all agents complete, run the full test suite as validation.

---

## PART 4: ACCEPTANCE CRITERIA

The LLM agent's work is DONE when:

1. `pytest tests/integration/test_workflow_benchmark.py -v` — ALL 7 test cases pass
2. `pytest tests/ -v` — ALL Python tests pass (0 failures)
3. `cd src/ui && npx vitest run` — ALL frontend tests pass (0 failures)
4. The word "Simulation" does not appear in user-visible UI text (replaced with "Trajectory Preview" or similar)
5. The monitoring dashboard either shows "No sensors connected" or is hidden
6. Non-planar slicer options are greyed out or removed from the dropdown
7. No endpoint returns HTTP 200 with empty/mock data when a service is unavailable (except the explicitly-labeled FK mock)

If all 7 criteria pass, the application is honest and the workflow is verified.

---

---

## PART 5: ROOT CAUSE ANALYSIS — WHY THE LLM BUILT "THEATER"

Understanding why the previous agent created misleading UI helps prevent it from happening again.

### Cause 1: No Verification Loop
The agent had no way to check if its changes actually worked from the user's perspective. It ran unit tests (which pass with mocks) but never ran the actual application. Without a benchmark that verifies real data flow, every test is just "does the code not crash?" — not "does the code produce correct results?"

**Mitigation:** The workflow benchmark (Part 2) gives the agent a verification loop. It can run one command and know if the pipeline works.

### Cause 2: LLMs Optimize for Perceived Completeness
When an LLM sees empty UI panels (monitoring, process status, collision detection), it fills them with plausible-looking content. A monitoring dashboard with `220 ± 5°C` looks more complete than one showing "N/A". The LLM isn't lying — it's pattern-matching on what a "complete" dashboard looks like, without checking whether the data source exists.

**Mitigation:** The plan explicitly instructs: "If something doesn't work, don't show it." The acceptance criteria check for fake data. The benchmark Test Case 7 verifies that errors are honest.

### Cause 3: Missing Domain Knowledge About What "Simulation" Means
In robotics, "simulation" means physics simulation (collision detection, deposition modeling, force feedback). In web development, "simulation" often means "animated replay." The LLM used the web-dev definition. The PyBullet code existed but the LLM didn't realize it needed to be wired into the service layer to constitute a real simulation.

**Mitigation:** The plan renames "Simulation" to "Trajectory Preview" to be honest about what it is. When PyBullet is connected (Phase 2+), it can be renamed back.

### Cause 4: ORNL Slicer 2 Is a Hard External Dependency
The LLM couldn't pip-install ORNL Slicer 2. So it built a mock that returns canned data. The mock lets tests pass, but it also means the LLM never tested real slicing. Everything downstream (waypoints, IK, export) was built against mock data.

**Mitigation:** The benchmark uses the mock for CI but Test Cases 1-5 verify the data structure and coordinate correctness. Even with mock data, we can verify "are the coordinates within physical bounds?" and "are joint angles non-zero?"

### Cause 5: No Acceptance Test Culture
The project had unit tests and integration tests but no test that said: "A user loads a cube, slices it, solves IK, and exports G-code — does the G-code contain the right coordinates?" Without this, the LLM could make every unit test pass while the E2E workflow was broken.

**Mitigation:** The benchmark IS the acceptance test. It tests the user journey, not the code paths.

---

## PART 6: REFERENCE LINKS AND SOURCES

These were consulted during plan development:

- **CuraEngine Test Suite:** https://github.com/Ultimaker/CuraEngine/tree/main/tests
- **CuraEngine Integration Tests:** https://github.com/Ultimaker/CuraEngine/tree/main/tests/integration
- **PrusaSlicer Test Data:** https://github.com/prusa3d/PrusaSlicer/tree/master/tests/data
- **SlicerTestModels (Community Benchmark Geometries):** https://github.com/Ghostkeeper/SlicerTestModels
- **SlicerTestModels Basic Shapes:** https://github.com/Ghostkeeper/SlicerTestModels/tree/master/basic
- **Multi-Axis Robotic Printing Workflow Paper:** https://www.mdpi.com/2306-5354/12/9/949
- **Spatial Printing with Continuous Fiber (Toolpath Verification):** https://arxiv.org/html/2311.17265v2
- **3DP Benchmark Model for Dimensional Accuracy:** https://strathprints.strath.ac.uk/68205/

---

*This plan should be loaded into the LLM agent's context at the start of the next session. The agent should treat the benchmark test as its primary deliverable and the corrective fixes as mandatory prerequisites.*
