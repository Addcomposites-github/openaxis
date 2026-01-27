# OpenAxis Desktop Application

Modern desktop application for robotic hybrid manufacturing, built with Electron, React, and Three.js.

## Features

- **Project Management**: Create, edit, and manage manufacturing projects
- **Geometry Editor**: Import and visualize 3D models (STL, OBJ, STEP)
- **Toolpath Editor**: Generate and customize toolpaths with live preview
- **Simulation**: Visualize robot motion and detect collisions
- **Monitoring**: Real-time sensor data, system status, and alerts
- **Settings**: Configure robot, processes, and application preferences

## Tech Stack

- **Electron 28** - Desktop application framework
- **React 18** - UI framework
- **TypeScript 5** - Type-safe development
- **Three.js** - 3D visualization
- **Tailwind CSS** - Modern styling
- **Zustand** - State management
- **Recharts** - Data visualization

## Prerequisites

- Node.js 20+ and npm
- Python 3.11+ with OpenAxis installed
- Windows 11, Ubuntu 22.04+, or macOS 13+

## Installation

```bash
# Navigate to UI directory
cd src/ui

# Install dependencies
npm install
```

## Development

### Start in Development Mode

```bash
# Start Vite dev server and Electron
npm run dev

# Or start separately:
npm run dev:react    # Vite dev server on http://localhost:5173
npm run dev:electron # Electron window (waits for Vite)
```

The application will:
1. Start the Python backend server on `http://localhost:8080`
2. Launch Vite dev server on `http://localhost:5173`
3. Open Electron window with hot-reload enabled
4. Open DevTools automatically

### Backend Server

The Python backend server starts automatically when you launch the Electron app. To run it manually:

```bash
# From project root
python src/backend/server.py
```

Server runs on: `http://localhost:8080`

### Type Checking

```bash
npm run type-check
```

### Linting

```bash
npm run lint
```

### Formatting

```bash
npm run format
```

## Building for Production

### Build React App

```bash
npm run build
```

Output: `dist/` directory with optimized React build

### Package Electron App

```bash
npm run build:electron
```

Output: `dist-electron/` directory with installers:
- **Windows**: `OpenAxis-Setup-0.1.0.exe` (NSIS installer), `OpenAxis-0.1.0-win.exe` (portable)
- **Linux**: `OpenAxis-0.1.0.AppImage`, `OpenAxis-0.1.0.deb`
- **macOS**: `OpenAxis-0.1.0.dmg`, `OpenAxis-0.1.0-mac.zip`

## Project Structure

```
src/ui/
├── electron/              # Electron main process
│   ├── main.js           # Application entry, Python backend management
│   └── preload.js        # IPC bridge
├── src/                  # React application
│   ├── pages/           # Page components
│   │   ├── Dashboard.tsx
│   │   ├── ProjectManager.tsx
│   │   ├── GeometryEditor.tsx
│   │   ├── ToolpathEditor.tsx
│   │   ├── Simulation.tsx
│   │   ├── Monitoring.tsx
│   │   └── Settings.tsx
│   ├── components/      # Reusable components
│   │   └── Layout.tsx
│   ├── stores/          # Zustand state management
│   │   ├── projectStore.ts
│   │   ├── robotStore.ts
│   │   └── simulationStore.ts
│   ├── types/           # TypeScript definitions
│   │   └── index.ts
│   ├── utils/           # Utilities
│   │   └── ipc.ts       # Backend communication
│   ├── App.tsx          # Application routing
│   ├── main.tsx         # React entry point
│   └── index.css        # Global styles
├── public/              # Static assets
├── package.json         # Dependencies
├── tsconfig.json        # TypeScript config
├── vite.config.ts       # Vite config
└── tailwind.config.js   # Tailwind config
```

## Keyboard Shortcuts

### File
- `Ctrl/Cmd + N` - New Project
- `Ctrl/Cmd + O` - Open Project
- `Ctrl/Cmd + S` - Save Project
- `Ctrl/Cmd + I` - Import Geometry
- `Ctrl/Cmd + E` - Export G-code

### Process
- `Ctrl/Cmd + G` - Generate Toolpath
- `Ctrl/Cmd + Shift + S` - Simulate

### View
- `F5` - Reload
- `Ctrl/Cmd + Shift + I` - Toggle DevTools
- `F11` - Toggle Fullscreen

## API Endpoints

The Python backend provides a REST API:

### Projects
- `GET /api/projects` - List all projects
- `GET /api/projects/:id` - Get project
- `POST /api/projects` - Create project
- `PUT /api/projects/:id` - Update project
- `DELETE /api/projects/:id` - Delete project

### Geometry
- `POST /api/geometry/import` - Import geometry file
- `POST /api/geometry/export` - Export geometry
- `POST /api/geometry/analyze` - Analyze geometry

### Toolpath
- `POST /api/toolpath/generate` - Generate toolpath
- `POST /api/toolpath/optimize` - Optimize toolpath
- `POST /api/toolpath/export` - Export G-code

### Robot
- `GET /api/robot/state` - Get robot state
- `POST /api/robot/connect` - Connect to robot
- `POST /api/robot/disconnect` - Disconnect
- `POST /api/robot/home` - Home robot
- `POST /api/robot/enable` - Enable motors
- `POST /api/robot/disable` - Disable motors
- `POST /api/robot/move_to` - Move to position

### Simulation
- `POST /api/simulation/start` - Start simulation
- `POST /api/simulation/step` - Step simulation
- `GET /api/simulation/check_collisions` - Check collisions
- `GET /api/simulation/get_state` - Get simulation state

### Monitoring
- `GET /api/monitoring/sensors` - Get sensor data
- `GET /api/monitoring/system` - Get system status
- `GET /api/monitoring/alerts` - Get alerts

## Troubleshooting

### Application won't start
- Check Node.js version: `node --version` (should be 20+)
- Reinstall dependencies: `rm -rf node_modules package-lock.json && npm install`
- Check Python backend: `python src/backend/server.py`

### 3D view not rendering
- Check GPU acceleration is enabled in Electron
- Update graphics drivers
- Check browser console for WebGL errors

### Backend connection errors
- Verify Python backend is running on `http://localhost:8080`
- Check firewall isn't blocking port 8080
- Review backend logs for errors

### Hot reload not working
- Check Vite dev server is running on port 5173
- Clear browser cache
- Restart dev servers

## Contributing

See `CONTRIBUTING.md` in project root.

## License

Apache License 2.0 - See `LICENSE` in project root.

## Documentation

- [Architecture Overview](../../docs/architecture.md)
- [API Documentation](../../docs/api.md)
- [Phase 3 Completion](../../docs/PHASE3_COMPLETE.md)
- [Roadmap](../../docs/ROADMAP.md)
