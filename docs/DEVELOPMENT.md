# OpenAxis Development Guide

Complete guide for developing OpenAxis, including backend, frontend, and testing.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Project Structure](#project-structure)
- [Backend Development](#backend-development)
- [Frontend Development](#frontend-development)
- [Testing](#testing)
- [Building](#building)
- [Debugging](#debugging)

## Prerequisites

### Required

- **Python 3.11+**: Core backend language
- **Node.js 20+**: Frontend and Electron runtime
- **Git**: Version control
- **Conda** (recommended): Python environment management

### Optional

- **PyBullet**: Physics simulation (auto-installed with package)
- **psutil**: System monitoring for backend API
- **Visual Studio Code**: Recommended IDE

## Setup

### 1. Clone Repository

```bash
git clone https://github.com/openaxis/openaxis.git
cd openaxis
```

### 2. Setup Python Environment

```bash
# Create conda environment
conda create -n openaxis python=3.11
conda activate openaxis

# Install package in editable mode
pip install -e .

# Install development dependencies
pip install pytest pytest-cov pytest-xdist black isort flake8 mypy

# Install pre-commit hooks
pre-commit install
```

### 3. Verify Python Installation

```bash
# Run tests
python -m pytest tests/ -v

# Check coverage
python -m pytest tests/ --cov=src/openaxis --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html # Windows
```

### 4. Setup Frontend

```bash
cd src/ui

# Install dependencies
npm install

# Verify TypeScript compilation
npm run type-check

# Verify linting
npm run lint
```

## Project Structure

```
openaxis/
├── src/
│   ├── openaxis/                # Python backend
│   │   ├── core/               # Core data structures
│   │   ├── slicing/            # Toolpath generation
│   │   ├── motion/             # Motion planning
│   │   ├── simulation/         # Digital twin
│   │   ├── processes/          # Process plugins
│   │   └── hardware/           # Robot drivers (Phase 4)
│   ├── backend/                # HTTP API server
│   │   └── server.py
│   └── ui/                     # Electron/React frontend
│       ├── electron/           # Electron main process
│       └── src/                # React application
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests (Phase 4)
│   └── e2e/                    # End-to-end tests (Phase 4)
├── config/                     # Configuration files
│   ├── robots/                 # Robot URDF/configs
│   └── processes/              # Process parameters
├── docs/                       # Documentation
├── scripts/                    # Utility scripts
└── examples/                   # Example projects
```

## Backend Development

### Running the Backend Server

```bash
# Option 1: Direct execution
python src/backend/server.py

# Option 2: Using script
python scripts/start_backend.py

# Option 3: Custom port/host
python scripts/start_backend.py --host 0.0.0.0 --port 9000
```

Server will be available at `http://localhost:8080`

### API Endpoints

See [src/ui/README.md](../src/ui/README.md) for complete API documentation.

### Adding New Features

#### 1. Create Module

```python
# src/openaxis/mymodule/__init__.py
from .core import MyClass

__all__ = ['MyClass']
```

#### 2. Add Tests

```python
# tests/unit/mymodule/test_core.py
import pytest
from openaxis.mymodule import MyClass

def test_my_class():
    obj = MyClass()
    assert obj.method() == expected_value
```

#### 3. Update API

```python
# src/backend/server.py
def do_POST(self):
    # ...
    elif path == '/api/mymodule/action':
        # Handle new endpoint
        self._send_json({'status': 'success'})
```

### Code Style

```bash
# Format code
black src/ tests/
isort src/ tests/

# Check linting
flake8 src/ tests/

# Type check
mypy src/openaxis

# Run pre-commit checks
pre-commit run --all-files
```

### Python Standards

- **Type Hints**: Use everywhere
- **Docstrings**: Google style
- **Line Length**: 100 characters
- **Imports**: Sorted with isort
- **Formatting**: Black with default settings

Example:

```python
from typing import List, Optional
import numpy as np

def process_toolpath(
    points: List[np.ndarray],
    speed: float = 10.0,
    layer_height: Optional[float] = None
) -> Toolpath:
    """Process toolpath from points.

    Args:
        points: List of 3D points as numpy arrays
        speed: Travel speed in mm/s
        layer_height: Layer height in mm, auto-detected if None

    Returns:
        Processed toolpath object

    Raises:
        ValueError: If points list is empty
    """
    if not points:
        raise ValueError("Points list cannot be empty")

    # Implementation...
    return toolpath
```

## Frontend Development

### Running Development Server

```bash
cd src/ui

# Start both React and Electron
npm run dev

# Or separately:
npm run dev:react    # Vite on http://localhost:5173
npm run dev:electron # Electron window
```

### Project Structure

```
src/ui/src/
├── pages/           # Page components (Dashboard, Projects, etc.)
├── components/      # Reusable components
├── stores/          # Zustand state management
├── types/           # TypeScript definitions
├── utils/           # Utilities (IPC, helpers)
├── App.tsx          # Application routing
└── main.tsx         # React entry point
```

### Adding New Pages

#### 1. Create Page Component

```tsx
// src/ui/src/pages/MyPage.tsx
export default function MyPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">My Page</h1>
      {/* Content */}
    </div>
  );
}
```

#### 2. Add Route

```tsx
// src/ui/src/App.tsx
import MyPage from './pages/MyPage';

// In Routes:
<Route path="/mypage" element={<MyPage />} />
```

#### 3. Add Navigation

```tsx
// src/ui/src/components/Layout.tsx
const navigation = [
  // ...
  { name: 'My Page', path: '/mypage', icon: MyIcon },
];
```

### State Management

Create Zustand store:

```typescript
// src/ui/src/stores/myStore.ts
import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

interface MyState {
  items: Item[];
  addItem: (item: Item) => void;
}

export const useMyStore = create<MyState>()(
  immer((set) => ({
    items: [],
    addItem: (item) => set((state) => {
      state.items.push(item);
    }),
  }))
);
```

Use in component:

```typescript
import { useMyStore } from '../stores/myStore';

function MyComponent() {
  const items = useMyStore((state) => state.items);
  const addItem = useMyStore((state) => state.addItem);

  return (
    <button onClick={() => addItem(newItem)}>
      Add Item
    </button>
  );
}
```

### Frontend Standards

- **TypeScript**: Strict mode enabled
- **Components**: Functional components with hooks
- **Styling**: Tailwind CSS utility classes
- **State**: Zustand with Immer for complex state
- **Icons**: Heroicons (outline for UI, solid for emphasis)

### 3D Visualization

Using React Three Fiber:

```tsx
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';

function MyScene() {
  return (
    <Canvas>
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} />

      <mesh>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color="blue" />
      </mesh>

      <OrbitControls />
    </Canvas>
  );
}
```

## Testing

### Python Tests

```bash
# Run all tests
pytest tests/

# With verbose output
pytest tests/ -v

# Specific module
pytest tests/unit/slicing/

# With coverage
pytest tests/ --cov=src/openaxis --cov-report=html

# Parallel execution
pytest tests/ -n auto

# Stop on first failure
pytest tests/ -x
```

### Test Structure

```python
# tests/unit/mymodule/test_feature.py
import pytest
from openaxis.mymodule import MyClass

@pytest.fixture
def my_fixture():
    """Setup test fixture"""
    return MyClass()

def test_basic_functionality(my_fixture):
    """Test basic functionality"""
    result = my_fixture.method()
    assert result == expected

def test_edge_case():
    """Test edge case"""
    with pytest.raises(ValueError):
        MyClass().invalid_operation()

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiple_cases(input, expected):
    """Test multiple input cases"""
    assert MyClass().double(input) == expected
```

### Frontend Tests (Future)

```bash
# Unit tests
npm test

# E2E tests
npm run test:e2e

# With coverage
npm run test:coverage
```

## Building

### Python Package

```bash
# Build wheel
python -m build

# Install locally
pip install dist/openaxis-*.whl

# Verify
python -c "import openaxis; print(openaxis.__version__)"
```

### Electron Application

```bash
cd src/ui

# Build React app
npm run build

# Package Electron app
npm run build:electron

# Output: dist-electron/
```

Build artifacts:
- **Windows**: `.exe` installer, portable `.exe`
- **Linux**: `.AppImage`, `.deb`
- **macOS**: `.dmg`, `.zip`

## Debugging

### Backend Debugging

#### VS Code Launch Configuration

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Backend Server",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/src/backend/server.py",
      "console": "integratedTerminal"
    },
    {
      "name": "Python: Current Test",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v"]
    }
  ]
}
```

#### Logging

```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### Frontend Debugging

#### Chrome DevTools

- Press `F12` or `Ctrl+Shift+I`
- Sources tab: Set breakpoints in TypeScript
- Console: View logs and errors
- Network: Inspect API calls
- React DevTools: Inspect component state

#### VS Code Launch Configuration

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Electron: Main",
      "type": "node",
      "request": "launch",
      "cwd": "${workspaceFolder}/src/ui",
      "runtimeExecutable": "${workspaceFolder}/src/ui/node_modules/.bin/electron",
      "args": ["."],
      "outputCapture": "std"
    }
  ]
}
```

#### Console Logging

```typescript
console.log('Debug info:', data);
console.warn('Warning:', warning);
console.error('Error:', error);

// With trace
console.trace('Trace point');
```

### Common Issues

#### Port Already in Use

```bash
# Find process using port 8080
lsof -i :8080           # macOS/Linux
netstat -ano | findstr :8080  # Windows

# Kill process
kill -9 <PID>           # macOS/Linux
taskkill /PID <PID> /F  # Windows
```

#### Import Errors

```bash
# Reinstall package
pip uninstall openaxis
pip install -e .

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

#### Node Module Issues

```bash
# Clear and reinstall
cd src/ui
rm -rf node_modules package-lock.json
npm install

# Clear cache
npm cache clean --force
```

## Performance Profiling

### Python Profiling

```bash
# Profile script
python -m cProfile -o output.prof script.py

# View results
python -m pstats output.prof
# In pstats shell: sort time, stats 20
```

### Frontend Profiling

Use React DevTools Profiler:
1. Open React DevTools
2. Go to Profiler tab
3. Click record
4. Perform actions
5. Stop recording
6. Analyze flame graph

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/my-feature
```

### Commit Message Convention

```
feat: add new feature
fix: fix bug
docs: update documentation
style: format code
refactor: refactor code
test: add tests
chore: update dependencies
```

## Resources

- [COMPAS Documentation](https://compas.dev/compas/latest/)
- [React Three Fiber](https://docs.pmnd.rs/react-three-fiber)
- [Electron Documentation](https://www.electronjs.org/docs/latest/)
- [Zustand Documentation](https://docs.pmnd.rs/zustand)
- [Tailwind CSS](https://tailwindcss.com/docs)

## Getting Help

- GitHub Issues: Report bugs
- GitHub Discussions: Ask questions
- Documentation: Read docs/
- Examples: Check examples/
