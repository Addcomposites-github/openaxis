# Ungrounded Code Registry

This document tracks all code identified as "ungrounded" (LLM-generated custom
implementations without research citations or library backing) during the
February 2026 audit, along with their resolution status.

**Rule:** Every algorithm must either call a proven library function or cite a
specific research paper/textbook/standard. LLM-generated math without citations
is not acceptable.

---

## Deleted Code

### Slicing Module

| Code | File | Problem | Resolution |
|------|------|---------|------------|
| Custom trimesh.section() slicing pipeline | `planar_slicer.py` | Custom code substituting for ORNL Slicer 2 | Replaced with compas_slicer PlanarSlicer |
| Custom rotation-based angled slicing | `angled_slicer.py` | Rotate mesh, planar slice, rotate back — unvalidated | Deleted; raises NotImplementedError |
| Custom circle-generation radial slicing | `radial_slicer.py` | Parametric circles — no research citation | Deleted; raises NotImplementedError |
| Custom arc-length interpolation | `curve_slicer.py` | Linear interpolation instead of B-splines | Deleted; raises NotImplementedError |
| Custom helical toolpath generation | `revolved_slicer.py` | Gram-Schmidt with magic 0.9 threshold | Deleted; raises NotImplementedError |
| 8 custom infill patterns | `infill_patterns.py` | "Medial" pattern was 2 hardcoded perpendicular lines (fake Voronoi skeleton) | Deleted; raises NotImplementedError |
| Custom pyclipper contour offsetting | `contour_offset.py` | Wrapper around pyclipper — should be in compas_slicer | Deleted; raises NotImplementedError |
| Custom seam placement heuristics | `seam_control.py` | No citation for seam optimization strategy | Deleted; raises NotImplementedError |
| Custom lead-in/lead-out generation | `engage_disengage.py` | Custom arc/ramp generation without ISO 6983 compliance | Deleted; raises NotImplementedError |
| Custom support detection + generation | `support_generation.py` | Overhang detection valid approach, but clustering/generation ungrounded | Deleted; raises NotImplementedError |

### Motion Module

| Code | File | Problem | Resolution |
|------|------|---------|------------|
| scipy.optimize IK solver | `kinematics.py` (IKSolver) | Custom substitution for MoveIt2 IK | Deleted; raises NotImplementedError |
| Numerical Jacobian IK | `kinematics.py` (JacobianIKSolver) | Hardcoded orientation to zero (`jacobian[3:, i] = 0`) — position-only solver masquerading as 6-DOF | Deleted; raises NotImplementedError |
| Moving average trajectory smoothing | `planner.py` (TrajectoryOptimizer.smooth_trajectory) | Averaged joint angles — breaks at wrap boundaries (170deg -> -170deg averages to 0deg) | Deleted; raises NotImplementedError |
| Simple time parameterization | `planner.py` (TrajectoryOptimizer.time_parameterize) | distance/max_velocity — ignores acceleration, jerk, dynamics | Deleted; raises NotImplementedError |
| Stub returning fake [0.0] values | `external_axes.py` (compute_positioner_angles) | Returned [0.0] always, pretending to compute | Changed to raise NotImplementedError |
| Stub returning midpoint | `external_axes.py` (optimize_axis_position) | Returned midpoint of range, pretending to optimize | Changed to raise NotImplementedError |

### Process Plugins

| Code | File | Problem | Resolution |
|------|------|---------|------------|
| Heat input formula | `waam.py` (calculate_heat_input) | Q = V*I/(speed*1000) — missing arc efficiency factor (eta). 20-40% error. | Deleted; raises NotImplementedError |
| Deposition rate | `waam.py` (calculate_deposition_rate) | Magic 0.8 efficiency factor with no citation | Deleted; raises NotImplementedError |
| Welding parameter multipliers | `waam.py` (get_welding_parameters) | Magic 1.05x, 1.1x multipliers for infill — no empirical basis | Deleted; raises NotImplementedError |
| Cutting force model | `milling.py` (calculate_cutting_force) | `hardness * 3.0` specific cutting force — unvalidated | Deleted; raises NotImplementedError |
| MRR calculation | `milling.py` (calculate_material_removal_rate) | Simplified DOC * stepover * feed — missing chip thinning, tool engagement | Deleted; raises NotImplementedError |
| Spindle speed calculator | `milling.py` (calculate_optimal_spindle_speed) | Ignored material parameter (always used caller surface speed) | Deleted; raises NotImplementedError |
| Machining parameter multipliers | `milling.py` (get_machining_parameters) | Magic 1.2x, 0.8x multipliers — no empirical basis | Deleted; raises NotImplementedError |
| Extrusion amount calculator | `pellet.py` (calculate_extrusion_amount) | Assumed rectangular bead cross-section | Deleted; raises NotImplementedError |
| Print parameter multipliers | `pellet.py` (get_print_parameters) | Magic 0.8x, 1.2x multipliers — no empirical basis | Deleted; raises NotImplementedError |

### Frontend

| Code | File | Problem | Resolution |
|------|------|---------|------------|
| Newton-Raphson IK solver | `analyticalIK.ts` | Custom 6-DOF solver for ABB IRB 6700. Hardcoded wrist (j5=-(j2+j3)), magic initial guesses, failed for off-axis targets | Deleted; returns unreachable until backend API integration |

---

## Retained Code (Grounded)

These modules were reviewed and found to be properly grounded:

| Code | File | Grounding |
|------|------|-----------|
| COMPAS geometry operations | Throughout | compas library API calls |
| PyBullet simulation | `environment.py` | pybullet library API calls |
| PyBullet collision | `collision.py` | pybullet library API calls |
| URDF loading | Various | compas_robots library |
| SLERP interpolation | `planner.py` | scipy.spatial.transform.Slerp (well-known algorithm) |
| Linear joint interpolation | `planner.py` (JointPlanner) | numpy linspace — trivial data interpolation |
| Toolpath data structures | `toolpath.py` | Dataclasses — no algorithms |
| Process parameter validation | `waam.py`, `pellet.py`, `milling.py` | Range checks — no physics formulas |
| G-code generation | `gcode.py` | Vendor-specific output format — no custom math |
| Postprocessors | `postprocessor/` | Vendor-specific (RAPID, KRL, Fanuc) — format translation only |

---

## Documentation Lies Fixed

| Document | False Claim | Correction |
|----------|-------------|------------|
| README.md | Phases 1-3 "Complete" | Phases 1-3 are "Rebuilding" / "~50%" |
| README.md | Technology table showed all libraries as integrated | Added Status column showing actual integration state |
| CLAUDE.md | "Slicing: ORNL Slicer 2 integration" | ORNL Slicer 2 is NOT integrated (C++ app). Using compas_slicer |
| CLAUDE.md | "Motion Planning: MoveIt2 via ROS2 Humble" | MoveIt2 NOT integrated. Using compas_fab stubs |
| CLAUDE.md | "Simulation: pybullet_industrial" | pybullet_industrial imported but not fully integrated |
| system-architecture.md | Listed `ornl_slicer.py` | File does NOT exist |
| system-architecture.md | Listed `moveit_bridge.py` | File does NOT exist |
| system-architecture.md | Listed `compas_slicer.py` | File does NOT exist (slicing is in `planar_slicer.py`) |
| system-architecture.md | Listed 7 simulation files | Only `environment.py` exists |
