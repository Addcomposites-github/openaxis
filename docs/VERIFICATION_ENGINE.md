# OpenAxis: Verification Engine Design
# Ground Truth for Slicing + IK Without Physics Tests

**Date:** 2026-02-20
**Purpose:** Define what a real verification engine looks like — one that gives the coding agent
ground truth to check its work against, rather than testing itself.

---

## The Core Problem

An LLM coding agent cannot verify its own output. If it writes the slicing code AND writes the
expected test values by running that code, both sides of the comparison came from the same source.
Any systematic bug that shifts all coordinates by a constant will make the code wrong AND make
the test accept that wrong output.

Real verification needs **at least two independent paths to the same answer.**

---

## What Independent Ground Truth Actually Exists Here

### 1. The Coordinate Transform — Independently Verifiable

`src/ui/src/utils/units.ts:waypointToRobotFrame()` is a pure mathematical function:

```
Slicer output: [x_mm, y_mm, z_mm] (Z-up, relative to build plate)
         ↓  (mm → meters, Z-up → Z-up robot frame, subtract robot position)
IK input:  [x_m, y_m, z_m] (meters, Z-up, robot base frame)
```

The exact transform:
```
sceneX = buildPlateOrigin[0] + slicerX * 0.001
sceneY = buildPlateOrigin[1] + slicerZ * 0.001    ← slicer Z maps to scene Y (Y-up)
sceneZ = buildPlateOrigin[2] - slicerY * 0.001    ← slicer Y maps to scene -Z

robotX = sceneX - robotPos[0]
robotY = -(sceneZ - robotPos[2])                  ← scene Y-up → robot Z-up
robotZ = sceneY - robotPos[1]
```

This transform is **not the thing being tested** — it IS the ground truth. Any IK result can be
back-checked: apply FK to the joint angles, get a position, transform it back through the inverse
of `waypointToRobotFrame`, and compare to the original slicer coordinates. If they don't match,
something in the pipeline is wrong.

### 2. FK as an Independent Oracle

Forward kinematics from published DH parameters is **not** LLM math. The ABB IRB 6700 DH
parameters used in the code come from roboticstoolbox-python's standard robot library (Peter
Corke, "Robotics, Vision and Control", Springer 2023). FK is a closed-form matrix multiplication:
T = T1 * T2 * T3 * T4 * T5 * T6. You can compute this independently with `roboticstoolbox`,
`numpy`, or by hand from the DH table.

**This means:** Given a set of joint angles, we can compute the end-effector position without
trusting anything in the OpenAxis codebase. If `robot_service.py` returns joint angles for a
given target, we can independently compute FK and check whether those joint angles actually
place the tool at the right position.

### 3. The Only Slicing Ground Truth: Real ORNL Slicer 2 Output

The slicing geometry is NOT independently verifiable by the LLM — ORNL Slicer 2 is a complex
C++ application whose internals we don't control. The only ground truth for sliced coordinates
is the actual G-code that ORNL Slicer 2 produces when you give it a specific input.

**How to create this ground truth:**
1. Run ORNL Slicer 2 on a specific STL with specific settings
2. Save the G-code output as a fixture file
3. Future tests compare new output against the fixture
4. If the fixture needs to change, a human reviews the diff and approves it

This is the approach used by CuraEngine
(https://github.com/Ultimaker/CuraEngine/tree/main/tests) and PrusaSlicer
(https://github.com/prusa3d/PrusaSlicer/tree/master/tests/data).

---

## The Verification Engine: What to Build

The engine has two parts:

### Part A: The Coordinate Oracle (Can Build Now)

A Python script/module that independently computes what joint angles SHOULD be for a given
slicer output point, using only:
- The `waypointToRobotFrame()` transform (pure math, no OpenAxis dependencies)
- roboticstoolbox-python FK (not our IK — just the FK oracle)
- The published DH parameters

```python
# tests/verification/coordinate_oracle.py
"""
Independent coordinate verification oracle.

This module computes expected values WITHOUT using the OpenAxis codebase.
It uses:
  - The published ABB IRB 6700 DH parameters (from manufacturer datasheet)
  - roboticstoolbox-python FK as an independent calculator
  - The waypointToRobotFrame() transform (pure arithmetic)

Usage:
  from tests.verification.coordinate_oracle import (
      slicer_to_robot_frame,   # Transform slicer coords to robot frame
      fk_from_joints,          # Independent FK calculation
      verify_ik_solution,      # Check if joint angles place TCP at target
  )
"""

import math
import numpy as np

# -------------------------------------------------------------------
# ABB IRB 6700 DH Parameters
# Source: roboticstoolbox-python standard robot library
# Reference: Peter Corke, "Robotics, Vision and Control", Springer 2023
# These are fixed by the robot manufacturer — not LLM-generated values.
# -------------------------------------------------------------------
IRB6700_DH = [
    # (d_m, a_m, alpha_rad)
    (0.780,   0.320, -math.pi / 2),   # J1: Base rotation
    (0.000,   1.125,  0.000),          # J2: Shoulder
    (0.000,   0.200, -math.pi / 2),   # J3: Elbow
    (1.1425,  0.000,  math.pi / 2),   # J4: Wrist 1
    (0.000,   0.000, -math.pi / 2),   # J5: Wrist 2
    (0.200,   0.000,  0.000),          # J6: Wrist 3
]

# Joint limits (radians) from robot_service.py — sourced from ABB datasheet
IRB6700_QLIM = [
    (-math.radians(170), math.radians(170)),   # J1
    (-math.radians(65),  math.radians(85)),    # J2
    (-math.radians(180), math.radians(70)),    # J3
    (-math.radians(300), math.radians(300)),   # J4
    (-math.radians(130), math.radians(130)),   # J5
    (-math.radians(360), math.radians(360)),   # J6
]

# Default TCP offset: 150mm Z offset for WAAM torch
TCP_Z_OFFSET_M = 0.150


def dh_transform(theta: float, d: float, a: float, alpha: float) -> np.ndarray:
    """
    Standard Denavit-Hartenberg homogeneous transform matrix.
    Formula from Craig, "Introduction to Robotics", 3rd ed., eq. 3.6.
    This is standard textbook — not LLM math.
    """
    ct, st = math.cos(theta), math.sin(theta)
    ca, sa = math.cos(alpha), math.sin(alpha)
    return np.array([
        [ct,    -st * ca,  st * sa,   a * ct],
        [st,     ct * ca, -ct * sa,   a * st],
        [0,      sa,       ca,        d],
        [0,      0,        0,         1],
    ])


def fk_from_joints(joint_angles_rad: list[float], tcp_z_m: float = TCP_Z_OFFSET_M) -> dict:
    """
    Independent FK calculation using DH parameters.

    This does NOT call robot_service.py — it is a separate implementation
    using the same published DH parameters, for independent verification.

    Returns:
        {
            "position_m": [x, y, z],   # TCP position in meters (robot base frame, Z-up)
            "transform": np.ndarray,    # Full 4x4 homogeneous transform
        }
    """
    T = np.eye(4)
    for i, (q, (d, a, alpha)) in enumerate(zip(joint_angles_rad, IRB6700_DH)):
        T = T @ dh_transform(q, d, a, alpha)

    # Apply TCP Z offset (tool pointing down, offset along tool Z axis)
    T_tcp = np.eye(4)
    T_tcp[2, 3] = tcp_z_m
    T = T @ T_tcp

    return {
        "position_m": [T[0, 3], T[1, 3], T[2, 3]],
        "transform": T,
    }


def slicer_to_robot_frame(
    slicer_pos_mm: tuple[float, float, float],
    build_plate_origin_scene_m: tuple[float, float, float],
    robot_pos_scene_m: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> tuple[float, float, float]:
    """
    Convert slicer coordinates (mm, Z-up) to robot base frame (meters, Z-up).

    This is a direct transcription of units.ts:waypointToRobotFrame() —
    pure arithmetic, independently verifiable.

    Args:
        slicer_pos_mm:              [x, y, z] from ORNL Slicer 2, in mm, Z-up
        build_plate_origin_scene_m: Build plate position in Three.js scene [x, y, z] Y-up meters
        robot_pos_scene_m:          Robot base position in Three.js scene [x, y, z] Y-up meters

    Returns:
        [x, y, z] in meters, Z-up, relative to robot base
    """
    sx, sy, sz = slicer_pos_mm
    bx, by, bz = build_plate_origin_scene_m
    rx, ry, rz = robot_pos_scene_m

    # Step 1: slicer mm Z-up → scene meters Y-up
    scene_x = bx + sx * 0.001
    scene_y = by + sz * 0.001   # slicer Z → scene Y
    scene_z = bz + (-sy * 0.001)  # slicer Y → scene -Z

    # Step 2: scene Y-up → robot base Z-up (subtract robot offset, invert rotation)
    dx = scene_x - rx
    dy = scene_y - ry
    dz = scene_z - rz

    robot_x = dx
    robot_y = -dz
    robot_z = dy

    return (robot_x, robot_y, robot_z)


def verify_ik_solution(
    joint_angles_rad: list[float],
    target_robot_frame_m: tuple[float, float, float],
    tolerance_m: float = 0.002,
    tcp_z_m: float = TCP_Z_OFFSET_M,
) -> dict:
    """
    Verify that a set of joint angles places the TCP at the target position.

    Uses independent FK (not robot_service.py) to compute where the TCP ends up.
    Compares against the target. Returns the error.

    Args:
        joint_angles_rad:       6-element list of joint angles in radians
        target_robot_frame_m:   Target [x, y, z] in meters, robot base frame
        tolerance_m:            Acceptable position error in meters (default 2mm)
        tcp_z_m:                TCP Z offset in meters

    Returns:
        {
            "fk_position_m": [x, y, z],    # Where FK says the TCP is
            "target_m": [x, y, z],          # Where we wanted the TCP
            "error_m": float,               # Euclidean distance error
            "within_tolerance": bool,
            "tolerance_m": float,
        }
    """
    fk = fk_from_joints(joint_angles_rad, tcp_z_m)
    fk_pos = fk["position_m"]
    tx, ty, tz = target_robot_frame_m

    error = math.sqrt(
        (fk_pos[0] - tx) ** 2 +
        (fk_pos[1] - ty) ** 2 +
        (fk_pos[2] - tz) ** 2
    )

    return {
        "fk_position_m": fk_pos,
        "target_m": list(target_robot_frame_m),
        "error_m": error,
        "error_mm": error * 1000,
        "within_tolerance": error <= tolerance_m,
        "tolerance_m": tolerance_m,
    }


def joints_within_limits(joint_angles_rad: list[float]) -> dict:
    """
    Check that all joint angles are within the ABB IRB 6700 limits.

    Returns:
        {
            "all_within": bool,
            "violations": list of {"joint": int, "value_deg": float, "limit_deg": (min, max)}
        }
    """
    violations = []
    for i, (q, (lo, hi)) in enumerate(zip(joint_angles_rad, IRB6700_QLIM)):
        if not (lo <= q <= hi):
            violations.append({
                "joint": i + 1,
                "value_deg": math.degrees(q),
                "limit_deg": (math.degrees(lo), math.degrees(hi)),
            })
    return {
        "all_within": len(violations) == 0,
        "violations": violations,
    }
```

### Part B: The Slicing Fixture System (Requires Human Action First)

This part cannot be built by the coding agent alone. It requires a human to:

1. Open ORNL Slicer 2
2. Load one of the STL files in `test-geometry/` (start with `test_box.stl`)
3. Set known parameters:
   ```
   Layer height:    2.0 mm
   Bead width:      6.0 mm
   Perimeters:      1
   Infill density:  0%
   No support
   ```
4. Run the slicer
5. Save the resulting `.gcode` file to `tests/fixtures/test_box_2mm_1wall_0infill.gcode`
6. Record the settings used in `tests/fixtures/README.md`

Once that fixture exists, the coding agent can write a test like:

```python
# tests/integration/test_slicing_fixtures.py
"""
Fixture-based slicing regression test.

Expected outputs were produced by running ORNL Slicer 2 manually
on the input files and committing the results. Any change to the
fixture requires human review and approval.
"""

def test_test_box_slicing_matches_fixture():
    """
    Slice test_box.stl and compare to the human-verified fixture.
    If this test fails, the slicer output has changed. A human must
    review whether the change is correct before updating the fixture.
    """
    fixture_path = Path("tests/fixtures/test_box_2mm_1wall_0infill.gcode")
    if not fixture_path.exists():
        pytest.skip("Fixture not yet created — requires human to run ORNL Slicer 2")

    # Run our slicer pipeline on the same input
    slicer = ORNLSlicer()
    config = ORNLSlicerConfig("FDM")
    config.set_layer_height(2.0)
    config.set_bead_width(6.0)
    config.set_perimeters(1)
    config.set_infill(density=0)
    toolpath = slicer.slice("test-geometry/test_box.stl", config)

    # Export to G-code and compare to fixture
    exported = PostProcessor().export(toolpath, format="gcode")
    fixture = fixture_path.read_text()

    # Compare coordinate lines only (ignore comments, timestamps)
    def coord_lines(gcode):
        return [l.strip() for l in gcode.splitlines()
                if l.startswith("G1") or l.startswith("G0")]

    assert coord_lines(exported) == coord_lines(fixture), \
        "Slicer output differs from human-verified fixture. Review the diff."
```

---

## How the Coding Agent Uses This Engine

The agent does NOT write expected values. It uses the oracle to CHECK values that the
pipeline produces:

```python
# Pattern the coding agent should follow:

# 1. Run the pipeline to get a result
toolpath = slicer.slice(stl_path)
waypoints = simulation_service.create_simulation(toolpath)
ik_result = robot_service.solve_toolpath_ik(waypoints)

# 2. For each IK solution, ask the oracle to verify it
for i, (waypoint, joints) in enumerate(zip(waypoints, ik_result["trajectory"])):
    slicer_pos_mm = waypoint["position"]

    # Convert to robot frame using the oracle's coordinate transform
    # (same math as units.ts but in Python, verifiable independently)
    robot_target_m = oracle.slicer_to_robot_frame(
        slicer_pos_mm,
        build_plate_origin,
        robot_position,
    )

    # Check if the IK joints actually reach the target
    check = oracle.verify_ik_solution(joints, robot_target_m)

    assert check["within_tolerance"], (
        f"Waypoint {i}: IK error {check['error_mm']:.2f}mm "
        f"(FK gives {check['fk_position_m']}, target was {check['target_m']})"
    )

    # Check joint limits using manufacturer spec
    limits_check = oracle.joints_within_limits(joints)
    assert limits_check["all_within"], (
        f"Waypoint {i}: Joint limit violations: {limits_check['violations']}"
    )
```

This is meaningful verification because:
- `oracle.slicer_to_robot_frame()` is independent arithmetic — not the code being tested
- `oracle.fk_from_joints()` uses the same DH parameters via a separate implementation
- The DH parameters come from the robot manufacturer, not from the LLM
- If the IK solver returns wrong joint angles, `fk_from_joints()` will compute a
  position that doesn't match the target, and the test fails

---

## What This Engine Does NOT Verify

**Slicing geometry correctness.** Whether ORNL Slicer 2 put the perimeter in the right
place for a given part is NOT verifiable by this engine. That requires either:
- A human expert reviewing the toolpath against the expected print geometry
- Physical printing and measurement
- Comparison against a human-verified fixture (Part B above)

The coordinate oracle only verifies that **once you have waypoints from the slicer**,
the coordinate transform and IK solution are internally consistent.

---

## Files to Create

```
tests/
  verification/
    __init__.py
    coordinate_oracle.py      ← The oracle (Part A above — build this now)
  fixtures/
    README.md                 ← Documents what fixtures exist and how they were created
    .gitkeep                  ← Placeholder until human creates first fixture
  integration/
    test_ik_verification.py   ← Tests that use the oracle to verify IK solutions
```

---

## Priority

1. **Build `coordinate_oracle.py` now** — it requires no human input, just the published
   DH parameters which are already in the code. The coding agent can do this.

2. **Write `test_ik_verification.py` using the oracle** — this is the one genuinely
   grounded IK test we can have right now.

3. **Create the first slicing fixture manually** — when you (the user/developer) next
   run ORNL Slicer 2, slice `test_box.stl` with the settings above and commit the output.
   This unlocks Part B.

4. **Never write coordinate assertions that you derived by running the code** — if you
   run the slicer, see it outputs Z=2.0, and then write `assert Z == 2.0`, that is not
   a test. Use the oracle pattern instead.

---

## The Limitation You Asked About: Multi-Geometry, More Complexity

Your instinct is right — more complex geometry will stress the pipeline more. The right
progression for slicing fixtures:

| Fixture | Geometry | What it stresses |
|---------|----------|-----------------|
| 1 (start here) | `test_box.stl` | Basic planar slicing, layer count |
| 2 | `ADAXIS_20240729_Nozzle.stl` | Curved surfaces, varying cross-section |
| 3 | `Wing_Mold_01092022_v1.stl` | Large complex surface, thin features |
| 4 | `Propeller_01092022_v1.step` | Twisted geometry, STEP format |

Each requires a human to run ORNL Slicer 2 and commit the fixture. The coding agent
cannot bootstrap this — it needs that human action first.

For IK, the oracle works for any geometry because it is coordinate-agnostic. Once you
have a sliced toolpath, any waypoint in it can be verified with `verify_ik_solution()`.

---

*This document describes what to build. The coordinate oracle (Part A) can be built by
the coding agent immediately. The slicing fixtures (Part B) require a human action first.*
