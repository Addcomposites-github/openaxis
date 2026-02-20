# Quickstart: STL to G-code

This tutorial walks through the complete workflow: importing a 3D model, configuring slicing parameters, generating toolpath, simulating, and exporting G-code.

## 1. Start the Application

```bash
# Terminal 1: Start the backend
python src/backend/server.py

# Terminal 2: Start the frontend
cd src/ui && npm run dev
```

Open `http://localhost:5173` in your browser.

## 2. Configure the Robot Cell (Setup Tab)

1. The app opens on the **Setup** tab with a 3D viewport.
2. **Robot Model**: ABB IRB 6700 is loaded by default.
3. **End Effector**: Select your process tool (WAAM torch, pellet extruder, or spindle).
4. **Process Type**: Choose your manufacturing process (WAAM, Pellet Extrusion, or Milling).
5. **Work Table**: Adjust position and size to match your physical setup.

## 3. Import Geometry (Geometry Tab)

1. Switch to the **Geometry** tab.
2. Click **Import STL** or drag-and-drop an STL file.
3. The part appears on the work table in the 3D viewport.
4. Use the transform tools to position, rotate, and scale the part.
5. Optionally use **Place on Plate** to snap the part to the table surface.

Supported formats: STL, OBJ.

## 4. Generate Toolpath (Toolpath Tab)

1. Switch to the **Toolpath** tab.
2. Select a **Material** from the material library (this auto-fills slicing parameters).
3. Adjust slicing parameters as needed:
   - **Layer Height**: Height per layer (mm)
   - **Extrusion Width**: Bead width (mm)
   - **Wall Count**: Number of perimeter walls
   - **Infill Density**: Interior fill percentage
   - **Infill Pattern**: Grid, triangles, hexagonal, etc.
4. Click **Generate Toolpath**.
5. The toolpath visualization appears in the viewport.
6. Use the layer slider to inspect individual layers.

## 5. Simulate (Simulation Tab)

1. Switch to the **Simulation** tab.
2. The system computes inverse kinematics (IK) for the toolpath automatically.
3. A progress indicator shows IK computation status.
4. Once ready, use the playback controls:
   - **Play/Pause**: Start or pause the simulation
   - **Speed**: Adjust playback speed (0.25x to 4x)
   - **Timeline**: Scrub through the simulation
5. Collision warnings appear if the robot encounters issues.

## 6. Export G-code (Post-Processor)

1. In the **Toolpath** tab, expand the **Post-Processor** panel.
2. Select your export format:
   - **G-code** (.gcode) for standard CNC/3D printers
   - **ABB RAPID** (.mod) for ABB robots
   - **KUKA KRL** (.src) for KUKA robots
   - **Fanuc LS** (.ls) for Fanuc robots
3. Configure motion parameters (speed, zone data, blending).
4. Optionally add event hooks (program start/end, layer start/end).
5. Click **Export** to download the program file.

## Next Steps

- Configure custom materials in the Material Library
- Set up ORNL Slicer 2 for production slicing: [ORNL Slicer Setup](ornl-slicer-setup.md)
- Review the [API Documentation](../api/) for programmatic access
