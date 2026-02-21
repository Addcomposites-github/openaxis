# OpenAxis — Bug & Improvement Kanban

> **How to use:** Say "let's take IK-001" and we pull it into **In Progress**.
> When done it moves to **Done** with a fix note.
>
> **Status key:** 🔴 Blocked · 🟡 In Progress · 🟢 Done · ⚪ Backlog
>
> **Suggested order:** Fix blockers first so later items can actually be tested.
> See the **Recommended Fix Order** section at the bottom.

---

## 🟡 In Progress

| ID | Area | Title | Notes |
|----|------|-------|-------|
| BUG-001 | IK / TCP | **TCP offset (x,y,z,rx,ry,rz) not applied correctly** | Fix committed 2026-02-21. Cannot be acceptance-tested until IK-002 (server dropout) is resolved — that is the next card to take. |

---

## ⚪ Backlog — Backend / Server Stability  ← Fix these first

| ID | Priority | Title | Detail |
|----|----------|-------|--------|
| BE-003 | **Critical** | **Backend goes offline during long IK computation — blocks all testing** | The FastAPI server runs IK synchronously on the main thread. While solving 1000+ points, health-check polls time out and the frontend shows "backend not reachable" and drops the session. Fix: run IK in a background thread (`asyncio.to_thread` already used in stream endpoint — apply same pattern to the batch endpoint and ensure the health-check endpoint is always served). This is a prerequisite before BUG-001 can be acceptance-tested. |
| IK-001 | **Critical** | **IK solves ALL points before playback can start — blocks UI entirely** | All waypoints are batched and solved before the play button is usable. If even one fails the whole solve is reported as failed. Fix: (a) use the existing SSE streaming endpoint (`/solve-trajectory-stream`) and start playback after the first chunk returns, (b) mark individual unreachable points as yellow warnings not a hard stop, (c) never block the UI thread while IK runs. Must be fixed before production use. |
| IK-002 | **Critical** | **"Backend not reachable" banner fires mid-computation** | Consequence of BE-003. Health-check polls fail during IK computation. Even if BE-003 is fixed, suppress this banner while a known long operation (`solveTrajectoryIK`) is in flight — don't show "server down" when the server is simply busy. |
| BE-002 | Medium | **Several endpoints return HTTP 200 + empty data instead of HTTP 503** | Silent failures. Should return 503 so the frontend shows a proper error. |
| BE-001 | Low | **Monitoring dashboard shows fake/random data** | Temperature, flow rate, pressure panels show hardcoded random values. Show `--` / "Not connected" until hardware is present (Phase 4). |

---

## ⚪ Backlog — Project / Session Management  ← Fix these second

| ID | Priority | Title | Detail |
|----|----------|-------|--------|
| UI-011 | **Critical** | **No project save / load / rename** | "Workspace" label at the top is not editable. No save button. No open-project dropdown. Need: (a) click workspace name to rename inline, (b) a Save button that writes current state to disk, (c) a dropdown/menu to open a different project. Auto-save every ~30 s as a fallback. |
| UI-012 | High | **Clicking "Save" in Setup jumps the user to the next tab** | Save should save and stay. No navigation side-effects. Show a brief "Saved ✓" confirmation in place and nothing else. |
| UI-002 | High | **Slicer parameters reset to defaults on tab switch or reload** | Layer height, wall count, infill, seam, etc. should persist in project state and be restored exactly when returning to the tab. Resolved by UI-011 (project save), but parameters should at minimum be held in Zustand store across tab changes even before save is implemented. |
| UI-001 | High | **Tab switch resets simulation state** | IK result, trajectory playback position, joint angles all discarded on tab change. Should survive tab navigation. Zustand store already exists — state just needs to not be cleared on unmount. |

---

## ⚪ Backlog — UI / Layout

| ID | Priority | Title | Detail |
|----|----------|-------|--------|
| UI-003 | Medium | **Process selector appears in two places (Setup + Process tab)** | One canonical location: Process tab owns process type. TCP Setup tab owns tool geometry only. Remove duplicate from Setup. |
| UI-004 | Medium | **Robot base position poorly labelled and hard to find** | Inputs exist but labelled ambiguously. Needs clear label "Robot Base Position (world frame, mm)" in a named sub-section of Setup. |
| UI-005 | Medium | **Setup tab too dense** | Collapsible sections (Robot Cell / End Effector / Work Frame). Only the active section expanded by default. |
| UI-006 | Medium | **No toggle to hide original geometry in Toolpath / Simulation view** | Raw mesh stays visible while viewing slices, making toolpath lines hard to read. Needs a per-object visibility toggle (eye icon) in the 3D view header. |
| UI-007 | Medium | **Quality score / joint limit / singularity panels take too much space** | Fold these into a collapsible "Diagnostics" accordion. Collapsed by default. |
| UI-008 | Low | **No coordinate-system selector for live TCP readout** | TCP position shown in one implicit frame. Should be a dropdown: World / Robot Base / Work Frame. Should update in real time during playback — no need to switch to Manual mode to see it. |
| UI-009 | Low | **Jog panel only accessible in Manual mode** | Jogging and home-position setter should also be a collapsible panel in Simulation mode. That is where the user actually sees the robot and wants to set home. |
| UI-010 | Low | **Work frame / workbench coordinate frame missing** | Only World and Robot Base exist. A user-defined Work Frame (origin on build plate) is needed for meaningful TCP readout and for positioner work. |

---

## ⚪ Backlog — IK / Simulation

| ID | Priority | Title | Detail |
|----|----------|-------|--------|
| IK-003 | Low | **Home position set in Setup tab, not Simulation tab** | Should be settable from Simulation tab: jog robot to desired pose, press "Set as Home". |

---

## ⚪ Backlog — Slicer

| ID | Priority | Title | Detail |
|----|----------|-------|--------|
| SL-002 | High | **Wall count minimum is 3 regardless of user input** | User sets 1 wall, always gets 3. Either a hardcoded floor in `PlanarSlicer` or the UI value is not reaching the slicer. Needs: trace UI field → API param → slicer constructor. |
| SL-001 | High | **No brim / raft / skirt support** | Essential for large-format WAAM/pellet. Current `PlanarSlicer` has no concept of these. |
| SL-003 | Medium | **Seam control not exposed in UI** | `PlanarSlicer` has `seam_mode/shape/angle` params. UI exposes only a subset. Full seam controls + visual indicator needed. |
| SL-004 | Medium | **Point density / waypoint spacing not user-controllable** | User cannot set max waypoint spacing (mm). Directly affects IK load and part quality. |
| SL-005 | High | **PlanarSlicer too limited — evaluate replacement** | No brim/raft, min 3 walls, no variable layer height. Candidates: (a) **compas_slicer** (already in stack), (b) **CuraEngine** subprocess, (c) **PrusaSlicer** CLI. This is a sub-project. |
| SL-006 | Low | **Non-planar slicers appear in UI but raise NotImplementedError** | Grey them out with a "Phase 2" tooltip or remove until implemented. |

---

## ⚪ Backlog — Post-Processors / Export

| ID | Priority | Title | Detail |
|----|----------|-------|--------|
| PP-001 | Medium | **tcpOffset not passed to export endpoint** | Post-processors read `toolpath_data['tcpOffset']` but the export request doesn't inject the UI tool config. Still defaults to Z=150mm. Fix: export request must carry `tcpOffset` from TCPSetupPanel. |
| PP-002 | Low | **RAPID robot configuration field hardcoded `[0,0,0,0]`** | `cf` data in robtarget should reflect actual arm configuration to avoid flips. |

---

## 🟢 Done

| ID | Title | Fixed | Notes |
|----|-------|-------|-------|
| BUG-TCP-ROT | **TCP rotation (rx,ry,rz) silently dropped** | 2026-02-21 | Full 6DOF SE3 in `_solve_rtb`, `forward_kinematics`, `inverse_kinematics`. |
| BUG-TCP-IK-CLEAR | **`inverse_kinematics()` always cleared tool offset** | 2026-02-21 | Was `robot.tool = SE3()` unconditionally. Now uses `tcp_offset` param. |
| BUG-NORMAL-IK | **IK target orientation hardcoded RPY(0,180,0) for all points** | 2026-02-21 | Now uses per-waypoint slicing plane normal via `_normal_to_SE3()`. |
| BUG-NORMAL-PP | **Post-processor frame orientation hardcoded** | 2026-02-21 | `normal_to_zyx_euler()` used in RAPID/KRL/Fanuc. `[0,0,-1,0]` / `B 180` gone. |
| BUG-FRONTEND-RX | **SimulationPanel sent rx=ry=rz=0 to IK** | 2026-02-21 | Reads `endEffectorOffset[3,4,5]`, passes full 6DOF to all three IK calls. |
| BUG-NORMALS-FLOW | **Waypoint normals not flowing through pipeline** | 2026-02-21 | `toolpath_service` → `simulation_service` → `Waypoint` type → frontend → IK. |

---

## Recommended Fix Order

Work through these top-to-bottom. Each one unblocks the next.

```
1. BE-003  Backend thread safety / health-check survives IK computation
           → Without this nothing can be reliably tested

2. IK-001  Streaming IK + start playback from first chunk
   IK-002  Suppress false "server down" banner during computation
           → Together these make IK usable on real parts

3. BUG-001 Accept TCP offset result (needs #1 and #2 to test)

4. UI-011  Project save / load / rename
   UI-012  Save button must not auto-navigate
   UI-002  Parameters persist across tab switches
   UI-001  Simulation state persists across tab switches
           → These four are daily friction; do them as a batch

5. SL-002  Wall count floor bug (quick win — 1–2 hours)
   SL-005  Evaluate slicer replacement (sub-project, plan first)

6. UI-003 → UI-010  UI polish pass (can be done incrementally)
```
