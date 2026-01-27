# OpenAxis - Robot Simulation Focus Session

**Date:** 2026-01-27
**Goal:** Implement industrial-grade robotic CAM system with collision detection and motion validation

---

## Core Mission

Build a **complete robotic manufacturing workflow** comparable to industrial CAM systems:

```
Import Geometry → Position → Slice → Robot Simulation → Collision Check → Export Program
```

**NOT** a geometry viewer. **NOT** a slicer with UI polish.
**YES** a real robotic manufacturing system with motion planning and safety validation.

---

## Current State: What Works

### ✅ Geometry Pipeline (Complete)
- Import: STL/OBJ files
- Placement: Auto-center on 1000x1000mm build plate
- Transform: Move/rotate/scale with 3D controls
- Validation: Build volume checking

### ✅ Slicing Pipeline (Complete)
- Parameters: Layer height, extrusion width, walls, infill
- Backend: HTTP API ready (`http://localhost:8080`)
- Output: Toolpath segments with layer data
- Export: G-code generation

### ✅ Visualization (Complete)
- 3D scene with build plate
- Toolpath rendering (color-coded by type)
- Layer-by-layer animation
- Statistics dashboard

### ✅ Backend Foundation (Complete)
- Motion planning modules (`src/openaxis/motion/`)
- Kinematics stubs (`kinematics.py`, `planner.py`)
- Collision detection stub (`collision.py`)
- Process plugins (WAAM, pellet, milling)

### ✅ Test Suite (Complete)
- 93/93 backend tests passing
- System diagnostics: 21/21 checks passing

---

## Critical Gap: No Robot Simulation

### ❌ What's Missing (THE MAIN GOAL)

**1. Robot Model**
- No robot arm visible in workspace
- No joint visualization
- No end effector representation

**2. Motion Simulation**
- Toolpath exists but robot doesn't follow it
- No inverse kinematics calculation
- No pose-by-pose animation
- No reachability checking

**3. Collision Detection**
- No robot self-collision check
- No robot vs part collision
- No robot vs build plate collision
- No safety validation

**4. Singularity & Limits**
- No joint limit checking
- No singularity detection
- No manipulability analysis
- No workspace validation

**5. External Axes**
- No positioner/turntable
- No linear track
- No coordinated motion

---

## Project Structure (Clean)

```
openaxis/
├── src/
│   ├── backend/
│   │   ├── server.py                    # HTTP API server
│   │   ├── geometry_service.py          # Geometry operations
│   │   └── toolpath_service.py          # Slicing & toolpath
│   │
│   ├── openaxis/
│   │   ├── motion/
│   │   │   ├── kinematics.py            # IK/FK (stubs - NEEDS WORK)
│   │   │   ├── planner.py               # Motion planning (stubs - NEEDS WORK)
│   │   │   ├── collision.py             # Collision detection (stub - NEEDS WORK)
│   │   │   └── external_axes.py         # External axes (stub - NEEDS WORK)
│   │   │
│   │   ├── processes/                   # Process-specific logic
│   │   ├── simulation/                  # Simulation setup
│   │   └── slicing/                     # Toolpath generation
│   │
│   └── ui/
│       ├── src/
│       │   ├── pages/
│       │   │   ├── GeometryEditor.tsx   # Geometry manipulation ✅
│       │   │   ├── ToolpathEditor.tsx   # Toolpath visualization ✅
│       │   │   └── Simulation.tsx       # Robot simulation (EMPTY - PRIORITY)
│       │   │
│       │   ├── components/
│       │   │   ├── BuildPlate.tsx       # Build plate ✅
│       │   │   ├── ToolpathRenderer.tsx # Toolpath rendering ✅
│       │   │   └── [MISSING] RobotModel.tsx       # ← NEED THIS
│       │   │   └── [MISSING] RobotSimulation.tsx  # ← NEED THIS
│       │   │
│       │   └── api/
│       │       └── toolpath.ts          # Backend API client ✅
│       │       └── [MISSING] robot.ts   # ← NEED THIS
│       │
│       └── public/
│           └── [MISSING] robots/        # ← NEED URDF/GLTF models
│
├── docs/
│   ├── ROADMAP.md                       # Full project plan
│   └── archive/
│       └── REFOCUSED_PRIORITIES.md      # Why we refocused on robots
│
├── examples/                            # Demo scripts
├── scripts/                             # Utilities
└── tests/                               # Test suite
```

---

## Implementation Priority (No Distractions)

### Phase 1: Robot Visualization (IMMEDIATE)
**Goal:** See a robot arm in the workspace

**Tasks:**
1. Find/acquire robot model (URDF or GLTF)
   - ABB IRB 6700 (preferred)
   - Or generic 6-axis industrial robot
2. Load robot into `GeometryEditor.tsx` or create dedicated `Simulation.tsx`
3. Position robot next to build plate
4. Render robot with proper joint hierarchy
5. Add manual joint sliders for testing

**Deliverable:** Robot visible and manually controllable

**Time:** 1-2 days

---

### Phase 2: Inverse Kinematics (CORE)
**Goal:** Calculate joint angles to reach toolpath points

**Tasks:**
1. Integrate COMPAS FAB IK solver (backend)
   - Create `/api/robot/ik` endpoint
   - Input: target pose (position + orientation)
   - Output: joint angles [J1, J2, J3, J4, J5, J6]
2. For each toolpath point:
   - Call IK service
   - Get joint configuration
   - Handle IK failures (unreachable)
3. Cache joint angles for entire toolpath
4. Frontend: Call IK API for toolpath

**Deliverable:** Joint angles calculated for entire toolpath

**Time:** 2-3 days

---

### Phase 3: Motion Simulation (CORE)
**Goal:** Robot animates following toolpath

**Tasks:**
1. Animate robot through joint configurations
   - Interpolate between poses
   - Update robot model joints
2. Add simulation controls:
   - Play/pause
   - Speed control (0.25x - 4x)
   - Step forward/backward
   - Jump to specific point
3. Sync with toolpath layer display
4. Show end effector path trace

**Deliverable:** Robot follows toolpath in 3D

**Time:** 2-3 days

---

### Phase 4: Collision Detection (CRITICAL SAFETY)
**Goal:** Detect collisions during motion

**Tasks:**
1. Backend collision checking:
   - Create `/api/robot/check-collision` endpoint
   - Check robot self-collision
   - Check robot vs part
   - Check robot vs build plate
2. Visual feedback:
   - Red highlighting for collisions
   - Display collision points
   - Stop simulation at collision
3. Pre-validate entire toolpath

**Deliverable:** Collision warnings before execution

**Time:** 2-3 days

---

### Phase 5: Singularity & Reachability (SAFETY)
**Goal:** Validate motion feasibility

**Tasks:**
1. Check joint limits for each pose
2. Calculate manipulability index
3. Detect singularities
4. Color-code toolpath by feasibility:
   - Green: Safe
   - Yellow: Near limits
   - Red: Unreachable/singular
5. Warn user before simulation

**Deliverable:** Motion validation complete

**Time:** 2-3 days

---

### Phase 6: External Axes (ADVANCED)
**Goal:** Expand workspace with positioner/track

**Tasks:**
1. Add rotary table model
2. Implement coordinated motion planning
3. Distribute motion between robot + external axis
4. Optimize to avoid joint limits

**Deliverable:** Multi-axis coordination

**Time:** 3-4 days

---

## Technology Stack

### Backend
- **Python 3.10+**
- **COMPAS** + **COMPAS FAB** - Kinematics, motion planning
- **Flask/FastAPI** - HTTP server (already have Flask-like server)
- **python-fcl** (optional) - Advanced collision detection

### Frontend
- **React** + **TypeScript**
- **Three.js** - 3D rendering
- **@react-three/fiber** - React Three.js integration
- **urdf-loader** or **@gltf-loader** - Robot model loading

### Robot Models
- **URDF** (Universal Robot Description Format) - Preferred
- **GLTF** - Alternative, easier to load

---

## Key Decisions

### Robot Model Choice
**Recommendation:** ABB IRB 6700
**Why:**
- Large payload (150-300kg)
- Common in manufacturing
- URDF available from ROS Industrial
- Good for WAAM/large-scale additive

**Alternative:** Generic 6-axis robot (faster to prototype)

### IK Solver
**Recommendation:** COMPAS FAB with ROS backend
**Why:**
- Already in tech stack
- Proven industrial solution
- Handles complex kinematics
- Free and open-source

### Collision Detection
**Start with:** Three.js bounding box/raycasting (simple, fast)
**Upgrade to:** python-fcl (accurate mesh-based collision)

---

## Success Metrics

**Minimum Viable Product (MVP):**
1. ✅ Import geometry
2. ✅ Place on build plate
3. ✅ Slice to toolpath
4. ⏳ **Robot visible in workspace** ← NEXT
5. ⏳ **Robot follows toolpath**
6. ⏳ **Collision warnings**
7. ⏳ **Reachability validation**
8. ⏳ **Export robot program** (RAPID/KRL)

**When we achieve this, we have an industrial-grade CAM system.**

---

## What We Will NOT Do (Avoid Distractions)

❌ **UI polish** - No color themes, no fancy buttons
❌ **Documentation** - Only essential docs
❌ **Minor bug fixes** - Unless blocking core functionality
❌ **Feature creep** - Stick to the workflow
❌ **Optimization** - Make it work first
❌ **Testing every detail** - Focus on integration tests

**Rule:** If it doesn't directly contribute to robot simulation, we skip it.

---

## Immediate Next Steps

### Step 1: Acquire Robot Model (Today)
- [ ] Search for ABB IRB 6700 URDF
- [ ] Check ROS Industrial repository
- [ ] Or find generic 6-axis robot GLTF
- [ ] Test loading in Three.js

### Step 2: Create Robot Component (Today)
- [ ] Create `src/ui/src/components/RobotModel.tsx`
- [ ] Load URDF/GLTF model
- [ ] Position next to build plate
- [ ] Add basic joint controls

### Step 3: Backend IK Service (This Week)
- [ ] Create `/api/robot/ik` endpoint
- [ ] Integrate COMPAS FAB
- [ ] Test with sample poses
- [ ] Return joint angles

### Step 4: Connect Frontend to IK (This Week)
- [ ] Call IK for each toolpath point
- [ ] Display "calculating..." progress
- [ ] Handle errors gracefully
- [ ] Cache results

---

## Git Repository

**URL:** https://github.com/Addcomposites-github/openaxis
**Status:** Clean, all work committed and pushed

**Latest Commits:**
```
f57000e - docs: Add cleanup summary and next steps guide
da180f0 - chore: Add .claude/ to .gitignore
e043109 - feat: Implement Weeks 1-3 - Complete CAM UI with backend integration
```

---

## Start Commands

```bash
# Backend
python src/backend/server.py

# Frontend
cd src/ui
npm run dev

# Open browser
http://localhost:5173
```

---

## Focus Statement

**We are building a robotic manufacturing CAM system, not a geometry viewer.**

Every feature must answer: **"Does this help validate robot motion for safe manufacturing?"**

If no → skip it.
If yes → implement it.

Let's build the robot simulation.

---

**Next Action:** Find ABB IRB 6700 URDF or suitable robot model.

**End Goal:** Robot arm following toolpath with collision detection, just like RoboDK or SprutCAM.

---

*Session Start: 2026-01-27*
*Priority: Robot visualization and motion simulation*
*No distractions. Focus on the mission.*
