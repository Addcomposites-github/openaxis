# OpenAxis Research Brief: Complete UI/UX Workflow Analysis

## Purpose

This document is a **research brief for a dedicated Claude Code session** whose sole job is deep competitive analysis of robotic additive manufacturing (RAM) software UIs. The goal is to extract **every minor detail** — layout, button count, field names, panel titles, dropdown options, slider ranges, status indicators — so we can implement a production-quality UI in OpenAxis.

---

## What We Already Have (DO NOT Re-Research)

OpenAxis already has a working prototype with these completed features:

### Current Architecture
- **Stack**: React + Three.js + Zustand + Tailwind, Python backend (FastAPI)
- **Single persistent Canvas**: One Three.js scene that never unmounts across all tabs
- **4-tab workspace**: Setup → Geometry → Toolpath → Simulation
- **Robot**: ABB IRB 6700-200/2.60 loaded from URDF with collision/visual meshes
- **IK**: Analytical geometric IK (3.5μs/point, 245K waypoints in 852ms)
- **Simulation**: 60fps useFrame-based playback with per-waypoint joint interpolation
- **Toolpath**: Planar slicing with perimeter/infill/travel segments, 400 layers

### Current UI Tabs
1. **Setup**: Robot model selection, end effector type/offset, external axis config, work table size/position
2. **Geometry**: STL/OBJ import, transform tools, slicing parameters (layer height, wall count, infill density/pattern)
3. **Toolpath**: Layer-by-layer preview, statistics (segments, points, time, material), G-code export
4. **Simulation**: Play/pause/speed controls, joint sliders, IK status, reachability, TCP position display, follow-TCP camera

### What Works
- Robot visualization with URDF
- Geometry import and placement on build plate
- Toolpath generation (planar slicing)
- Robot simulation following toolpath with smooth per-waypoint IK
- Auto-speed calculation, inter-segment travel times
- Backend with roboticstoolbox-python DH-based IK solver

---

## What We Need to Research

For each software below, we need **pixel-level detail** of the entire user workflow. Not "it can do slicing" — we need "the slicer panel has a dropdown with options X, Y, Z, a slider from A to B with label C, and a checkbox D."

### Target Software (Priority Order)

1. **Adaxis AdaOne** (Primary — closest to our goal)
   - Website: https://adaxis.eu
   - Resource center: https://resource.adaxis.eu
   - We have their documentation extracted in `docx_extracted.txt`

2. **AiBuild** (Secondary — good hybrid manufacturing UI)
   - Website: https://www.ai-build.com
   - Known for: AI-enhanced path planning, multi-process support

3. **RoboDK** (Reference — most complete offline programming)
   - Website: https://robodk.com
   - Known for: 600+ robot models, post processor library

4. **CEAD AM Flexbot** (Reference — pellet extrusion specific)
   - Often used with AdaOne, has specific cell configurations

5. **Meltio Space** (Reference — wire-laser DED specific)
   - Website: https://meltio3d.com

---

## Research Areas — Exhaustive Detail Required

### AREA 1: Cell/Robot Setup Workflow

For each software, document:

**Robot Import/Selection**
- How is a robot added? (library browser? file import? dropdown?)
- What robot brands/models are available?
- What information is shown per robot? (reach, payload, DOF, image?)
- Can you import custom robots? How? (URDF? Step? DH parameters?)
- Is there a robot library browser? How is it organized?

**Robot Positioning**
- How is the robot base position set? (drag in 3D? input fields? both?)
- What coordinate system is used? (world frame? user frame?)
- Can the base be tilted/rotated? (for wall-mounted or ceiling-mounted robots)
- Is there a "base frame" concept separate from world frame?
- Can the robot be placed on a pedestal? How is pedestal height defined?

**End Effector / Process Head / TCP Definition**
- How is the tool center point (TCP) defined? (XYZ offset? full 6DOF frame?)
- What is the UI for TCP input? (fields? visual picker? teach mode?)
- Can you import tool/process head 3D geometry? (STL? STEP?)
- How are tool conventions handled? (Z+, Z-, tool pointing direction)
- Is there a tool frame rotation input? What convention? (Euler XYZ? RPY? Quaternion?)
- Can you define multiple process heads? How do you switch between them?
- What process types are available? (WAAM, pellet extrusion, milling, laser cladding, etc.)
- How is the tool weight/mass defined?
- How is tool collision geometry defined?

**External Axes**
- What types of external axes? (positioner, linear track, turntable, gantry)
- How are they added and configured?
- What parameters per axis? (travel limits, speed, acceleration)
- How is the robot linked to an external axis? (parent-child in scene tree?)
- How is coordinated motion configured?

**Work Frame / Base Frame**
- How is the work frame (base/coordinate system for the part) defined?
- Can the work frame be tilted? (non-horizontal build plates)
- Is there a "work frame wizard" or calibration procedure?
- How does the work frame relate to the post processor output?
- Can you define multiple work frames?

**Build Platform**
- How is the build platform added? (import geometry? parametric box?)
- What parameters? (size, position, material)
- Is there a build volume visualization? (max envelope)

### AREA 2: Geometry Import & Preparation

**File Formats**
- What formats are supported? (STL, STEP, OBJ, 3MF, IGES, etc.)
- Is there a format preference / what's recommended?
- Are there file size limits?

**Part Manipulation**
- What transform tools exist? (translate, rotate, scale, mirror)
- How is translation input? (drag gizmo? numeric fields? both?)
- What rotation convention? (Euler XYZ? RPY? Quaternion? all options?)
- Is there a "place surface on platform" feature? How does it work?
- Can you snap to surfaces or edges?

**Mesh Operations**
- Boolean operations? (union, subtract, intersect)
- Mesh repair? (hole filling, self-intersection removal)
- Mesh offset/shell?
- Mesh simplification/decimation?
- Section/slice preview before generating full toolpath?

**Part Tree / Scene Hierarchy**
- How are multiple parts organized? (flat list? tree hierarchy?)
- Can parts be grouped?
- What properties are shown per part? (name, dimensions, volume, surface area)

### AREA 3: Slicing / Path Planning — THE MOST CRITICAL SECTION

**Slicing Strategies Available**
- What strategies exist? Document each one:
  - Planar horizontal (standard FDM-style)
  - Planar along curve (non-planar conformal)
  - Radial (from center outward)
  - Revolved surface (for rotational parts with positioner)
  - Sweep (along a guide curve)
  - Multi-planar
  - Variable angle / tilted planes
  - Geodesic
  - Other?
- How is each strategy selected? (dropdown? visual selector?)
- What parameters does each strategy expose?

**Slicing Parameters (for each strategy)**
- Layer height (mm) — range, step, default
- Bead width / extrusion width (mm)
- Wall count / perimeters
- Infill density (%)
- Infill pattern options (lines, grid, triangles, hexagons, concentric, Hilbert, gyroid, etc.)
- Top/bottom solid layers
- Overlap percentage (infill-wall overlap)
- Seam position (random, aligned, back, custom)
- Z-seam alignment
- Start/end distance from seam
- Spiral/vase mode
- Adaptive layer height
- Overhang angle threshold
- Support generation (auto? manual? tree supports?)
- Raft/brim/skirt options
- Speed settings (print speed, travel speed, first layer speed)
- Retraction settings (if applicable)
- Temperature/power settings per layer
- Layer time control (min layer time, fan speed adjustments)
- Engage/disengage movements (approach/retract at start/end of each layer)

**Path Planning Specific to Robotic AM**
- Tool orientation along path (how is it controlled?)
- Lead/lag angle
- Tilt angle / weave pattern
- Interlayer dwell time
- Layer-to-layer transition type (ramp, step, helical)
- Multi-bead/multi-pass strategies
- Stiffener/rib generation for thin walls
- Overlap strategy for multi-pass
- Collision-aware path modification

**Slicing Engines Available (Open Source)**
- What open-source slicers exist that support non-planar / multi-axis?
- ORNL Slicer 2 capabilities
- CuraEngine capabilities for robotic AM
- PrusaSlicer/SuperSlicer non-planar features
- FullControl GCode Designer
- Any research/academic slicers for WAAM?
- Gradient/variable layer height slicers

### AREA 4: Toolpath Visualization & Editing

**Visualization**
- How is the toolpath displayed? (lines? tubes? points?)
- Color coding scheme? (by type? by speed? by temperature? by layer?)
- Can you switch between color modes?
- Layer-by-layer playback controls? (slider? buttons? animation?)
- Transparency/opacity controls?
- Cross-section view?
- Is there a graph/chart view? What data does it show?

**Toolpath Editing**
- Can you edit individual waypoints?
- Can you move/delete/insert waypoints?
- Region-based parameter editing? (select area, change speed/temp)
- Start point / seam modification?
- Manual path drawing / sketching?
- Path ordering / resequencing?
- Undo/redo for edits?

**Toolpath Data Display**
- What statistics are shown? (total time, material, path length, layer count, etc.)
- Per-layer statistics? (time, points, length)
- Graph view data? (deposition rate vs time, speed vs position, robot joint angles, etc.)
- Collision detection results? (how displayed?)
- Singularity detection results?
- Reachability map / heatmap?

### AREA 5: Simulation — UI Controls & Display

**Playback Controls**
- What buttons? (play, pause, stop, reset, step forward, step back)
- Speed control? (slider? dropdown? what speeds?)
- Timeline scrubber? (what information on the timeline?)
- Can you jump to a specific layer / time / waypoint?
- Loop playback? (continuous? single? layer-by-layer?)

**Robot Visualization During Simulation**
- Is the robot fully animated (all joints)?
- Are joint angles displayed during playback?
- Is the TCP position displayed? (format: XYZ + orientation)
- Is there a "ghost" showing the next few positions?
- Trail/trace of TCP path during playback?
- Material deposition visualization? (growing part during sim?)
- Can you zoom to / follow the TCP?

**Simulation Data Display Panel**
- What information is shown in the side panel during simulation?
- Current time / total time
- Current layer / total layers
- Current speed / feedrate
- Current segment type (perimeter, infill, travel)
- Joint angles (all 6 + external axes)
- TCP position (XYZ + RPY/quaternion)
- Joint velocities
- Joint torques (estimated?)
- Collision status
- Singularity proximity
- Reachability status
- Process parameters (temperature, wire feed, gas flow, etc.)
- Deposition rate

**Simulation Validation Checks**
- What checks are performed? (collision, singularity, joint limits, reach, etc.)
- How are violations displayed? (color change? markers? popup? log?)
- Can you export a validation report?
- Is there a "fix" or "resolve" option for violations?

**Homing / Start Position**
- How is the robot home position defined?
- Is there a "safe" position concept?
- How does the robot move to the start of the toolpath from home?
- Approach/retract moves — how are they defined?
- Is there a "teach" mode for defining positions?

### AREA 6: Post Processor & Code Generation

**Post Processor Architecture**
- What is a post processor in this context?
- How many post processors are available?
- Can you create custom post processors?
- What output formats? (ABB RAPID, KUKA KRL, Fanuc TP, Siemens Sinumerik, G-code, etc.)
- Is there a post processor editor? What does it look like?

**Post Processor Events / Triggers**
- What events can have custom code injected?
  - Program start / end
  - Layer start / end
  - Process on / off (torch on/off, extruder on/off)
  - Tool change
  - Pause/wait
  - External axis moves
  - Gas on/off
  - Wire feed start/stop
  - Custom triggers
- What variables are accessible in event code?
  - Layer number
  - Current position (XYZ + orientation)
  - Current speed
  - Current temperature/power
  - Extrusion volume/rate
  - Time
  - Custom variables

**Output Configuration**
- What options for coordinate output? (joint angles? Cartesian? both?)
- Coordinate precision? (decimal places)
- Angle convention for orientation? (Euler? RPY? Quaternion? axis-angle?)
- Which base frame is used for output? (world? work frame? tool frame?)
- Motion type per segment? (MoveJ? MoveL? MoveC?)
- Zone/blending parameters? (fine? z1? z5? z10?)
- Speed data format?
- I/O signal definitions?

### AREA 7: Monitoring & Robot Connection

**Connection Methods**
- How does the software connect to the robot controller?
- OPC UA integration — how is it configured?
- Direct controller connection (RSI, EGM, etc.)
- What information is exchanged in real-time?

**Real-Time Monitoring**
- What data is displayed during real execution?
- Position tracking (commanded vs actual)
- Temperature monitoring
- Force/torque feedback
- Camera feed integration
- Layer completion tracking
- Estimated time remaining
- Process quality indicators

### AREA 8: Additional Features to Investigate

**Multi-Process / Hybrid Manufacturing**
- How are multiple processes combined? (additive + subtractive)
- Process sequencing UI
- Tool change handling
- Different speed/parameter sets per process

**External Axis Coordination**
- How is the positioner interpolation configured?
- What interpolation modes? (synchronous, sequential, shortest path)
- Can you specify rotation limits per layer?
- How are singularities in external axes handled?

**Project / Cell Management**
- How are projects organized?
- Can you save/load cells separately from projects?
- Export/share functionality?
- Version control / undo history?

---

## Reference Materials Available

The research session should use these existing materials:

1. **AdaOne Documentation**: `docx_extracted.txt` (4735 lines) — contains workspace layout, cell creation guide, toolpath guide, post processor info, equipment control
2. **ROADMAP.md**: Our development phases and feature targets
3. **PHASE_BRIDGE_PLAN.md**: Integration plan with manufacturing features needed
4. **SESSION_START_ROBOT_FOCUS.md**: Current state analysis and priority gaps
5. **config/robots/abb_irb6700.yaml**: Our current robot config (DH params, joint limits, velocities)
6. **config/processes/waam_steel.yaml**: Our WAAM process parameters (wire, welding, gas, layer params)

---

## Research Methodology

1. **Video Analysis**: Search YouTube for tutorial/demo videos of each software. Pause at every screen and document:
   - Panel layout (left, right, top, bottom)
   - Button icons and labels
   - Input field names and types (slider, dropdown, numeric, checkbox)
   - Status indicators (badges, colors, icons)
   - Menu hierarchy (main menu → sub-menu → items)

2. **Documentation Scraping**: Fetch official docs/resource centers:
   - https://resource.adaxis.eu (AdaOne resource center)
   - https://www.ai-build.com/resources (AiBuild)
   - https://robodk.com/doc/en/ (RoboDK documentation)

3. **Academic Papers**: Search for papers on:
   - "robotic additive manufacturing software workflow"
   - "WAAM path planning software"
   - "multi-axis slicing algorithms"
   - "non-planar 3D printing slicing"

4. **Open Source Slicers**: Evaluate:
   - ORNL Slicer 2 (https://github.com/ORNLSlicer/Slicer-2)
   - FullControl (https://fullcontrolgcode.com)
   - Non-planar slicing research projects
   - CuraEngine robotic AM plugins

---

## Output Format Required

For each software and each area, produce a structured document with:

```
## [Software Name] - [Area]

### UI Layout
- Panel position: [left/right/top/bottom]
- Panel width: [approximate px or % if visible]
- Background: [color/theme]

### Controls
| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| ... | dropdown | ... | [...] | ... | ... |
| ... | slider | ... | min-max | ... | ... |
| ... | button | ... | N/A | N/A | ... |
| ... | checkbox | ... | on/off | off | ... |
| ... | numeric | ... | min-max, step | ... | ... |

### Workflow Steps
1. User does X
2. Panel shows Y
3. User clicks Z
...

### Screenshots/Video Timestamps
- [URL] at [timestamp]: Shows [what]
```

---

## Priority of Research

1. **HIGHEST**: Slicing strategies and parameters (Area 3) — this directly drives our next implementation sprint
2. **HIGH**: Post processor / code generation (Area 6) — needed for actual robot execution
3. **HIGH**: Simulation UI controls and data display (Area 5) — we have basic version, need production polish
4. **MEDIUM**: Cell/robot setup workflow (Area 1) — we have basics, need TCP definition and work frame
5. **MEDIUM**: Toolpath visualization and editing (Area 4) — we have visualization, need editing
6. **LOWER**: Monitoring and connection (Area 7) — Phase 4 feature
7. **LOWER**: Multi-process and external axes (Area 8) — Phase 2+ feature

---

## Key Insight From Our Development

The biggest lesson from building OpenAxis so far: **the devil is in the details**. The difference between a demo and production software is not the big features — it's the 200 small things:
- The exact TCP frame definition workflow
- How the work frame relates to the post processor output coordinates
- What happens when a joint limit is violated during simulation (do you stop? warn? auto-adjust?)
- How the homing position is defined and how the robot gets there
- What triggers exist in the post processor and what variables are accessible
- How the base frame calibration works for non-horizontal installations

These details can ONLY be found by carefully studying production software that real manufacturers use daily.

---

*This brief should be provided to the new Claude Code research session along with the `docx_extracted.txt` file and the project's `ROADMAP.md` for context.*
