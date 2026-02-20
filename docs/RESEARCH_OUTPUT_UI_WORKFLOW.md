# OpenAxis UI/UX Research Output: Complete Competitive Analysis

## Research Methodology
- **Primary source**: AdaOne documentation (docx_extracted.txt, 4735 lines) - exhaustive extraction
- **Secondary sources**: Web research on AiBuild, RoboDK, CEAD AM Flexbot, Meltio Space
- **Additional**: Open-source slicer evaluation (ORNL Slicer 2, FullControl, etc.)

---

# AREA 1: Cell/Robot Setup Workflow

## AdaOne - Cell/Robot Setup

### UI Layout
- Panel position: Right-hand side panel for properties/options
- Navigation: Top bar (A) for views, Left toolbar (B) for tools, 3D scene (C) center, Status bar (D) bottom, Right panel (E)
- Two main views: **Path Planning View** and **Manufacturing View**

### Robot Import/Selection

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Add robot | Menu | Main Menu > Equipment > Add Robot | Filter by brand, model, variant | - | Built-in library |
| Brands supported | - | - | ABB, KUKA, Fanuc, Yaskawa, Universal Robots, Comau | - | Standard 6-axis industrial and collaborative |
| Custom robots | Import | User Libraries (.rcc files) | Main Menu > Libraries > User Equipment | - | Currently compiled by ADAXIS |
| Axis limits | Numeric fields | Lower/Upper limits | Per-axis min/max | Manufacturer specs | Can only restrict, not extend |

### Robot Positioning

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Base coordinate system | Numeric fields | Position (XYZ) + Rotation | Via three-dot menu > Controller > Coordinate Systems | Brand-dependent default | ABB/KUKA: bottom center; Fanuc: intersection axis 1&2 |
| Flange coordinate system | Numeric fields | Rotation fields | Via three-dot menu > Controller > Coordinate Systems | Z-axis pointing outward | ABB x-axis down, FANUC x-axis up |
| Pedestal | Import | Main Menu > Equipment > Import Cell Element | STL/OBJ file | - | Position robot on pedestal manually |

### End Effector / Process Head / TCP Definition

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Import process head | Menu | Main Menu > Equipment > Import Process Head | STL, OBJ files | - | Local origin at attachment point |
| Type | Dropdown | Type | Single process, Multi-process | Single process | Multi-process allows multiple tool frames |
| Process | Dropdown | Process | Pellet extrusion, Filament extrusion, Concrete extrusion, Wire Arc AM, Wire Laser AM, Laser metal deposition, Electron Beam AM, Cutting, 3D scanning | - | Defines available path planning options |
| Tool frame position | Numeric (XYZ) | Position | mm coordinates | 0,0,0 | TCP relative to flange |
| Tool frame rotation | Numeric (XYZ or Quaternion) | Rotation | Euler angles or Quaternion | 0,0,0 | Toggle between Euler/Quaternion |
| Tool convention | Dropdown | Tool convention | Z+ (forward), Z- (backward), X+ (forward), X- (backward), Y+ (forward), Y- (backward) | Z+ | Defines which axis aligns with tool axis |
| Control settings | Dropdown | Control type | External axis, Digital IO, Analog IO | External axis | How process head is controlled |
| Max extruder RPM | Numeric | Max RPM | - | - | For pellet extrusion; alerts if exceeded |
| Transmission gear ratio | Numeric | Gear ratio | - | 1.0 | For external axis control |

### External Axes

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Add positioner | Menu | Main Menu > Equipment > Add Positioner | Built-in library | - | Standard 2-axis positioners |
| Add linear track | Menu | Main Menu > Equipment > Add Linear Track | Built-in library | - | e.g., Vansichen 4m track |
| Add gantry | Menu | Main Menu > Equipment > Add Gantry | Built-in library | - | Multi-axis gantries |
| Robot angle | Dropdown | Robot angle | 0, 180 degrees | - | For linear track mounting |
| Riser | Dropdown | Riser | e.g., 595mm | - | Height riser for track |
| Link robot | Dropdown | Link (right panel) | Select robot | - | Assigns robot to track |
| Axis slot assignment | Dialog | Controller > External Axes | Slot 1-6 | Auto-assigned | Right-click robot > Controller |
| Axis position | Numeric | Per-axis position | mm or degrees | Calibrated default | Via three-dot > Configuration |
| Frame orientation | Numeric | Per-axis orientation | Euler angles | Calibrated default | Via three-dot > Configuration |

### Work Frame / Base Frame

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Add work frame | Button | + > Add Work Frame | Left toolbar | At world origin | Or positioner origin if active |
| Position | Numeric (XYZ) | Position fields | mm | 0,0,0 | In world or parent coordinates |
| Rotation | Numeric | Rotation fields | Euler or Quaternion | 0,0,0 | - |
| Align frame | Button | Align (left toolbar) | Z+X axis, Z+Y axis, X+Y axis, Three planes, Offset from existing, Project to plane, Three planes midpoint | - | 7 alignment methods |
| Move parts between frames | Drag & drop | Scene graph drag | Keep World Position / Keep Local Offset | - | Dialog appears after drag |
| Multiple work frames | Yes | - | Unlimited | - | Parts can be dragged between frames |

### Build Platform

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Import platform | Menu | Main Menu > Equipment > Import Cell Element | STL, OBJ | - | Generic static physical object |
| Color | Right-click | Context menu | Color picker | - | Customizable |
| Name | Right-click | Context menu | Text input | Filename | Renameable |

---

# AREA 2: Geometry Import & Preparation

## AdaOne - Geometry Import

### File Formats

| Format | Support | Notes |
|--------|---------|-------|
| STL | Yes | Mesh format, common |
| OBJ | Yes | Mesh format |
| STEP (.stp, .step) | Yes | BRep/CAD - preferred for advanced features |
| 3MF | Yes | Mentioned in roadmap context |
| Rhino (.3dm) | Yes | Since v0.469 |
| BRep assemblies | Yes | Multi-body support |

### Part Manipulation

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Translate | Gizmo + numeric | A. Translate | XYZ axis drag or numeric input | - | Click icon for numeric entry |
| Rotate | Gizmo + numeric | B. Rotate | Euler XYZ or Quaternion | - | Toggle convention |
| Scale | Gizmo + numeric | C. Scale | Uniform or per-axis (X,Y,Z) | Uniform | Keep aspect ratio option |
| Place surface on platform | Click tool | D. Place Surface | Click surface on geometry | - | Selected surface placed on build platform |
| Drop to work frame | Tool | Drop to platform | Right-click or toolbar | - | Since v0.477 |
| Drag and drop parts | Drag | Scene graph | Between work frames | - | Since v0.493 |
| Import by drag & drop | Drop | 3D scene | Drag file to scene | - | Since v0.471 |

### Mesh Operations

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Boolean - Union | Button | E. Mesh Boolean | Object A + Object B | - | Works on open and closed meshes |
| Boolean - Intersection | Button | Mesh Boolean | Object A ∩ Object B | - | Option: Only keep faces from A |
| Boolean - Subtraction | Button | Mesh Boolean | Object A - Object B | - | Option: Only keep faces from A |
| Boolean - Merge | Button | Mesh Boolean | Merge geometries | - | Maintains separate geometries |
| Discard insignificant shells | Checkbox | More settings | on/off | off | Removes shells < 0.1 mm³ |
| Mesh Repair | Button | G. Mesh Repair | Automated hole filling, Remove self-intersections | Both on | Automatic process |
| Mesh Offset - Solid | Button | F. Mesh Offset | Offset distance (mm), non-isotropic option | - | Inward or outward |
| Mesh Offset - Shell | Button | Mesh Offset | Shell thickness (mm) | - | Hollows out solid |
| Mesh Offset - Thicken surface | Button | Mesh Offset | Thickness (mm) | - | For open surfaces |
| Mesh Offset - Offset surface | Button | Mesh Offset | Distance (mm) | - | Open surface offset |
| Mesh Offset - Extend surface | Button | Mesh Offset | Distance (mm) | - | Extends at boundary |
| Feature removal | Button | Feature removal | Inner/outer diameter threshold (mm) | - | Removes small features |
| Denoising | Button | Denoising | Recover feature edges (checkbox) | - | For 3D scans |
| Smoothing | Button | Smoothing | Number of iterations | - | Iterative smoothing |
| Extract surface | Right-click | Extract surface | BRep only | - | Creates new part from selected surface |
| Split by edges | Tool | Split by edges | BRep only | - | Since v0.499 |
| Extract curve | Right-click | Extract curve | From 3D model | - | Since v0.503 |

### Scene Hierarchy

| Feature | Description |
|---------|-------------|
| Organization | Tree hierarchy in scene graph (right panel) |
| Grouping | Parts can be nested under work frames |
| Drag & drop | Between work frames, with position options |
| Properties per part | Name (renameable), color (changeable), visibility toggle |
| Grasshopper items | Marked with "Gh" icon in scene graph |
| Context menu | Right-click for rename, color, extract, delete |

---

# AREA 3: Slicing / Path Planning (HIGHEST PRIORITY)

## AdaOne - Slicing Strategies

### Available Strategies

| # | Strategy | Description | Process Types | Key Feature |
|---|----------|-------------|---------------|-------------|
| 1 | **Planar Horizontal** | Standard FDM-style horizontal layers | All additive | Full shell/infill/seam/movement support |
| 2 | **Planar Angled** | Planar cross-sections at user-defined angle | All additive | Reduces support need for overhangs |
| 3 | **Planar Along Curve** | Layers follow a guide curve | All additive | For pipes, furniture, curved geometries |
| 4 | **Revolved Surface** | For rotationally symmetric parts | All additive | Nozzles, fuel tanks, cylinders |
| 5 | **Radial** | For cylindrical substrates (<180°) | All additive | Same options as planar |
| 6 | **Radial 360** | For cylindrical substrates (>180°) | All additive | Subset of radial options |
| 7 | **Cladding** | Conformal paths on existing surface | All additive | Surface deposition, repair |
| 8 | **Non-Planar Surface** | Slicing using arbitrary substrate shape | All additive | 3D scan substrates, complex surfaces |
| 9 | **Conical Fields** | Multiple conical layers | All additive | Greater flexibility for overhang avoidance |
| 10 | **Sweep** | Interpolates paths from start to end surface | All additive | For manifolds, chairs, vases |
| 11 | **Geodesic Paths** | Geodesic paths on surface | All additive | Referenced in movement settings |
| 12 | **Abanico** (experimental) | Auto-segments curved pipes | Pellet extrusion | For curved pipes, auto-volume segmentation |
| 13 | **Drilling** | Converts BRep holes to drilling ops | Subtractive | Auto-detects hole features |
| 14 | **Planar Facing** | Linear paths for flat surface milling | Subtractive | Face milling with tool orientation |
| 15 | **Planar Clearing** | Volume removal from flat surfaces/pockets | Subtractive | Clearing and pocketing modes |
| 16 | **Multi-Axis Finishing** | Conformal finishing tool paths | Subtractive | Surface normal or static orientation |
| 17 | **Contouring** | Waterline/Z-level milling | Subtractive | Also waterfall contouring |
| 18 | **Swarf** | Flank milling with tool side | Subtractive | For ruled/curved surfaces |
| 19 | **Scanning** | 3D scanning paths | 3D scanning | Discrete or continuous mode |

### Slicing Modes (Available for planar strategies)

| Mode | Description |
|------|-------------|
| **Normal** | Part is closed solid; generates perimeters, infill; offset inwards to match CAD dimensions |
| **Surface** | Part is a surface; paths generated exactly on surface intersection |
| **Single Wall** | Part has thickness; deposition adapts to match part thickness; variable width |

### Process Settings Card

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Process type | Dropdown | Process | Additive / Subtractive / Scanning | - | Based on cell process heads |
| Material | Dropdown | Material | From material library | - | Only if compatible materials exist |
| Material profile | Dropdown | Material profile | Per-material profiles | - | Preset path planning values |
| Deposition height | Numeric (mm) | Deposition height | mm | - | Layer thickness |
| Deposition width | Numeric (mm) | Deposition width | mm | - | Bead width |
| Base print speed | Numeric (mm/s) | Base print speed | mm/s | - | While depositing |
| Base travel speed | Numeric (mm/s) | Base travel speed | mm/s | - | While not depositing |

### Shell Settings (Planar strategies)

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Perimeters | Numeric | Perimeters | Integer count | - | Number of outer shell perimeters |
| Perimeter overlap | Numeric (%) | Perimeter overlap | % of bead width | - | Between adjacent perimeters |
| Perimeter max overlap | Numeric (%) | Perimeter max overlap | % of bead width | - | Maximum allowed overlap |
| Perimeter offset | Numeric (mm) | Perimeter offset | mm (positive=inward, negative=outward) | 0 | For machining margin |
| Alternate extra perimeter | Checkbox | Alternate extra perimeter | on/off | off | Extra perimeter every other layer |
| Inner perimeter width | Numeric (%) | Inner perimeter width | % of bead width | 100% | Width of inner perimeters |
| Print direction | Dropdown | Print direction | Clockwise, Counterclockwise, Alternate each layer | - | Perimeter direction |
| Print order | Dropdown | Print order | Part interior first, Part exterior first, Alternate, Inner perimeters first, Outer perimeters first, Alternate, Spiralize continuous path | Part exterior first | Controls print sequence |
| Top layers | Numeric | Top layers | Integer | - | Solid layers below "air" |
| Bottom layers | Numeric | Bottom layers | Integer | - | Solid layers above "air" |
| Initial bottom layers | Numeric | Initial bottom layers | Integer | - | Solid layers on build platform |
| Fill pattern | Dropdown | Fill pattern (top/bottom) | Linear, Offset curves | Linear | For top/bottom solid layers |

### Infill Settings

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Infill type | Dropdown | Infill type | Linear, Triangular, Grid, Triangle grid, Radial, Offset, Hexagrid, Medial, Weaving | Linear | 9 infill patterns |
| Infill density | Numeric (%) | Infill density | 0-150%+ | - | >100% = over-extrusion |
| Infill/perimeter overlap | Numeric (%) | Infill/perimeter overlap | % of bead width | - | Bonding between infill and perimeters |
| Infill before perimeter | Checkbox | Infill before perimeter | on/off | off | Print order control |
| Alternate print direction | Checkbox | Alternate print direction | on/off | off | Alternates infill direction per layer |
| Advanced infill mode | Toggle | Advanced infill | on/off | off | Per-layer infill control |
| End connector | Dropdown | End connector (Linear) | Perimeter follow, Triangular, None | - | How linear passes connect |

### Seam Settings

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Seam type | Selector | Seam type | Guided, Distributed, Random | - | 3 seam placement modes |
| Position guides (Guided) | Mode selector | Guide mode | Points, Edges, Drawing (freehand/polyline) | - | Click on part to place |
| Seam shape (Guided) | Dropdown | Seam shape | Straight, Zigzag, Triangular, Sine wave | Straight | Modulates seam around guide |
| Offset (Distributed) | Numeric (mm) | Offset distance | mm or angular degrees | - | Distance between seams |
| Use angular offset | Checkbox | Use angular offset | on/off | off | Angular distribution |
| Wipe move | Settings | Wipe | Length, speed, vertical offset | - | Post-deposition wipe |
| Lift at process end | Settings | Lift | Height (mm) | - | Vertical lift after deposition end |
| Ramp between layers | Checkbox | Ramp between layers | on/off | off | Revolved surface only |
| Ramp length | Numeric (mm) | Ramp length | mm | - | Length of layer ramp |

### Engage / Disengage Moves (Advanced)

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Use advanced | Toggle | Use advanced | on/off | off | Enables detailed control |
| Approach distance | Numeric (mm) | Approach distance | mm | - | Linear move from above |
| Arc radius | Numeric (mm) | Arc radius | mm | - | Arc connecting approach to path |
| Arc angle | Numeric (°) | Arc angle | degrees | - | Angle of connecting arc |
| Lead in length | Numeric (mm) | Lead in length | mm | 0 | Extra linear move before path |
| Lead in angle | Numeric (°) | Lead in angle from path | degrees | 0 | Angle relative to path direction |
| Wipe behaviour | Dropdown | Wipe behaviour | Along path, Straight | Along path | At process end |
| Wipe length | Numeric (mm) | Wipe length | mm | - | Distance of wipe move |
| Wipe vertical offset | Numeric (mm) | Wipe vertical offset | mm | 0 | Lift before wipe |
| Wipe open paths | Checkbox | Wipe open paths | on/off | off | Apply wipe to open paths |
| Retract distance | Numeric (mm) | Retract distance | mm | - | Linear retract from path |

### Movement Settings

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Wall speed | Numeric (mm/s) | Wall speed | mm/s | Base print speed | Perimeter speed |
| Infill speed | Numeric (mm/s) | Infill speed | mm/s | Base print speed | Infill speed |
| Travel speed | Numeric (mm/s) | Travel speed | mm/s | Base travel speed | Non-deposition speed |
| Wipe speed | Numeric (mm/s) | Wipe speed | mm/s | - | Wipe move speed |
| Initial layers count | Numeric | Initial layers | Integer | 0 | Layers with different speed |
| Initial print speed | Numeric (mm/s) | Initial print speed | mm/s | - | Speed for initial layers |
| Initial travel speed | Numeric (mm/s) | Initial travel speed | mm/s | - | Travel for initial layers |
| Speed after process on | Dropdown | Mode | Constant, Acceleration | - | Speed ramp at start |
| Speed after process on - Speed | Numeric (%) | Speed | % of path speed | - | Reduced speed percentage |
| Speed after process on - Distance | Numeric (mm) | Distance | mm | - | Ramp distance |
| Speed after process on - Steps | Numeric | Number of steps | Integer | 1 | For acceleration mode |
| Speed before process off | Dropdown | Mode | Constant, Deceleration | - | Speed ramp at end |
| Speed before process off - Speed | Numeric (%) | Speed | % of path speed | - | Reduced speed percentage |
| Speed before process off - Distance | Numeric (mm) | Distance | mm | - | Deceleration distance |
| Layer time control | Toggle | Layer time control | on/off | off | Enforce min/max layer time |
| Layer time mode | Dropdown | Mode | Wait, Adapt speed, Fixed wait | Adapt speed | How to enforce layer time |
| Minimum time/layer | Numeric (s) | Minimum time/layer | seconds | - | Minimum layer duration |
| Minimum speed | Numeric (mm/s) | Minimum speed | mm/s | - | Floor for adapt speed mode |
| Maximum time/layer | Numeric (s) | Maximum time/layer | seconds | - | Maximum layer duration |
| Maximum speed | Numeric (mm/s) | Maximum speed | mm/s | - | Ceiling for adapt speed mode |
| Deposition speed control | Checkbox | Deposition speed control | on/off | off | Vary speed for deposition rate |

### Optimization Settings

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Remove aligned points | Checkbox | Remove aligned points | on/off | - | Reduces file size |
| Minimum point distance | Numeric (mm) | Min point distance | mm | 0.1 | Removes close points |
| Maximum point distance | Numeric (mm) | Max point distance | mm | - | Adds interpolation points |
| Minimum path length | Numeric (mm) | Min path length | mm | - | Removes short paths |
| Avoid short travel moves | Numeric (mm) | Avoid short travel | mm | - | Converts short travels to print moves |
| Corner detection | Toggle | Corner detection | on/off | off | Sharp corner handling |
| Corner start zone | Numeric (mm) | Start zone length | mm | - | Zone before corner |
| Corner end zone | Numeric (mm) | End zone length | mm | - | Zone after corner |
| Corner compensation | Dropdown | Compensation type | Triangular, Circular | - | Geometry modification at corners |
| Arc fitting | Toggle | Arc fitting (experimental) | on/off, Tolerance (mm) | off, 0.1mm | Approximates linear moves with arcs |

### Additions Settings

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Add brim | Checkbox | Add brim | on/off | off | Adhesion improvement |
| Brim line count | Numeric | Line count | Integer | - | Number of brim lines |
| Brim distance from part | Numeric (mm) | Distance from part | mm (negative = inside only) | 0 | Distance to part edge |
| Print from outside in | Checkbox | Print from outside in | on/off | on | Brim print direction |
| Avoid concave areas | Checkbox | Avoid concave areas | on/off | off | Skip internal holes |
| Add raft | Checkbox | Add raft | on/off | off | Under-part support |
| Raft offset from part | Numeric (mm) | Offset from part | 0-200 mm | - | Raft extension beyond part |
| Raft shape | Dropdown | Raft shape | Perimeter, Convex hull, Min bounding box, Aligned bounding box | Perimeter | Shape of raft |
| Raft layers | Numeric | Raft layers | Integer | - | Number of raft layers |
| Raft distance to part | Numeric (mm) | Distance to part | mm (negative pushes into part) | - | Gap between raft and part |

### Deposition Zones (WAAM/Pellet specific)

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Enable zones | Toggle | Deposition zones | on/off | off | Available for WAAM CMT/PAW or experimental |
| Start zone length | Numeric (mm) | Start zone | mm | - | Length of start zone |
| End zone length | Numeric (mm) | End zone | mm | - | Length of end zone |

### Corner Compensation

| Control | Type | Label | Options/Range | Default | Notes |
|---------|------|-------|---------------|---------|-------|
| Corner start zone | Numeric (mm) | Start zone | mm | - | Distance before corner |
| Corner end zone | Numeric (mm) | End zone | mm | - | Distance after corner |
| Deposition compensation | Numeric | Factor | multiplier | 1.0 | Deposition rate at corners |
| Speed compensation | Numeric | Factor | multiplier | 1.0 | Speed at corners |
| Geometry compensation | Dropdown | Type | Triangular, Circular | None | Path geometry modification |
| Triangle/Circle size | Numeric (mm) | Length/Radius | mm | - | Size of compensation |

---

# AREA 4: Toolpath Visualization & Editing

## AdaOne - Toolpath Visualization

### Overlays (Color Coding)

| Overlay | Type | What it Shows | Color Scale |
|---------|------|---------------|-------------|
| Travel moves | Toggle | Travel vs deposition paths | on/off visibility |
| Tool orientation | Toggle | Coordinate axes at each target | RGB axes (R=X, G=Y, B=Z) |
| Seam positions | Toggle | Start/end of print paths | Yellow=start, Blue=end |
| Reachability check | Background | Real-time reach analysis | Red=unreachable |
| Tool path order | Color map | Execution order | Sequential gradient |
| Deposition | Color map | Deposition multiplier | Relative to base bead |
| Tool speed | Color map | Speed in mm/s | Gradient |
| Layer time | Color map | Time per layer in seconds | Gradient |
| Layer length | Color map | Length per layer in mm | Gradient |
| Process mode | Color map | Process mode per point | Distinct colors |
| Toolpath type | Color map | Path types | Distinct colors |
| Bead overhang | Color map | Overlap with previous layer | 0-100% gradient |
| Tool ID | Color map | Different tools | Distinct colors |
| Rotation | Color map | Tool axis rotation degrees | Gradient |
| Curvature | Color map | Curvature per mm | Gradient |
| Override limits | Toggle | Custom min/max for visualization | Does not affect values |

### Part Overlays

| Overlay | What it Shows | Notes |
|---------|---------------|-------|
| Overhangs | Angle relative to slicing plane | Red=critical, Yellow=moderate; >45° problematic |

### Graph View

| Data Type | Description |
|-----------|-------------|
| Deposition multiplier | Relative to base bead dimensions |
| Deposition rate | Material deposited in kg/h or cm3/s |
| Tool speed | TCP speed |
| Layer time | Time per layer |
| Layer length | Length per layer |
| Bead overhang | Overhang amount |
| Curvature | Path curvature |
| Machine axes | Joint values (updates real-time) |
| Point spacing | Distance between adjacent points |
| Lock to simulation | Button to follow simulation position |

### Toolpath Analytics

| Category | Statistics |
|----------|-----------|
| Geometry & Structure | Layer count, Point count, Total path length, Travel move length, Path type distribution, Process starts/stops, Point spacing, Bead width/height, Bead ratio, Overhangs |
| Motion & Kinematics | Execution time, TCP speed, Target rotation (reorientation speed), Layer time |
| Process | Material usage, Deposition rate/flow rate |
| Quality rating | Color bar: Green=pass, Yellow=warning, Red=critical |
| Checks performed | Singularities, Out of reach, Deposition rate, Bead ratios, Tool reorientation speed, Overhangs, Layer time |

### Cost Modelling

| Parameter | Type | Notes |
|-----------|------|-------|
| Energy cost/hour | Numeric | Of machine time |
| Maintenance cost/hour | Numeric | Of machine time |
| Depreciation cost/hour | Numeric | Of machine time |
| Min machine time/job | Numeric (hours) | Minimum per job |
| Operator cost/hour | Numeric | Labor cost |
| Operator time/job | Numeric (hours) | Per job |
| Programming time/job | Numeric (hours) | Per job |
| Post-processing cost | Numeric | Per part/job |
| Consumables cost | Numeric | Per part/job |
| Scrap rate | Numeric (%) | Percentage |
| Overhead rate | Numeric (%) | Percentage |
| Currency | Settings | Default EUR, configurable |

## AdaOne - Toolpath Editor

### Access
- Three-dot menu in right panel when toolpath is selected

### UI Layout
- 3D view: Interact with toolpath
- Layer view: Select which layers to display
- Main toolbar: Selection and filtering tools
- Right panel: List of modifications and settings

### Selection Modes

| Mode | Description |
|------|-------------|
| Path selection | Select entire paths |
| Point selection | Select individual points |
| Selection filters | Filter by properties (length, layer number, overhang, curvature) |
| Add to / Remove from | Modify existing selection |

### Available Modifications

| Modification | Category | Description | Options |
|-------------|----------|-------------|---------|
| Process on | Process state | Toggle process on/off | on/off per selection |
| Job number | Process state | Set welding job number | WAAM only |
| Current | Process state | Set welding current | WAAM/WLAM |
| Wire feed speed | Process state | Set wire feed speed | WAAM/WLAM |
| Spindle speed | Process state | Set spindle RPM | Machining only |
| Deposition multiplier | Deposition | Scale local deposition rate | Numeric factor |
| Speed - Fixed value | Motion | Apply fixed speed | mm/s |
| Speed - Scale by coefficients | Motion | Scale min/max speeds | Two scaling factors |
| Speed - Layer time | Motion | Set time per layer | Seconds |
| Start delay | Motion | Delay before path | Seconds |
| End delay | Motion | Delay after path | Seconds |
| Stop at end | Motion | Full stop after path | on/off |
| Density factor | Density | Scale point density | Factor (2 = double) |
| Minimum distance | Density | Min distance after densification | mm |
| Tool axis rotation | Tool orientation | Rotate around tool axis | Override or offset |
| Unidirectionality | Tool orientation | TCP axis follows path | on/off |
| Override orientation | Tool orientation | Direction of tool vector | Default, Normal, Tangent, Fixed |
| Global offset | Translation | Translate in X,Y,Z | mm relative to toolpath frame |
| Flip path direction | Winding | Reverse path direction | CW/CCW |
| Remove | Remove | Delete selected points/paths | Irreversible (but undo works) |

### Interpolation of Changes

| Interpolation Basis | Available For | Description |
|---------------------|---------------|-------------|
| Layer number | Point & path | Smooth changes across layers |
| Path length | Point & path | Based on path length |
| Overhang | Point only | Based on local overhang |
| Curvature | Point only | Based on geometry curvature |
| Deposition | Point only | Based on local deposition value |
| Bead number | Point & path | Cumulative bead number |
| Bead number within layer | Point & path | Per-layer bead number |
| Invert interpolation | Checkbox | Reverse the interpolation direction |
| Custom min/max | Numeric | Override interpolation range |

---

# AREA 5: Simulation — UI Controls & Display

## AdaOne - Simulation

### Playback Controls
- **Tool path slider**: Layer-by-layer scrubber in the 3D view
- **Arrow keys**: Navigate between points in the slider
- **Layer mode**: Animate layer by layer
- **Speed**: Controlled via path planning settings (actual robot speed)

### Robot Visualization During Simulation
- Full animated robot with all joints
- TCP position displayed
- Trail/trace of TCP path (via overlays)
- Real-time reachability checking (red markers for unreachable)
- Collision detection (alerts when detected)
- Graph view syncs with simulation position
- Lock graph to current simulation position (button)

### Simulation Data Display

| Data | Where Displayed | Notes |
|------|----------------|-------|
| Current layer / total layers | Slider | Visual indicator |
| Joint angles | Real-time during sim | All joints + external axes |
| TCP position | Real-time | XYZ + orientation |
| Tool speed | Graph view / overlay | mm/s |
| Deposition rate | Graph view / overlay | kg/h or cm3/s |
| Layer time | Graph view / overlay | Seconds per layer |
| Bead overhang | Graph view / overlay | % overlap |
| Machine axes values | Graph view | Updates real-time if toolpath modified |
| Point spacing | Graph view | Distance between points |
| Curvature | Graph view | Per mm |

### Validation Checks

| Check | How Displayed | Auto/Manual |
|-------|---------------|-------------|
| Reachability/Out of reach | Red markers on toolpath, overlay | Real-time background check |
| Singularity detection | Quality rating bar | Background analysis |
| Collision detection | Alerts/notifications | Can be disabled for hidden entities |
| Joint limits | Via axis config | Restricted during setup |
| Bead overhang | Overlay + analytics | Background analysis |
| Deposition rate warnings | Quality bar + analytics | If exceeds max extruder RPM |
| Tool reorientation speed | Quality bar + analytics | Background analysis |

### Tool Path Quality Rating Bar
- Located at top of analytics dialog
- Color-coded rectangles: Green=pass, Yellow=warning, Red=critical
- Hover for details on warnings/issues
- Checks: Singularities, out of reach, deposition rate, bead ratios, reorientation speed, overhangs, layer time

---

# AREA 6: Post Processor & Code Generation

## AdaOne - Post Processors

### Architecture
- Access: Main Menu > Libraries > Post Processors
- Create new: "Create new" button in bottom left
- 3 tabs: General, Events, Interpolation
- Must click "Save" to persist changes

### Format Presets (Output Formats)

| Format | Output | Notes |
|--------|--------|-------|
| G-code | .gcode / .nc | Highly configurable, includes orientation & external axes |
| ABB RAPID | .mod / .modx | Native ABB programming |
| ABB RAPID Arc Welding | .mod | ArcL/ArcC instructions |
| KUKA KRL | .src | Native KUKA programming |
| KUKA SIEMENS | - | For Siemens-controlled KUKA robots |
| KUKA PathStream | .csv | For App4PostPro option |
| FANUC LS | .ls + .kl + .dt | TP programs with KAREL orchestration |
| CSV | .csv | Generic data export |
| YASKAWA INFORM II | .jbi | Pulse-based joint output |
| Siemens Sinumerik RMR | .nc | Run My Robot G-code |
| Ada3DP | .ada3dp | Protocol Buffer format for Python/external editing |
| OpenSBP | - | Experimental |

### General Settings

| Control | Type | Label | Options | Notes |
|---------|------|-------|---------|-------|
| Format preset | Dropdown | Format | (see above) | Sets output language |
| Use as default | Checkbox | Use as default | on/off | Preselected when exporting |
| Split method | Dropdown | Split method | None, Per layer, Per points, Per points per layer | Handles large programs |
| Enable circular motion | Checkbox | Circular motion | on/off | MoveC instructions |
| Output tool data | Checkbox | Output tool data | on/off | Export TCP definition |
| Output workobject data | Checkbox | Output workobject data | on/off | Export work frame |

### Events System

| Event | When Triggered | Description |
|-------|----------------|-------------|
| Program start | Beginning of program | Header, variable definitions |
| Program end | End of program | Cleanup, homing |
| Layer start | Start of each layer | Layer-specific setup |
| Layer end | End of each layer | Interlayer actions |
| Process on | Before first point with process on | Torch/extruder activation |
| Process off | After last point with process on | Torch/extruder deactivation |
| Before each point | Before each motion instruction | Per-point actions |
| After each point | After each motion instruction | Per-point actions |
| After first point | After first process-on point | Initial stabilization |
| Before last point | Before last process-on point | End-of-path preparation |

### Post Processor Variables

| Variable | Scope | Description |
|----------|-------|-------------|
| {version} | All | AdaOne version |
| {layerIndex} | Layer events | Current layer number |
| {time} | Point events | Current time |
| {depositionFactor} | Point events | Deposition multiplier |
| {spindleSpeed} | Point events | Spindle RPM |
| {pointAngle} | Point events | Direction change at point |
| {mat0_material_constant} | Material | Material constant value |
| {mat0_extrusion_constant} | Material | Extrusion constant (rev/cm3) |
| {mat0_drying_time} | Material | Drying time (hours) |
| {mat0_drying_temperature} | Material | Drying temperature (°C) |
| {mat0_bed_temperature} | Material | Build plate temperature (°C) |
| {mat0_heatzone_1} to {mat0_heatzone_5} | Material | Extruder heat zone temps (°C) |
| {mat0_material_id} | Material | Material identifier string |

### Interpolation Settings (Zone/Blending)

| Robot Brand | Options |
|-------------|---------|
| KUKA | C_DIS, C_VEL |
| ABB | fine, z0, z1, z5, z10, z15, z20, z30, z40, z50, z60, z80, z100, z150, z200, custom zonedata |

### ABB-Specific Options

| Control | Type | Description |
|---------|------|-------------|
| Motion instructions | Dropdown | Default (MoveL/TriggL) or Custom (AdaL/AdaC) |
| Deposition unit | Dropdown | cm3/s or RPM |
| Deposition precision | Numeric | Decimal places |
| Use load sessions | Checkbox | Dynamic module loading |
| Wrap targets in function | Checkbox | getLinRT/getCircRT for dynamic offset |
| EGM motion stream | Checkbox | Real-time external control |
| Export program file | Checkbox | .pgf file output |
| Override tool frame | Checkbox | Export tooldata variable |
| Override work frame | Checkbox | Export workobject variable |

### G-Code Specific Options

| Control | Type | Description |
|---------|------|-------------|
| Output orientation | Toggle | Include orientation data |
| Orientation format | Dropdown | Direction vector or Euler angle |
| Orientation notation | Text (3 fields) | e.g., nX, nY, nZ |
| Output extrusion axis | Toggle | Include extrusion data |
| Extrusion notation | Text | e.g., E or EM= |
| Extrusion unit | Dropdown | Filament length (mm), Volume (cm3/mm3), Deposition factor, RPM, Feed rate (cm3/s), Bead area (mm2) |
| Extrusion precision | Numeric | Decimal places |
| Extrusion scaling factor | Numeric | Generic multiplier |
| Relative extrusion | Checkbox | Relative vs absolute |
| Modal extrusion | Checkbox | Only output on change |
| Output speed | Toggle | Include speed data |
| Speed notation | Text | e.g., F |
| Output external axis | Toggle | Include external axis data |
| External axis notation | Text (6 fields) | EA, EB, EC, ED, EE, EF |
| Output line number | Toggle | Include line numbers |
| Line number base | Dropdown | 1, 2, 5, 10 |
| Travel instruction | Dropdown | G0 or G1 |
| Position precision | Numeric | Decimal places |
| Modal Z commands | Checkbox | Only output Z on change |

---

# AREA 7: Monitoring & Robot Connection

## AdaOne - Manufacturing View

### Connection Methods

| Method | Description | Requirements |
|--------|-------------|-------------|
| OPC UA / Ethernet | Real-time data exchange | RJ45 Ethernet connection |
| ABB EGM | High-frequency streaming (250 Hz) | ABB EGM option |
| ABB WebSocket | Synchronous data exchange | Available on modern ABB controllers |
| KUKA RSI | Real-time interface | KUKA RSI option |
| FANUC User Socket | 4-10 ms data streaming | R636/R648 option |
| Yaskawa HSES | Real-time connection | HSES driver |

### Real-Time Monitoring Data

| Data Category | Parameters |
|---------------|-----------|
| Proprioceptive | Joint positions, TCP position/velocity/acceleration/jerk, axis states |
| Process | Feedrate, power, gas flow, welding parameters |
| Exteroceptive | Pyrometer, camera, distance sensors |
| Manufacturing logs | MongoDB storage (experimental), time-series collection |

### File Transfer
- ABB: Direct file transfer to controller (feature preview since v0.504)
- FANUC: AdaPack for drip-feed execution
- KUKA: PointLoader or standard KRL

---

# AREA 8: Multi-Process & External Axes

## AdaOne - Multi-Process Support

### Multi-Process Heads
- Multiple process heads per robot (since v0.494)
- Each head can have multiple tool frames
- Switch between processes in single cell
- Combine additive + subtractive in same project

### Tool Path Sequencer
- Access: Main Menu > Add Tool Path Sequence
- Combines multiple toolpaths in series or parallel
- Execution modes: Serial, Parallel

| Control | Type | Label | Options | Notes |
|---------|------|-------|---------|-------|
| Path execution mode | Dropdown | Strategy | Serial, Parallel | Per sequence |
| Modulo type (Parallel) | Dropdown | Modulo type | Layer, Layer pattern, Bead | How layers interleave |
| Modulo index | Numeric/Pattern | Pattern | Integer or pattern (e.g., 3:2:2) | Layer count per toolpath |
| Retraction move | Numeric (mm) | Retraction | mm | Before switching toolpaths |
| Approach move | Numeric (mm) | Approach | mm | After switching toolpaths |
| Travel speed | Numeric (mm/s) | Travel speed | mm/s | Between toolpaths |

### External Axis Coordination

| Feature | Description |
|---------|-------------|
| Positioner interpolation | Per-toolpath interpolation settings |
| Dynamic axis 1 | Enable/disable for 2-axis positioners |
| Override positioner limits | Override axis 1 limits |
| Linear track interpolation | Fixed axis value or constant offset |
| Coordinated motion | Synchronized robot + external axes |
| Positioners on linear tracks | Combined setup with coordinated motion |

### Process Modes
- Multiple Process On instructions within single Process Head
- Different process settings for different areas of same part
- Available for WAAM welding (different welding jobs per region)

### Conditional IO Events

| Control | Type | Description |
|---------|------|-------------|
| Add event | Button | Select IO to trigger |
| IO definition | Dialog | Name, Signal type (DI/DO/AI/AO), Type (1-bit/8-bit), Function, Min/Max |
| Variable | Dropdown | Variable to use as condition |
| Comparison | Dropdown | Operator (>, <, =, etc.) |
| Threshold | Numeric | Trigger value |
| Multiple conditions | Combine | AND/OR multiple conditions per IO |

---

# COMPETITOR RESEARCH

---

## RoboDK — Competitor Analysis

### Overview
- **Type**: Offline robot programming and simulation software
- **Strength**: Largest robot library (600+ models, 50+ manufacturers), extensive post processor collection (100+)
- **Architecture**: Desktop application (Windows/Mac/Linux) + Web version
- **UI Layout**: Main Menu + Toolbar + Station Tree (left panel) + 3D Scene (center) + Properties panel (right)

### Area 1: Cell/Robot Setup

| Feature | RoboDK Implementation |
|---------|----------------------|
| Robot import | File > Open Robot Library; online library at robodk.com/library; filter by brand/type/model |
| Robot brands | ABB, KUKA, Fanuc, Yaskawa, Staubli, UR, Comau, Denso, Doosan, Epson, Han's, JAKA, Kawasaki, Mecademic, Nachi, Omron-TM, Siemens, 40+ more |
| Robot types | 6-axis arms, Delta, SCARA, palletizing, PKM |
| Custom robots | Import DH parameters or URDF; Model Builder wizard |
| Reference frames | Drag & drop in Station Tree; teach 3-point calibration; manual XYZ + Euler entry |
| Euler angle formats | X>Y>Z (Fanuc/Motoman), X>Y'>Z'' (Staubli), Z>Y'>X'' (KUKA/Nachi), Quaternion (ABB), Custom Script |
| Tool (TCP) definition | Import tool 3D geometry; set TCP via 6DOF numeric entry; Alt+Shift to drag TCP interactively |
| External axes | Turntables, positioners, linear rails, gantries from library |
| Collision detection | Toolbar toggle button; check all pairs; visual highlighting |
| 3D navigation | Middle button = Pan, Right button = Rotate, Scroll = Zoom; configurable to match CAD software |
| Keyboard shortcuts | Alt = move reference frame, Alt+Shift = move TCP, F1 = help, F2 = rename, F6 = generate programs, F7 = show/hide |

### Area 3: Slicing / Path Planning (3D Printing Plugin)

| Feature | RoboDK Implementation |
|---------|----------------------|
| 3D printing support | Via dedicated 3D Printing add-in plugin |
| Input formats | G-code from any slicer (Cura, PrusaSlicer, etc.) |
| Workflow | Import G-code > Convert to robot paths > Simulate > Post-process |
| Slicing | External (not built-in); relies on standard FDM slicers |
| Path visualization | Color-coded toolpath lines in 3D scene |
| Multi-axis support | Via custom scripting; not native non-planar slicing |
| Robot machining | Separate module: curve follow project, point follow project, 3-axis/5-axis |
| CAM integration | Plugins for Fusion 360, Mastercam, hyperMILL, SolidWorks, Rhino, BobCAD, etc. |

### Area 5: Simulation

| Feature | RoboDK Implementation |
|---------|----------------------|
| Playback | Double-click program to simulate; Play/Pause/Stop |
| Speed control | Fast simulation button; hold spacebar to accelerate |
| Joint display | Robot panel shows all joint angles in real-time |
| Collision checking | Real-time during simulation; visual indicators |
| Program generation | Right-click > Generate Robot Program |
| Station tree | Hierarchical: Station > Robot > Tools > Reference Frames > Programs > Targets |

### Area 6: Post Processors

| Feature | RoboDK Implementation |
|---------|----------------------|
| Architecture | Each post processor = one Python (.py) file in C:/RoboDK/Posts/ |
| Count | 100+ default post processors for 50+ manufacturers |
| Selection | Right-click robot > Select Post Processor; or Robot Panel > Parameters |
| Editor | Program > Post Processor Editor (GUI plugin); or Program > Add/Edit Post Processor (text editor) |
| Customization | Inherit from existing post; override specific methods (setFrame, setTool, setSpeed, MoveJ, MoveL) |
| Key methods | setFrame(), setTool(), setSpeed(), MoveJ(), MoveL(), MoveC(), angles_2_str(), pose_2_str() |
| Output formats | ABB RAPID (IRC5, S4C), KUKA KRL (KRC1-5), Fanuc (R30iA/RJ3), Yaskawa INFORM, Staubli VAL3, UR Script, Comau PDL, Denso PAC, Siemens Sinumerik, G-code (multiple), CSV, 100+ more |
| Key ABB post processors | ABB RAPID IRC5, ABB RAPID IRC5 Robtargets, ABB RAPID S4C |
| Key KUKA post processors | KUKA KRC1, KRC2, KRC2_CamRob, KRC2_DAT, KRC4, KRC4 Config, KRC4 DAT, KRC5, KUKA IIWA, KUKA CNC, KUKA EntertainTech |
| Key Fanuc post processors | Fanuc R30iA, Fanuc R30iA Arc, Fanuc RJ3 |
| Customizable variables | MAX_LINES_X_PROG, INCLUDE_SUB_PROGRAMS, speed limits, frame definitions, motion types |
| Debugging | RoboDK-Debug.bat enables debug mode; preprocessed Python files in temp folder |

### Area 6 (cont.): Post Processor Event Methods (RoboDK RobotPost class)

| Method | Trigger/Purpose |
|--------|-----------------|
| `ProgStart()` | Program start header generation |
| `ProgFinish()` | Program end footer generation |
| `ProgSave()` | Save generated file to disk |
| `setFrame()` | Reference frame change |
| `setTool()` | Tool/TCP change |
| `setSpeed()` | Speed parameter change |
| `MoveJ()` | Joint movement instruction |
| `MoveL()` | Linear movement instruction |
| `MoveC()` | Circular movement instruction |
| `Pause()` | Pause/dwell instruction |
| `setDO()` | Set digital output |
| `setAO()` | Set analog output |
| `waitDI()` | Wait for digital input |
| `RunCode()` | Custom code injection point |
| `RunMessage()` | Display message on controller |
| `angles_2_str()` | Convert joint angles to output format |
| `pose_2_str()` | Convert poses to string representation |

### RoboDK Program Instruction Types

| Category | Instructions |
|----------|-------------|
| Movement | MoveJ (joint), MoveL (linear), MoveC (circular -- requires 2 targets) |
| Frame Control | Set Reference Frame, Set Tool Frame |
| Speed | Set Speed (joint and Cartesian independently) |
| Blending | Set Rounding value (blend radius between moves) |
| I/O | Set Digital Output, Set Analog Output, Wait Digital Input, Wait Analog Input |
| Timing | Pause (with optional timeout in ms) |
| Communication | Show Message (display on controller) |
| Program Flow | Program Call (blocking), Start Thread (non-blocking, for multi-robot) |

### RoboDK Simulation Speed Settings (Tools > Options > Motion)

| Setting | Default | Description |
|---------|---------|-------------|
| Normal simulation ratio | 5x | Multiplier over real-time |
| Fast simulation ratio | 100x | Multiplier for fast-forward |
| Collision PRM samples | 100 | Random samples for avoidance planner |
| PRM edges per sample | 25 | Graph connectivity parameter |

### RoboDK TCP Calibration Methods

| Method | Description | Min Points |
|--------|-------------|------------|
| Point-based (XYZ) | Touch fixed point with different orientations | 3-4 min, 8+ recommended |
| Plane-based (XYZ) | Touch plane with different orientations | 3-4 min, 8+ recommended |

### RoboDK 3D Printing / AM Plugin

| Feature | Detail |
|---------|--------|
| Access | Utilities > 3D Print Project |
| G-code import | Any slicer output; auto-calculated material flow (E directive) |
| Integrated slicers | Slic3r (built-in), Ultimaker Cura (custom profile) |
| Cura workspace | Custom printer profile matching robot reach (e.g., 6000x2500x2000mm) |
| Extruder control | E directive mapped to program call or analog output |
| Flow calculation | Automatic from movement distance and robot velocity |
| Multi-axis | Via custom scripting; not native non-planar |

### RoboDK External Axes Detail

| Type | Description |
|------|-------------|
| Linear Rail | Single-axis prismatic; extending robot reach |
| 1-Axis Turntable | Single rotary axis; simple positioner |
| 2-Axis Turntable | Tilt + rotate; complex positioner for welding/AM |
| Pedestal | Fixed elevated base; mounting platform |
| Custom Mechanism | User-defined via Utilities > Model Mechanism |
| Synchronization | Up to 6 external axes synced with robot (12 total) |
| Coupled joints | Adjustable weight/priority for motion optimization |

---

## AiBuild — Competitor Analysis

### Overview
- **Type**: AI-enhanced robotic manufacturing platform (AiSync)
- **Strength**: AI-powered path planning, real-time monitoring with ML defect detection
- **Architecture**: Cloud/Desktop hybrid; uses standard robot controllers
- **Processes**: FDM/FFF, pellet extrusion, WAAM, DED, concrete

### Area 1: Cell/Robot Setup

| Feature | AiBuild Implementation |
|---------|----------------------|
| Robot support | ABB, KUKA, Fanuc, UR, Comau, Yaskawa |
| Robot import | Select from built-in library by brand/model |
| TCP definition | 6DOF numeric entry (XYZ + RPY) |
| External axes | Positioners and linear tracks; coordinated motion |
| Cell configuration | Visual cell builder with drag-and-drop equipment placement |

### Area 3: Slicing / Path Planning

| Feature | AiBuild Implementation |
|---------|----------------------|
| Slicing engine | Proprietary AI-enhanced slicer |
| Strategies | Planar (standard), Adaptive layer height, Non-planar (AI-optimized), Continuous spiral |
| AI features | Automatic orientation optimization, support structure generation, path optimization for strength |
| Layer height | Adaptive based on geometry complexity |
| Infill patterns | Standard FDM patterns + AI-optimized density gradients |
| Speed optimization | AI adjusts speed based on thermal analysis |
| Multi-material | Support for multi-material paths |
| Path visualization | Color-coded by type (perimeter/infill/travel), speed, temperature |

### Area 5: Simulation

| Feature | AiBuild Implementation |
|---------|----------------------|
| Simulation type | Full robot animation with material deposition |
| Collision detection | Real-time during simulation |
| Thermal simulation | AI-predicted thermal field visualization |
| Build time estimation | ML-based accurate time prediction |

### Area 6: Post Processors

| Feature | AiBuild Implementation |
|---------|----------------------|
| Output formats | ABB RAPID, KUKA KRL, Fanuc TP, UR Script, G-code |
| Custom events | Process on/off, layer change, tool change triggers |
| I/O control | Configurable digital/analog I/O mapping |

### Area 7: Monitoring (Key Differentiator)

| Feature | AiBuild Implementation |
|---------|----------------------|
| Real-time monitoring | Camera-based layer tracking with ML analysis |
| Defect detection | AI identifies under-extrusion, over-extrusion, layer adhesion issues |
| Thermal monitoring | Infrared camera integration |
| Adaptive control | Real-time speed/temperature adjustment based on sensor feedback |
| Dashboard | Web-based monitoring dashboard with live feeds |
| Data logging | Full process data captured to cloud database |

---

## CEAD AM Flexbot — Competitor Analysis

### Overview
- **Type**: Large-scale pellet extrusion system with integrated robot cell
- **Uses**: Often paired with AdaOne software for path planning
- **Processes**: Pellet extrusion (large-format AM), milling (hybrid)

### Cell Configuration (Specific to CEAD)

| Feature | CEAD Implementation |
|---------|---------------------|
| Robot | ABB IRB 6700 series (typically 200/2.60) |
| Extruder | CEAD pellet extruder (up to 12 kg/hr) |
| Linear track | Up to 14m Vansichen linear track |
| Build volume | Up to 4m x 2m x 1.5m (depending on configuration) |
| Milling spindle | Optional hybrid milling head |
| Temperature control | Heated build plate, chamber temperature monitoring |
| AdaOne integration | Pre-configured cell templates available in AdaOne |
| Setup in AdaOne | Main Menu > Getting started > Setup CEAD AM Flexbot wizard |
| CEAD-specific fields | Track length, riser height (595mm options), robot angle (0°/180°) |

---

## Meltio Space — Competitor Analysis

### Overview
- **Type**: Wire-laser DED (Directed Energy Deposition) software
- **Strength**: Metal wire AM for part repair and multi-material metal printing
- **Processes**: Wire-laser DED exclusively

### Area 1: Setup

| Feature | Meltio Implementation |
|---------|----------------------|
| Integration | Designed for Meltio engine mounted on robot or CNC |
| Robot support | UR, KUKA, ABB (with Meltio integration kit) |
| CNC support | Mounts on 3-axis or 5-axis CNC machines |
| TCP definition | Pre-calibrated with Meltio engine specs |

### Area 3: Path Planning

| Feature | Meltio Implementation |
|---------|----------------------|
| Slicing | Proprietary slicer optimized for wire-laser DED |
| Strategies | Planar slicing, spiral/helical, cladding |
| Parameters | Wire feed rate, laser power, travel speed, shielding gas flow |
| Layer height | Typically 0.5-1.0mm for metal wire |
| Bead width | 1.0-3.0mm typical |
| Multi-material | Dual wire feed for material mixing/switching |

### Area 5: Monitoring

| Feature | Meltio Implementation |
|---------|----------------------|
| Melt pool monitoring | Integrated camera for melt pool visualization |
| Thermal monitoring | Real-time temperature tracking |
| Process feedback | Closed-loop laser power adjustment |
| Quality metrics | Layer-by-layer quality assessment |

---

## Open-Source Slicers for Robotic AM

### ORNL Slicer 2 (Primary Integration Target for OpenAxis)

| Feature | Details |
|---------|---------|
| Repository | github.com/ORNLSlicer/Slicer-2 |
| Language | C++ with Qt GUI |
| License | Custom ORNL license |
| Planar slicing | Standard horizontal layer slicing |
| Non-planar | Limited non-planar capabilities via research plugins |
| Multi-axis | 5-axis toolpath generation for BAAM/LSAM |
| Path types | Perimeter, infill (raster, offset, skeleton), support |
| Infill patterns | Linear, grid, triangular, hexagonal, concentric |
| Output | G-code, custom formats; extensible post-processor |
| Robot support | G-code output convertible to robot programs via external tools |
| Strengths | Large-format AM focus, ORNL research backing, industrial use at ORNL MDF |
| Limitations | Limited UI polish, documentation sparse, not actively maintained recently |

### FullControl GCode Designer

| Feature | Details |
|---------|---------|
| Website | fullcontrolgcode.com |
| Architecture | Python library (pip install fullcontrol) |
| Approach | Point-by-point path definition in Python scripts |
| Output | G-code for standard printers |
| Non-planar | Full non-planar support (define any 3D path) |
| Parametric | Fully parametric; complex geometry via code |
| Robot support | Not native; output is G-code |
| Strengths | Ultimate flexibility for research; great for custom path strategies |
| Limitations | No GUI; requires Python coding; no robot-specific features |

### CuraEngine (with Robotic AM Extensions)

| Feature | Details |
|---------|---------|
| Base slicer | Ultimaker Cura / CuraEngine (open source, C++) |
| Robotic extensions | Community plugins for robot output; Griffin flavor for Ultimaker |
| Infill patterns | Lines, Grid, Triangles, Tri-hexagon, Cubic, Octet, Quarter cubic, Concentric, Zigzag, Cross, Cross 3D, Gyroid, Lightning |
| Non-planar | Research plugins (e.g., non-planar Cura by github.com/nicklprice) |
| Strengths | Most feature-rich open-source slicer engine; massive community |
| Limitations | Designed for 3-axis FDM; robot support is add-on, not native |

### PrusaSlicer / SuperSlicer / OrcaSlicer

| Feature | Details |
|---------|---------|
| Non-planar | SuperSlicer has experimental non-planar features |
| Multi-axis | Not supported natively |
| Robotic AM | Not designed for; some community forks exist |
| Infill patterns (PrusaSlicer) | Rectilinear, Grid, Triangles, Stars, Cubic, Line, Concentric, Honeycomb, 3D Honeycomb, Gyroid, Hilbert Curve, Archimedean Chords, Octagram Spiral, Adaptive Cubic, Lightning |
| Strengths | Excellent UI/UX reference for slicer interface design |
| Limitations | 3-axis only; no robot support |

### Research / Academic Slicers

| Slicer | Focus | Key Feature |
|--------|-------|-------------|
| Curved Layer Fused Deposition Modeling (CLFM) | Non-planar | Curved layer slicing along surfaces |
| COMPAS Slicer | Robotic AM | Python, integrates with COMPAS ecosystem for robotic fabrication |
| Silkworm (Grasshopper) | Robotic AM | G-code generation from Grasshopper curves |
| HAL Robotics | Robotic AM | Programming framework for multi-robot systems |

---

# ADDITIONAL DETAILS FROM ADAONE RESOURCE CENTER (Live Browsing)

## Resource Center Site Structure (adaone.adaxis.eu)

### Top-Level Navigation
- Product
- Getting Started
- **Documentation** (main section)
- Learn
- Downloads

### Documentation Sections
1. **Setup and configuration**
   - Overview, Robotic arms, External axes, Process heads, Process control, Work frames, Materials, Print nozzles, Cutting tools, Cell elements
2. **Programming**
   - Overview
   - **Additive manufacturing**: Process settings, Strategies (10 types), Slicing modes, Continuous tool paths, Infill designer, Movement settings, Deposition zones, Seam control, Engage and disengage, Corner compensation
   - **Machining**: (sub-pages for subtractive strategies)
   - **3D scanning**
   - Process modes, Conditional IO events, Tool path sequencer, Tool path editor
3. **Plugins** (AdaSync/Grasshopper, etc.)
4. **Workflows** (Moulds and tooling, etc.)
5. **Analytics** (Overlays, Graph view, Quality rating, Cost modelling)
6. **Design and part optimization**
7. **Post processors**
8. **Resource management** (Cells, Projects, User libraries)
9. **Shortcuts and hotkeys**
10. **Experimental**

### Getting Started Section
- Installation and activation
- System requirements
- License definition
- Troubleshooting

### Configuration Section (from resource center)
- **Create a robot cell**: Step-by-step guide
- **Setup a CEAD AM Flexbot**: Specific configuration for CEAD systems
- **Use AdaOne with ABB 3DP**: ABB-specific workflow
- **PowerPac**: Additional functionality module

### Path Planning Section (from resource center)
- **Slicing strategies**: Central guide to all 10+ additive strategies
- **Engage / disengage travel moves**: Detailed approach/retract configuration
- **Moulds and tooling workflow**: Specialized hybrid manufacturing workflow

### Resources
- **Sample cells**: Pre-configured downloadable cell files
- **Sample parts**: Test geometry for evaluation
- **Material libraries**: Pre-defined material profiles

## Key AdaOne Process Settings (from Resource Center)

| Setting | Type | Description |
|---------|------|-------------|
| Material | Dropdown | Linked to material library; filtered by process type |
| Material profile | Dropdown | Preset values for layer height, perimeters, infill, etc. |
| Deposition height | Numeric (mm) | Layer height / bead height |
| Deposition width | Numeric (mm) | Bead width / extrusion width |
| Base print speed | Numeric (mm/s) | Speed during material deposition |
| Base travel speed | Numeric (mm/s) | Speed during non-deposition moves |

## Key Differences: AdaOne vs RoboDK

| Feature | AdaOne | RoboDK |
|---------|--------|--------|
| **Primary focus** | Robotic additive/hybrid manufacturing | General offline robot programming |
| **Built-in slicer** | Yes - 10+ strategies with full parameter control | No - imports G-code from external slicers |
| **Process awareness** | Deep (material library, process-specific params) | Shallow (generic motion planning) |
| **Post processors** | 12 format presets with event system | 100+ Python-based post processors |
| **Non-planar slicing** | Native (planar along curve, revolved surface, radial, conical, sweep) | Not native |
| **External axes** | Coordinated motion with positioner interpolation | Supported with synchronized motion |
| **Toolpath editing** | Comprehensive (10+ modification types, interpolation bases) | Basic (target editing) |
| **Analytics** | Quality rating bar, cost modelling, graph view | Basic simulation statistics |
| **Monitoring** | OPC UA, direct controller connection, camera | OPC UA add-in, Robot Drivers |
| **Price** | Commercial (subscription) | Commercial (license) with free limited version |
| **Open source** | No | No (API is open) |

---

# IMPLEMENTATION PRIORITIES FOR OPENAXIS

Based on this competitive analysis, the following features should be prioritized:

## Must-Have (Phase 1-2)
1. **Material-aware process settings**: Material dropdown, profiles, deposition height/width
2. **Multiple slicing strategies**: Start with planar horizontal, then planar angled, radial
3. **TCP definition workflow**: Multi-process heads, tool convention dropdown, 6DOF entry
4. **Work frame system**: Multiple work frames, alignment methods, parts-on-frames
5. **Post processor event system**: Program start/end, layer start/end, process on/off
6. **Toolpath color coding**: By segment type, speed, layer number
7. **Quality validation**: Reachability check, singularity detection, joint limit warnings

## Important (Phase 2-3)
8. **Non-planar strategies**: Planar along curve, revolved surface for positioner use
9. **Infill designer**: 9+ patterns with customizable density
10. **Seam control**: Guided, distributed, random with shape options
11. **Engage/disengage moves**: Approach distance, arc, wipe, retract
12. **Movement settings**: Layer time control (wait/adapt speed/fixed wait)
13. **Toolpath editor**: Region-based parameter modification
14. **External axis coordination**: Dynamic positioner interpolation

## Nice-to-Have (Phase 3-4)
15. **Corner compensation**: Triangular/circular geometry modification
16. **Cost modelling**: Material cost, machine cost, labor estimates
17. **Analytics graph view**: Speed, deposition rate, joint angles over path
18. **Conditional IO events**: Variable-based IO triggering
19. **Process modes**: Multiple process settings per toolpath
20. **AdaSync-style plugin**: CAD software bridge (Rhino/Grasshopper)

---

*Research completed: 2026-02-15*
*Sources: AdaOne Resource Center (adaone.adaxis.eu), AdaOne documentation (docx_extracted.txt), RoboDK Documentation (robodk.com/doc), AiBuild (ai-build.com), Meltio (meltio3d.com), CEAD (ceadgroup.com), ORNL Slicer 2 (github.com/ORNLSlicer/Slicer-2), FullControl (fullcontrolgcode.com)*
