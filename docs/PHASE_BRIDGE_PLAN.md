# Phase Bridge: Connecting UI to Core Functionality

## Current Situation

**What We Have:**
- ✅ **Phase 1 (Backend)**: Complete CLI workflow - STL → Slicing → Toolpath → G-code
- ✅ **Phase 3 (Frontend)**: Beautiful UI with React + Three.js
- ❌ **Gap**: UI and backend are not connected functionally

**User Perspective Issues:**
1. Clicking "Generate Toolpath" shows notification but no actual slicing
2. No visible toolpath layers/segments in 3D view
3. No build plate (should be 1m x 1m minimum)
4. Geometry doesn't snap to build plate
5. No layer-by-layer visualization
6. No simulation of actual manufacturing process

## Root Cause Analysis

The Phase 3 UI was built as visual mockups without integration to Phase 1's working backend:
- GeometryEditor has file loading but doesn't call backend slicing
- ToolpathEditor shows placeholder paths, not actual sliced toolpaths
- Simulation shows cubes/spheres instead of real robot + workpiece
- Backend server exists but UI doesn't make API calls

## Revised Plan: Phase 1.5 - UI Integration Bridge

**Goal**: Connect the working Phase 1 backend to the Phase 3 UI to create a functional end-to-end workflow.

**Duration**: 2-3 weeks focused development

---

## Critical Features for Manufacturing Workflow

### 1. Build Plate System (Priority: CRITICAL)

**What's Needed:**
- 1m x 1m (1000mm x 1000mm) build plate visualization
- Grid overlay every 100mm
- Origin marker (0,0,0) clearly visible
- Z-height ruler showing build height

**Implementation:**
```typescript
// src/ui/src/components/BuildPlate.tsx
- Large plane geometry (1000 x 1000 mm)
- Grid helper with major/minor divisions
- Coordinate axes (X=red, Y=green, Z=blue)
- Dimensions display in corner
```

**Backend Changes:**
- Update slicer to respect build volume limits
- Add build volume validation in project config

### 2. Part Placement on Build Plate (Priority: CRITICAL)

**What's Needed:**
- Auto-snap imported geometry to build plate Z=0
- Collision detection with build plate bounds
- Face selection for build plate orientation
- Manual Z-offset adjustment
- Center on plate button
- Multiple parts placement

**User Workflow:**
1. Import STL → Automatically place on build plate
2. Click part face → Set as base (orient geometry)
3. Drag/move part on plate (X-Y only, locked to Z=0)
4. Show red warning if part exceeds build volume

**Implementation:**
```typescript
// GeometryEditor: Part placement controls
- Face picker (raycasting)
- Transform gizmo (position only, not rotation initially)
- Bounds checking against build plate
- Auto-orient based on selected face
```

### 3. Actual Slicing Integration (Priority: CRITICAL)

**What's Needed:**
- Call backend `/api/toolpath/generate` when button clicked
- Pass geometry file path + slicing parameters
- Receive actual toolpath data (segments, layers)
- Store toolpath in frontend state
- Navigate to ToolpathEditor with real data

**Backend Integration:**
```typescript
// GeometryEditor: Generate Toolpath flow
1. Validate part is on build plate
2. Collect slicing parameters:
   - Layer height (0.5mm - 5mm)
   - Extrusion width (2mm - 10mm)
   - Wall count (1-5)
   - Infill density (0% - 100%)
   - Infill pattern (lines, grid, etc.)
3. POST to /api/toolpath/generate
4. Wait for response with progress indicator
5. Store toolpath data
6. Navigate to /toolpath view
```

**Parameters UI:**
```typescript
// Slicing Parameters Panel
- Layer Height: 2.0mm (slider)
- Extrusion Width: 2.5mm (slider)
- Walls: 2 (number input)
- Infill: 20% (slider)
- Pattern: Lines (dropdown)
- Process: WAAM/Pellet/Milling (select)
```

### 4. Toolpath Visualization (Priority: CRITICAL)

**What's Needed:**
- Render actual toolpath segments as 3D lines
- Color code by type (perimeter=blue, infill=orange, travel=gray)
- Layer slider to show individual layers
- Play/pause animation through layers
- Show current layer number / total layers
- Extrusion rate visualization (line thickness)

**Implementation:**
```typescript
// ToolpathEditor: Real toolpath rendering
interface ToolpathSegment {
  type: 'PERIMETER' | 'INFILL' | 'TRAVEL';
  layer: number;
  points: [number, number, number][];
  speed: number;
  extrusionRate: number;
}

// Render as LineSegments in Three.js
- Group by layer
- Color by type
- Animate through layers with timeline
```

**Layer Controls:**
```typescript
// Layer visualization UI
- Layer slider: 1 / 20 layers
- Previous/Next layer buttons
- Show All / Show Single Layer toggle
- Auto-play animation (1 layer/sec)
- Jump to layer input
```

### 5. Manufacturing Simulation (Priority: HIGH)

**What's Needed:**
- Load robot model (URDF) into simulation
- Show part being built layer-by-layer
- Robot tool follows toolpath
- Material "appears" along toolpath
- Time display (elapsed / total)
- Pause/play/reset controls

**Implementation:**
```typescript
// Simulation: Real manufacturing visualization
- Load robot URDF from backend
- Position tool at toolpath start
- Animate tool along path
- Create mesh trail as material deposition
- Update layer display in real-time
```

---

## Implementation Phases

### Week 1: Build Plate & Placement (Days 1-5)

**Day 1-2: Build Plate Component**
- [ ] Create BuildPlate.tsx with 1m x 1m plane
- [ ] Add grid overlay (100mm major, 10mm minor)
- [ ] Add coordinate axes and origin marker
- [ ] Add build volume bounds box
- [ ] Add dimensions display

**Day 3-4: Part Placement**
- [ ] Auto-snap imported parts to Z=0
- [ ] Add bounds checking vs build plate
- [ ] Implement transform controls (position only)
- [ ] Add "Center on Plate" button
- [ ] Show warnings for out-of-bounds parts

**Day 5: Face Selection**
- [ ] Implement face picker with raycasting
- [ ] Auto-orient part based on selected face
- [ ] Visual feedback for selected face
- [ ] Update part position to keep on plate

**Deliverable:** User can import STL, place it on visible build plate, and orient it.

### Week 2: Slicing Integration (Days 6-10)

**Day 6-7: Slicing Parameters UI**
- [ ] Create SlicingParametersPanel component
- [ ] Layer height slider (0.5mm - 5mm)
- [ ] Extrusion width slider (2mm - 10mm)
- [ ] Wall count input (1-5)
- [ ] Infill density slider (0-100%)
- [ ] Pattern dropdown (lines, grid, triangles, hexagons)
- [ ] Process type selector (WAAM, Pellet, Milling)

**Day 8: Backend API Integration**
- [ ] Create API client (src/ui/src/api/toolpath.ts)
- [ ] Implement POST /api/toolpath/generate
- [ ] Handle file upload or path passing
- [ ] Progress indicator during slicing
- [ ] Error handling and user feedback

**Day 9-10: Toolpath Data Flow**
- [ ] Update project store with toolpath data
- [ ] Pass toolpath to ToolpathEditor
- [ ] Store slicing parameters with project
- [ ] Add re-slice functionality
- [ ] Save toolpath to project file

**Deliverable:** Clicking "Generate Toolpath" actually slices the geometry and stores real toolpath data.

### Week 3: Toolpath Visualization (Days 11-15)

**Day 11-12: Toolpath Rendering**
- [ ] Create ToolpathRenderer component
- [ ] Parse toolpath segments from backend
- [ ] Render as Three.js LineSegments
- [ ] Color code by segment type
- [ ] Group segments by layer
- [ ] Add line thickness based on extrusion rate

**Day 13: Layer Controls**
- [ ] Layer slider component
- [ ] Show single layer / show all toggle
- [ ] Previous/Next layer buttons
- [ ] Jump to layer input
- [ ] Current layer highlight

**Day 14: Animation**
- [ ] Play/pause animation through layers
- [ ] Speed control (0.5x - 4x)
- [ ] Auto-play from start
- [ ] Show layer number and progress bar
- [ ] Animate tool position along path

**Day 15: Statistics & Export**
- [ ] Display toolpath statistics
  - Total length
  - Layer count
  - Estimated time
  - Material usage
- [ ] Export G-code button
- [ ] Save toolpath visualization as image
- [ ] Print settings summary

**Deliverable:** User sees actual sliced layers and can visualize toolpath layer-by-layer.

---

## Bonus: Week 4 - Manufacturing Simulation (Optional)

**Day 16-17: Robot Model Loading**
- [ ] Load URDF from backend
- [ ] Position robot relative to build plate
- [ ] Show robot in home position
- [ ] Highlight tool/end-effector

**Day 18-19: Tool Animation**
- [ ] Animate tool along toolpath
- [ ] Sync with layer visualization
- [ ] Show material deposition trail
- [ ] Build part layer-by-layer visually

**Day 20: Simulation Controls**
- [ ] Play/pause/reset simulation
- [ ] Speed control
- [ ] Skip to layer
- [ ] Camera follow tool option
- [ ] Simulation time display

**Deliverable:** User can watch realistic manufacturing simulation.

---

## Technical Architecture

### Frontend State Management

```typescript
// src/ui/src/stores/manufacturingStore.ts
interface ManufacturingState {
  // Build plate
  buildPlate: {
    dimensions: { x: number; y: number; z: number };
    visible: boolean;
  };

  // Parts on plate
  parts: Array<{
    id: string;
    geometry: THREE.BufferGeometry;
    position: THREE.Vector3;
    rotation: THREE.Euler;
    onPlate: boolean;
    boundsValid: boolean;
  }>;

  // Slicing
  slicingParams: {
    layerHeight: number;
    extrusionWidth: number;
    wallCount: number;
    infillDensity: number;
    infillPattern: string;
    processType: string;
  };

  // Toolpath
  toolpath: {
    segments: ToolpathSegment[];
    layers: number;
    statistics: {
      totalLength: number;
      estimatedTime: number;
      materialUsage: number;
    };
  } | null;

  // Visualization
  currentLayer: number;
  showAllLayers: boolean;
  animationPlaying: boolean;
  animationSpeed: number;
}
```

### Backend API Endpoints

```python
# src/backend/server.py

POST /api/toolpath/generate
{
  "geometryPath": "/path/to/file.stl",
  "params": {
    "layerHeight": 2.0,
    "extrusionWidth": 2.5,
    "wallCount": 2,
    "infillDensity": 0.2,
    "infillPattern": "lines",
    "processType": "waam"
  }
}

Response:
{
  "status": "success",
  "data": {
    "id": "toolpath_123",
    "layerHeight": 2.0,
    "totalLayers": 20,
    "processType": "waam",
    "segments": [
      {
        "type": "PERIMETER",
        "layer": 0,
        "points": [[0,0,0], [1,0,0], ...],
        "speed": 1000.0,
        "extrusionRate": 1.0
      },
      ...
    ],
    "statistics": {
      "totalSegments": 100,
      "totalPoints": 5000,
      "layerCount": 20,
      "estimatedTime": 180.5,  // seconds
      "estimatedMaterial": 25.3  // relative units
    }
  }
}
```

---

## Testing Plan

### Unit Tests
- Build plate dimensions calculation
- Part bounds checking
- Toolpath segment parsing
- Layer grouping logic

### Integration Tests
- STL import → placement on plate
- Generate toolpath → receive data
- Toolpath data → 3D visualization
- Layer slider → correct layer shown

### User Acceptance Tests
1. Import 50mm cube → Placed centered on build plate
2. Select slicing params → Generate toolpath → See 25 layers
3. Use layer slider → See individual layer paths
4. Click play → Watch animation through all layers
5. Export G-code → Valid file downloaded

---

## Success Criteria

### Minimum Viable (Week 2)
- ✅ 1m x 1m build plate visible with grid
- ✅ Imported parts snap to plate
- ✅ Generate toolpath calls backend
- ✅ Real toolpath data received
- ✅ Basic toolpath lines rendered

### Full Feature (Week 3)
- ✅ Parts stay within build volume
- ✅ Face selection for orientation
- ✅ Complete slicing parameters UI
- ✅ Layer-by-layer visualization
- ✅ Animation through layers
- ✅ Toolpath statistics displayed
- ✅ G-code export working

### Stretch Goal (Week 4)
- ✅ Robot model in simulation
- ✅ Tool follows toolpath animated
- ✅ Material deposition visualization
- ✅ Full manufacturing simulation

---

## User Workflow After Implementation

### Current (Broken)
1. Open app → See projects
2. Create project → Opens geometry editor
3. Import STL → See floating cube
4. Click "Generate Toolpath" → Notification only
5. Navigate to toolpath editor → See placeholder
6. No understanding of what will be manufactured

### After Bridge Implementation
1. Open app → See projects
2. Create project → Opens geometry editor with **1m x 1m build plate**
3. Import STL → **Part automatically placed on plate**
4. Adjust placement → **Select face as base**, move on plate
5. Set parameters → **Layer height, walls, infill**
6. Click "Generate Toolpath" → **Backend slices geometry**
7. Wait 2-5 seconds → **Real toolpath data loaded**
8. Navigate to toolpath editor → **See actual toolpath lines**
9. Use layer slider → **View each layer**
10. Click play → **Animate through layers**
11. Check statistics → **See time estimate, material usage**
12. Export G-code → **Download actual G-code file**
13. Open simulation → **Watch robot build part layer-by-layer**

---

## Next Steps

**Immediate Actions:**
1. Create `docs/PHASE_BRIDGE_PLAN.md` (this document)
2. Set up Week 1 development branch
3. Create GitHub issues for each day's tasks
4. Begin with BuildPlate component

**Decision Points:**
- Week 1 Day 3: Face selection approach (raycasting vs manual)
- Week 2 Day 8: File handling (upload vs path reference)
- Week 3 Day 13: Animation performance with large toolpaths

**Resources Needed:**
- Example STL files (10mm cube, 100mm cube, complex part)
- Robot URDF files for simulation
- Performance testing with 10k+ segment toolpaths

---

## Conclusion

This bridge plan closes the gap between the working CLI backend (Phase 1) and the beautiful but non-functional UI (Phase 3). After 2-3 weeks, users will have a **truly functional manufacturing workflow** from CAD import to G-code export with full visualization.

The key insight: **We don't need to build everything in the original roadmap - we need to connect what already works!**
