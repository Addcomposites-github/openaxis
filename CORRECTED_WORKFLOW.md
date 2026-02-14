# OpenAxis Corrected Workflow

## The Problem
The original workflow was backwards - it started with geometry import before setting up the robot cell. This doesn't match real-world robotic manufacturing where you first set up your work cell, then bring in parts to manufacture.

## The Solution: Robot-First Workflow

```
┌─────────────────────────────────────────────────────┐
│  1. ROBOT CELL SETUP (NEW!)                        │
│     - Position robot base                           │
│     - Select end-effector (WAAM/Pellet/Spindle)    │
│     - Configure external axes (positioner/table)   │
│     - Define work table size & position            │
│     - Save cell configuration                       │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  2. GEOMETRY IMPORT & PLACEMENT                     │
│     - Import STL/STEP/OBJ                          │
│     - Geometry auto-places on work table           │
│     - Adjust position within robot reach           │
│     - Validate against work volume                  │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  3. SLICING (LINKED TO GEOMETRY)                   │
│     - Toolpath generated from geometry              │
│     - Toolpath moves WITH geometry                  │
│     - Adjust process parameters                     │
│     - Preview layers                                │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  4. SIMULATION & VALIDATION                         │
│     - Inverse kinematics calculation                │
│     - Robot motion simulation                       │
│     - Collision detection                           │
│     - Reachability analysis                         │
│     - Adjust if unreachable                         │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  5. CODE GENERATION                                 │
│     - ABB RAPID code                                │
│     - KUKA KRL (future)                            │
│     - Fanuc KAREL (future)                         │
│     - Export for robot controller                   │
└─────────────────────────────────────────────────────┘
```

---

## What's Been Fixed

### ✅ 1. Robot Cell Setup Page (NEW)

**Location:** `/robot-setup` in navigation

**Features:**
- **Robot Configuration Tab**
  - Select robot model (ABB IRB 6700-200/260)
  - Position robot base in cell (X, Z sliders)
  - View robot specifications (reach, payload, axes)

- **End Effector Tab**
  - Choose tool type:
    - WAAM Torch (wire arc additive)
    - Pellet Extruder (pellet-based printing)
    - Milling Spindle (subtractive)
    - None
  - Auto-configures TCP offset and mass

- **External Axes Tab**
  - Choose external axis type:
    - None
    - Turntable (1-axis rotation)
    - Positioner (2-axis tilt & rotate)
    - Linear Track (extend reach)
  - Position in cell (visual placement)

- **Work Table Tab**
  - Adjust table size (width, depth)
  - Set distance from robot
  - Defines manufacturing workspace

**Workflow Impact:**
- User MUST configure cell setup before importing geometry
- Configuration is saved and persists
- Geometry placement is relative to configured work table

---

### ✅ 2. Fixed Geometry Placement

**Problem:**
Parts placed "half down, half up" - bottom wasn't sitting on table correctly.

**Root Cause:**
The `centerOnPlate()` function calculated correct offsets but didn't transform the geometry vertices themselves. This caused Z-position misalignment.

**Solution:**
Modified `centerOnPlate()` in `geometryUtils.ts` to:
1. Calculate bounding box
2. Find center point (X, Y) and minimum Z
3. **Translate geometry vertices in-place** using `geometry.translate()`
4. Return position `{x: 0, y: 0, z: 0}` since geometry is now centered

**Result:**
- Geometry bottom now sits EXACTLY at Z=0 (work table surface)
- No more half-buried parts
- Proper visualization of manufacturing setup

---

### 🔄 3. Slicing Linked to Geometry (IN PROGRESS)

**Goal:**
When geometry moves, toolpath should move WITH it.

**Current Issue:**
- Toolpath is generated in global coordinates
- Moving geometry doesn't update toolpath
- They become disconnected

**Solution Plan:**
1. Store toolpath relative to geometry origin
2. Add parent-child relationship: `Geometry → Toolpath`
3. When geometry position changes, recalculate toolpath world coordinates
4. Visual: Toolpath follows geometry in 3D view

**Implementation:**
```typescript
interface GeometryPart {
  // ... existing fields
  toolpath?: {
    points: Vector3[];  // Relative to geometry origin
    worldPoints: Vector3[];  // Updated when geometry moves
  };
}

// When geometry moves:
function updateToolpathWorldCoordinates(part: GeometryPart) {
  if (!part.toolpath) return;

  const transform = new Matrix4().setPosition(
    part.position.x,
    part.position.y,
    part.position.z
  );

  part.toolpath.worldPoints = part.toolpath.points.map(p =>
    p.clone().applyMatrix4(transform)
  );
}
```

---

### 🚧 4. Reachability Visualization (NEXT)

**Goal:**
Show user if robot can reach all toolpath points BEFORE simulation.

**Features:**
- Color-code toolpath by reachability:
  - 🟢 Green: Fully reachable
  - 🟡 Yellow: Near limits (joint angles close to limits)
  - 🔴 Red: Unreachable
- Show warning overlay if any points unreachable
- Suggest geometry repositioning

**Implementation Approach:**
1. For each toolpath point, call IK solver
2. If IK returns solutions → reachable
3. If IK fails or violates joint limits → unreachable
4. Update visualization in real-time

---

### 🚧 5. ABB RAPID Code Generation (FUTURE)

**Goal:**
Export robot-ready code for ABB controllers.

**Output Format:**
```rapid
MODULE MainModule
    ! Auto-generated by OpenAxis
    ! Part: demo_part.stl
    ! Process: WAAM Steel

    CONST robtarget Home := [[0, 500, 500], [1, 0, 0, 0], [0, 0, 0, 0], [9E9, 9E9, 9E9, 9E9, 9E9, 9E9]];

    PROC main()
        MoveJ Home, v1000, z50, tool0;

        ! Start process
        SetDO DO_WeldOn, 1;

        ! Toolpath
        MoveL [[125.5, -45.2, 320.8], [1, 0, 0, 0], [0, 0, 0, 0], [9E9, 9E9, 9E9, 9E9, 9E9, 9E9]], v100, z1, tool0;
        MoveL [[126.2, -44.8, 321.5], [1, 0, 0, 0], [0, 0, 0, 0], [9E9, 9E9, 9E9, 9E9, 9E9, 9E9]], v100, z1, tool0;
        ! ... more points

        ! End process
        SetDO DO_WeldOn, 0;

        MoveJ Home, v1000, z50, tool0;
    ENDPROC
ENDMODULE
```

---

## Updated Navigation Flow

**Old (Incorrect):**
```
Dashboard → Projects → Geometry → Toolpath → Simulation
```

**New (Correct):**
```
Dashboard → Projects → Robot Setup → Geometry → Toolpath → Simulation → Code Export
```

---

## Key Improvements

### 1. **Digital Twin Concept**
The Robot Setup page creates a true digital twin of your manufacturing cell:
- Robot positioned correctly
- Work table defined
- External axes visualized
- End effector configured

### 2. **Geometry-Centric Workflow**
Once cell is set up, geometry becomes the center:
- Import part
- Auto-place on work table
- Slice generates toolpath (attached to geometry)
- Move geometry → toolpath moves too
- Simulate → validate reachability

### 3. **Manufacturing Reality**
This matches how real robotic AM works:
1. Build/calibrate physical cell
2. Bring part to station
3. Program robot (simulation)
4. Execute manufacturing

---

## What's Next

### Immediate Priorities

1. **Link Toolpath to Geometry**
   - Store toolpath relative to geometry
   - Update world coordinates on move
   - Test with actual sliced part

2. **Inverse Kinematics Integration**
   - Connect to backend IK solver
   - Calculate joint angles for toolpath points
   - Return multiple solutions

3. **Reachability Visualization**
   - Color-code toolpath by reachability
   - Show unreachable zones
   - Suggest corrections

4. **Robot Motion Simulation**
   - Animate robot along toolpath
   - Show joint angles changing
   - Display TCP path in 3D

5. **Collision Detection**
   - Robot self-collision
   - Robot-environment collision
   - Robot-part collision

6. **ABB RAPID Export**
   - Generate RAPID MODULE
   - Include process controls
   - Add safety zones

---

## Testing the New Workflow

### Step-by-Step Test

1. **Start Fresh**
   ```
   cd src/ui
   npm run dev
   ```

2. **Navigate to Robot Setup**
   - Click "Robot Setup" in sidebar
   - Should see ABB IRB 6700 in 3D view

3. **Configure Cell**
   - Tab 1: Position robot (leave at default or adjust)
   - Tab 2: Select "WAAM Torch"
   - Tab 3: Enable "Turntable" (optional)
   - Tab 4: Set work table 1.5m x 1.5m, 2m from robot
   - Click "Save Cell Setup & Continue"

4. **Import Geometry**
   - Navigate to "Geometry" page
   - Import an STL file
   - **Verify:** Part should sit perfectly on table (bottom at Z=0)
   - **Verify:** Part should be on the work table you configured

5. **Generate Toolpath**
   - Navigate to "Toolpath" page
   - Click "Generate Toolpath"
   - **Verify:** Toolpath appears on part

6. **Move Geometry** (Testing linked toolpath)
   - Go back to "Geometry" page
   - Adjust part position
   - **Expected:** Toolpath should move with geometry (once implemented)

7. **Simulate**
   - Navigate to "Simulation" page
   - Click "Play"
   - **Expected:** Robot animates along toolpath (once IK implemented)

---

## Summary

The workflow is now **robot-first**, matching real manufacturing:

✅ Robot cell setup BEFORE geometry import
✅ Geometry auto-places correctly on work table
✅ End effector configuration per process type
✅ External axes visualization
🔄 Toolpath linked to geometry (in progress)
🚧 Reachability analysis (next)
🚧 ABB RAPID code generation (next)

This creates a true **digital twin** of your manufacturing cell before you ever import a part.

---

**Last Updated:** 2026-01-27
**Status:** Core workflow restructured ✅
