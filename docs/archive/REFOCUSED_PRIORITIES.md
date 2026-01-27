# Refocused Priorities - Back to the Real Goal

## User Feedback: We Lost the Big Picture

**Quote:** "the final goal of this project is to actually have import the object generate the path and then the there is a robotic simulation with external axis that actually can you know follow that path you know without hitting singularity or you know detecting collision"

**The user is right** - we've been fixing minor UI issues while the **core robotic functionality** is missing.

---

## The REAL Success Criteria

**Complete Workflow Should Be:**
1. ✅ Import geometry (STL/OBJ) - **DONE**
2. ✅ Place on build plate - **DONE** (minor Z-offset issue to fix)
3. ✅ Generate toolpath - **DONE** (backend integration exists)
4. ❌ **ROBOT SIMULATION** - **MISSING!** ← **THIS IS THE MAIN GOAL**
5. ❌ Robot follows toolpath - **MISSING!**
6. ❌ Collision detection - **MISSING!**
7. ❌ Singularity checking - **MISSING!**
8. ❌ External axes coordination - **MISSING!**
9. ❌ Export robot program - **MISSING!**

---

## What's Currently Missing

### 1. **No Robot Model in Workspace** ⚠️
- User: "in the workspace there is no robot with the printed on top of it"
- **Issue:** We have a build plate but no robot arm visualization
- **What we need:**
  - 6-axis robot arm model (URDF or GLTF)
  - Positioned next to build plate
  - Joint visualization
  - End effector with tool

### 2. **No Robot Simulation** ⚠️
- **Issue:** Toolpath exists but robot doesn't move
- **What we need:**
  - Forward kinematics to position robot
  - Inverse kinematics to reach toolpath points
  - Animation of robot following path
  - Joint angle display

### 3. **No Collision Detection** ⚠️
- **What we need:**
  - Robot self-collision check
  - Robot vs part collision
  - Robot vs build plate collision
  - External axis collision

### 4. **No Singularity Checking** ⚠️
- **What we need:**
  - Detect when robot approaches singularity
  - Warn user
  - Suggest path modifications

### 5. **No External Axes** ⚠️
- **What we need:**
  - Rotary table model
  - Linear track model
  - Coordinated motion planning

---

## Immediate Action Plan

### Phase 1: Add Robot to Workspace (Priority 1)

**Goal:** User can see a robot arm in the 3D workspace

**Tasks:**
1. Find or create robot URDF/GLTF model (ABB IRB 6700 or similar)
2. Load robot model into GeometryEditor scene
3. Position robot next to build plate
4. Add joint controls to move robot manually
5. Display current joint angles

**Time:** 1-2 days
**Dependencies:** Three.js URDF loader or GLTF loader

---

### Phase 2: Robot Follows Toolpath (Priority 2)

**Goal:** Robot animates following the generated toolpath

**Tasks:**
1. Implement inverse kinematics (use existing Python backend with COMPAS)
2. For each toolpath point, calculate joint angles
3. Animate robot moving through poses
4. Show end effector path
5. Add play/pause/speed controls

**Time:** 2-3 days
**Dependencies:** COMPAS FAB for IK, motion planning

---

### Phase 3: Collision Detection (Priority 3)

**Goal:** Detect when robot would collide

**Tasks:**
1. Create collision meshes for robot links
2. Implement collision checking (use Three.js or Python backend)
3. Highlight colliding parts in red
4. Display collision warnings
5. Prevent execution if collision detected

**Time:** 2-3 days
**Dependencies:** Collision detection library (FCL, or Three.js raycasting)

---

### Phase 4: Singularity & Reachability (Priority 4)

**Goal:** Check if toolpath is feasible

**Tasks:**
1. Calculate manipulability index at each point
2. Check workspace reachability
3. Warn about singularities
4. Suggest alternative poses
5. Color-code toolpath by feasibility

**Time:** 2-3 days
**Dependencies:** COMPAS FAB kinematics

---

### Phase 5: External Axes (Priority 5)

**Goal:** Add rotary table and/or linear track

**Tasks:**
1. Add rotary table model
2. Implement coordinated motion (robot + table)
3. Expand workspace with external axes
4. Optimize motion distribution

**Time:** 3-4 days
**Dependencies:** Multi-group motion planning

---

## What We Should STOP Doing

❌ **Minor UI tweaks** (delete buttons, placement buttons, etc.)
❌ **Documentation for features that don't address the core goal**
❌ **Fixing cosmetic issues**

## What We Should START Doing

✅ **Robot visualization**
✅ **Motion simulation**
✅ **Collision checking**
✅ **Singularity detection**
✅ **Making this a REAL robotic manufacturing tool**

---

## Technical Approach

### For Robot Visualization
- **Option 1:** Use URDF loader + Three.js
- **Option 2:** Use pre-converted GLTF model
- **Recommendation:** Start with GLTF for speed, then add URDF support

### For Kinematics
- **Backend:** Use existing COMPAS FAB Python backend
- **Frontend:** Call IK service for each toolpath point
- **Caching:** Pre-calculate all joint angles, then animate

### For Collision
- **Option 1:** Three.js raycasting (simple, fast, client-side)
- **Option 2:** Python FCL via backend (accurate, slower)
- **Recommendation:** Start with Three.js, add FCL later

---

## Revised Success Criteria

**The workflow MUST be:**
1. Import STL
2. Auto-place on build plate (bottom touching Z=0)
3. Slice to generate toolpath
4. **See robot in workspace** ✅
5. **Click "Simulate" to see robot follow path** ✅
6. **Collision warnings if robot hits anything** ✅
7. **Singularity warnings if path not feasible** ✅
8. **Export robot program** (RAPID, KRL, etc.)

---

## Current Bugs to Fix First (Quick)

1. **Z-placement issue** - Part center at Z=0 instead of bottom
   - Check if geometry vertices are being offset correctly
   - Should take 10-15 minutes to diagnose and fix

2. **Toolpath navigation error** - User mentioned an error
   - Need to see the actual error message
   - Probably missing null check or state issue

Once these are fixed, **IMMEDIATELY pivot to robot visualization**.

---

## Resources Needed

### Robot Models
- ABB IRB 6700 URDF
- KUKA KR 500 URDF
- Fanuc M-20iA URDF
- Or generic 6-axis robot GLTF

### Libraries
- `urdf-loader` for Three.js
- COMPAS FAB for kinematics (already in stack)
- `python-fcl` for collision (optional)

### Backend Endpoints Needed
- `POST /api/robot/ik` - Calculate inverse kinematics
- `POST /api/robot/check-collision` - Check collision
- `POST /api/robot/check-singularity` - Check singularity
- `GET /api/robot/models` - List available robot models

---

## Next Steps (Immediate)

1. **Fix Z-placement bug** (15 min)
2. **Fix toolpath error** (15 min)
3. **Find robot GLTF/URDF model** (30 min)
4. **Load robot into scene** (2-3 hours)
5. **Position robot next to build plate** (30 min)
6. **Add manual joint controls** (1-2 hours)

**Total to get robot visible:** ~1 day

Then we can work on making it follow the toolpath.

---

## Long-Term Vision

This should become a **real robotic CAM software** like:
- **RoboDK** - Robot simulation and programming
- **SprutCAM** - CAM with robot support
- **Adaxis AdaOne** - The commercial tool we're competing with

Not just a geometry viewer with slicing.

---

## User is Right

The user is absolutely correct. We got distracted by:
- Making delete buttons visible
- Adding "Place on Plate" buttons
- Writing documentation
- Minor UI fixes

While the **core robotic functionality** - the entire reason this project exists - is missing.

**Let's refocus on what matters: Robot simulation with collision detection and singularity checking.**

---

## Questions for User

1. Which robot model should we start with? (ABB IRB 6700, KUKA, Fanuc, or generic?)
2. Do you have URDF files, or should we find open-source models?
3. What's the error you're seeing with toolpath navigation?
4. For the Z-placement, is the part floating above the plate or half-buried?

---

**Priority:** Get robot model visible in workspace by end of today.
