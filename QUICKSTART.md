# OpenAxis Quick Start Guide

## First Time Setup

### Prerequisites
- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Git** (already installed)

### Initial Setup

**Double-click:** `setup.bat`

This will:
- Create Python virtual environment
- Install Python dependencies (FastAPI, uvicorn)
- Install Node.js dependencies (React, Three.js, etc.)
- Copy robot config files to UI public directory

**Time:** ~2-3 minutes

---

## Starting OpenAxis

### Option 1: Full Stack (Recommended)

**Double-click:** `start.bat`

This will:
- Start Python backend on port 8000
- Start UI dev server on port 5173
- Automatically open browser to http://localhost:5173

You'll see two command windows:
- **OpenAxis Backend** - Python server logs
- **OpenAxis UI** - Vite dev server logs

### Option 2: UI Only (Current Setup)

**Double-click:** `start-ui-only.bat`

Use this if:
- Backend isn't ready yet
- You only want to work on UI/visualization
- Robot visualization and geometry work without backend

---

## Stopping OpenAxis

**Double-click:** `stop.bat`

This will:
- Close all OpenAxis windows
- Kill processes on ports 5173 and 8000
- Clean shutdown

Or simply close the command windows manually.

---

## Using OpenAxis

### 1. First Time: Robot Cell Setup

1. Navigate to **Robot Setup** in the sidebar
2. Configure your manufacturing cell:
   - **Robot Tab:** Position robot base
   - **End Effector Tab:** Select WAAM Torch / Pellet / Spindle
   - **External Axes Tab:** Add turntable or positioner (optional)
   - **Work Table Tab:** Set table size and position
3. Click **"Save Cell Setup & Continue"**

### 2. Import Geometry

1. Navigate to **Geometry**
2. Click **"Import Geometry"**
3. Select an STL file
4. Part will auto-place on the work table you configured
5. Adjust position if needed (stays on table surface)

### 3. Generate Toolpath

1. Navigate to **Toolpath**
2. Select slicing parameters
3. Click **"Generate Toolpath"**
4. Preview layers and adjust

### 4. Simulate

1. Navigate to **Simulation**
2. View robot and toolpath together
3. Click **Play** to animate (when IK is implemented)

---

## Troubleshooting

### Port Already in Use

If you see "port already in use" errors:

1. Run `stop.bat` to kill existing processes
2. Or manually kill processes:
   ```batch
   netstat -ano | findstr :5173
   taskkill /F /PID <PID>
   ```

### Dependencies Not Installed

If you see "module not found" errors:

1. Make sure you ran `setup.bat` first
2. For Python issues:
   ```batch
   cd src\backend
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. For Node.js issues:
   ```batch
   cd src\ui
   npm install
   ```

### Robot Not Visible

1. Open browser console (F12)
2. Check for loading errors
3. Verify files exist:
   - `src/ui/public/config/urdf/abb_irb6700.urdf`
   - `src/ui/public/config/meshes/`
4. Clear browser cache and reload

### Geometry Not Placing Correctly

1. Ensure you configured Robot Setup first
2. Check work table position is within robot reach (0.5-2.5m)
3. Try re-importing the geometry

---

## Development Workflow

### UI Only Development (Fastest)

```batch
start-ui-only.bat
```

Hot reload is enabled - changes appear instantly.

### Full Stack Development

```batch
start.bat
```

Both backend and frontend with hot reload.

### Stop All Services

```batch
stop.bat
```

Or press Ctrl+C in each window.

---

## File Structure

```
openaxis/
├── start.bat              ← Start full stack
├── start-ui-only.bat      ← Start UI only (recommended for now)
├── stop.bat               ← Stop all services
├── setup.bat              ← First time setup
├── src/
│   ├── backend/           ← Python FastAPI server
│   │   ├── server.py
│   │   └── venv/          ← Virtual environment (created by setup)
│   └── ui/                ← React + Three.js frontend
│       ├── src/
│       │   ├── pages/
│       │   │   ├── RobotSetup.tsx    ← NEW: Robot cell config
│       │   │   ├── GeometryEditor.tsx
│       │   │   ├── ToolpathEditor.tsx
│       │   │   └── Simulation.tsx
│       │   └── components/
│       │       └── RobotModel.tsx     ← URDF loader
│       └── public/
│           └── config/    ← Robot URDF & meshes
└── config/                ← Original robot configs
    ├── urdf/
    ├── meshes/
    └── robots/
```

---

## What's Working Now

✅ Robot cell setup interface
✅ Robot visualization (ABB IRB 6700)
✅ Geometry import & placement
✅ Geometry correctly sits on work table
✅ End effector configuration
✅ External axes visualization
✅ Toolpath generation
✅ Toolpath visualization

## What's Next

🔄 Link toolpath to geometry (moves together)
🚧 Inverse kinematics calculation
🚧 Reachability visualization
🚧 Robot motion simulation
🚧 Collision detection
🚧 ABB RAPID code export

---

## URLs

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs (when backend is running)

---

## Getting Help

- Check `CORRECTED_WORKFLOW.md` for detailed workflow explanation
- Check `ROBOT_INTEGRATION_STATUS.md` for technical robot details
- Check browser console (F12) for errors
- Check terminal output for backend errors

---

**Last Updated:** 2026-01-27
**Version:** 0.1.0 - Phase 1 Complete
