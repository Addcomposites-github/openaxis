# OpenAxis Testing Guide

Complete guide to testing the OpenAxis platform, including automated tests, quality checks, and validation workflows.

## Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Quality Test Suite](#quality-test-suite)
- [Writing Tests](#writing-tests)
- [Test Coverage](#test-coverage)
- [Continuous Integration](#continuous-integration)
- [Troubleshooting](#troubleshooting)

---

## Overview

OpenAxis uses a comprehensive testing strategy that includes:

- **Unit Tests**: Fast, isolated tests for individual modules
- **Integration Tests**: Tests for component interactions
- **End-to-End Tests**: Complete workflow validation
- **Quality Suite**: Comprehensive system-wide tests
- **Code Quality Checks**: Linting, type checking, formatting

### Test Philosophy

1. **Fast Feedback**: Unit tests run in seconds
2. **Comprehensive Coverage**: Aim for >80% code coverage
3. **Real-World Scenarios**: Integration tests mirror actual usage
4. **Automated Quality**: All tests run on every commit
5. **Clear Documentation**: Every test has a clear purpose

---

## Test Structure

```
tests/
├── unit/                          # Unit tests (fast, isolated)
│   ├── core/
│   │   ├── test_config.py        # Configuration management
│   │   ├── test_project.py       # Project CRUD operations
│   │   ├── test_robot.py         # Robot loading and kinematics
│   │   └── test_geometry.py      # Geometry processing
│   └── slicing/
│       ├── test_toolpath.py      # Toolpath data structures
│       ├── test_gcode.py         # G-code generation
│       └── test_planar_slicer.py # Planar slicing algorithm
│
├── integration/                   # Integration tests (moderate speed)
│   ├── test_simulation.py        # PyBullet simulation integration
│   ├── test_motion_planning.py   # Motion planning workflows
│   └── test_process_plugins.py   # Process plugin integration
│
├── e2e/                          # End-to-end tests (slower)
│   ├── test_waam_workflow.py     # Complete WAAM workflow
│   ├── test_pellet_workflow.py   # Complete pellet workflow
│   └── test_hybrid_workflow.py   # Multi-process workflows
│
├── hardware/                      # Hardware tests (manual only)
│   └── test_robot_comm.py        # Real robot communication
│
└── test_quality_suite.py         # Comprehensive quality tests
```

---

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/core/test_project.py

# Run with verbose output
pytest -v

# Run and show print statements
pytest -s
```

### Using the Quality Test Runner

The automated test runner provides comprehensive testing with reporting:

```bash
# Run all tests with summary
python scripts/run_quality_tests.py

# Generate HTML report
python scripts/run_quality_tests.py --html

# Run with code coverage
python scripts/run_quality_tests.py --coverage

# Include code quality checks
python scripts/run_quality_tests.py --quality

# Run everything
python scripts/run_quality_tests.py --all
```

### Test Categories

Run tests by category using markers:

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests
pytest -m integration

# End-to-end tests
pytest -m e2e

# Simulation tests
pytest -m simulation

# Slicing tests
pytest -m slicing

# Exclude slow tests
pytest -m "not slow"
```

### Running Specific Workflows

```bash
# Test WAAM workflow
pytest -m waam

# Test pellet extrusion workflow
pytest -m pellet

# Test milling workflow
pytest -m milling

# Test motion planning
pytest -m motion
```

---

## Quality Test Suite

The quality test suite (`tests/test_quality_suite.py`) provides comprehensive system validation.

### Test Workflows

#### Workflow 1: Geometry Loading
- Load STL files
- Compute bounding boxes
- Validate mesh properties

#### Workflow 2: Project Management
- Create projects
- Add parts to projects
- Save and reload projects

#### Workflow 3: Slicing & Toolpath
- Planar slicing
- Toolpath generation
- G-code generation for multiple formats

#### Workflow 4: Process Plugins
- WAAM process configuration
- Pellet extrusion parameters
- Milling process setup

#### Workflow 5: Configuration Management
- Load robot configurations
- Load process configurations
- Validate configuration files

#### Workflow 6: Simulation
- Create simulation environment
- Load objects into PyBullet
- Run physics simulation

#### Workflow 7: Motion Planning (Optional)
- Inverse kinematics
- Cartesian path planning
- Collision detection

#### Workflow 8: End-to-End
- Complete workflow from STL to G-code
- Project creation → Geometry → Slice → G-code
- File output validation

### Running the Quality Suite

```bash
# Run quality suite
pytest tests/test_quality_suite.py -v

# Generate detailed report
pytest tests/test_quality_suite.py -v --tb=long

# Run with HTML report
pytest tests/test_quality_suite.py --html=report.html --self-contained-html
```

---

## Writing Tests

### Test Structure

```python
import pytest
from openaxis.core.project import Project

class TestProjectManagement:
    """Test suite for project management"""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create temporary project for testing"""
        project = Project.create("Test", str(tmp_path))
        yield project
        # Cleanup happens automatically

    def test_create_project(self, temp_project):
        """Test project creation"""
        assert temp_project is not None
        assert temp_project.name == "Test"
        assert len(temp_project.parts) == 0
```

### Using Markers

```python
import pytest

@pytest.mark.unit
def test_fast_function():
    """Fast unit test"""
    assert 1 + 1 == 2

@pytest.mark.integration
@pytest.mark.slow
def test_complex_integration():
    """Slower integration test"""
    # Complex test logic
    pass

@pytest.mark.skipif(not HARDWARE_AVAILABLE, reason="Hardware not available")
def test_with_robot():
    """Test requiring physical hardware"""
    pass
```

### Test Fixtures

Common fixtures are available in `conftest.py`:

```python
def test_with_sample_geometry(sample_stl):
    """Test using sample STL fixture"""
    loader = GeometryLoader()
    mesh = loader.load(sample_stl)
    assert mesh is not None

def test_with_temp_workspace(temp_workspace):
    """Test using temporary workspace"""
    output_file = temp_workspace / "output.gcode"
    output_file.write_text("G0 X0 Y0")
    assert output_file.exists()
```

### Assertions Best Practices

```python
# Good: Descriptive assertions
assert len(toolpath.segments) > 0, "Toolpath should contain segments"
assert result.success, f"Operation failed: {result.error}"

# Good: Approximate comparisons for floats
assert distance == pytest.approx(10.0, abs=0.01)

# Good: Check types
assert isinstance(config, RobotConfig)

# Good: Check exceptions
with pytest.raises(ValueError, match="Invalid parameter"):
    process.validate_parameters()
```

---

## Test Coverage

### Viewing Coverage

```bash
# Run tests with coverage
pytest --cov=openaxis --cov-report=html

# Open HTML report
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

### Coverage Goals

| Module | Target Coverage |
|--------|----------------|
| Core (config, project, robot) | >90% |
| Slicing | >85% |
| Motion Planning | >80% |
| Process Plugins | >85% |
| Simulation | >75% |
| Hardware (when available) | >70% |

### Improving Coverage

1. **Identify gaps**: Check coverage report for uncovered lines
2. **Add tests**: Write tests for uncovered code paths
3. **Test edge cases**: Boundary conditions, errors, exceptions
4. **Integration tests**: Cover interactions between modules

---

## Code Quality Checks

### Linting with flake8

```bash
# Check all code
flake8 src/openaxis

# Check specific file
flake8 src/openaxis/core/project.py

# Auto-fix some issues
autopep8 --in-place --aggressive src/openaxis
```

### Type Checking with mypy

```bash
# Type check all code
mypy src/openaxis

# Type check specific module
mypy src/openaxis/core

# Generate HTML report
mypy src/openaxis --html-report mypy-report
```

### Code Formatting with black

```bash
# Check formatting
black --check src/openaxis

# Auto-format code
black src/openaxis

# Format specific file
black src/openaxis/core/project.py
```

### Running All Quality Checks

```bash
# Use the test runner
python scripts/run_quality_tests.py --quality

# Or run individually
flake8 src/openaxis && mypy src/openaxis && black --check src/openaxis
```

---

## Continuous Integration

### Pre-commit Hooks

Install pre-commit hooks to run tests automatically:

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### CI Pipeline

The CI pipeline (GitHub Actions) runs:

1. **Linting**: flake8, black
2. **Type Checking**: mypy
3. **Unit Tests**: Fast tests with coverage
4. **Integration Tests**: Component integration
5. **Quality Suite**: Comprehensive validation
6. **Build**: Package creation and validation

### Local CI Simulation

```bash
# Simulate CI pipeline locally
python scripts/run_quality_tests.py --all
```

---

## Test Data

### Sample Files

Test files are located in `tests/fixtures/`:

- `cube.stl` - Simple 10mm cube
- `complex_part.stl` - Complex geometry for stress testing
- `robot_config.yaml` - Sample robot configuration
- `process_config.yaml` - Sample process parameters

### Creating Test Data

```python
@pytest.fixture
def sample_toolpath():
    """Create sample toolpath for testing"""
    toolpath = Toolpath()
    toolpath.add_segment(ToolpathSegment(
        start_point=[0, 0, 0],
        end_point=[10, 0, 0],
        move_type=MoveType.LINEAR,
        speed=100.0
    ))
    return toolpath
```

---

## Performance Testing

### Measuring Test Duration

```bash
# Show slowest 10 tests
pytest --durations=10

# Show all test durations
pytest --durations=0
```

### Profiling Tests

```bash
# Profile test execution
pytest --profile

# Generate profiling report
pytest --profile-svg
```

### Performance Benchmarks

Key performance targets:

| Operation | Target Time |
|-----------|-------------|
| Load STL (1MB) | <100ms |
| Slice mesh (10k faces) | <1s |
| Generate G-code (1000 lines) | <200ms |
| IK solve (6-DOF) | <50ms |
| Collision check | <10ms |

---

## Troubleshooting

### Common Issues

#### Import Errors

```bash
# Ensure package is installed in editable mode
pip install -e .

# Or add src to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"  # Linux/macOS
set PYTHONPATH=%PYTHONPATH%;%CD%\src          # Windows
```

#### PyBullet GUI Issues

```python
# Use DIRECT mode for headless testing
sim = SimulationEnvironment(gui=False)
```

#### Missing Dependencies

```bash
# Install test dependencies
pip install -e ".[dev]"

# Or install individually
pip install pytest pytest-cov pytest-html pytest-timeout
```

#### Permission Errors

```bash
# Ensure test directories are writable
chmod -R 755 tests/  # Linux/macOS
```

### Debug Failed Tests

```bash
# Run with debugger on failure
pytest --pdb

# Show local variables on failure
pytest -l

# Verbose output with full traceback
pytest -vv --tb=long

# Stop on first failure
pytest -x
```

### Test Isolation Issues

```bash
# Run tests in random order to detect dependencies
pytest --random-order

# Run specific test in isolation
pytest tests/unit/core/test_project.py::TestProjectManagement::test_create_project
```

---

## Test Reports

### Generated Reports

After running tests, reports are saved to `test_reports/`:

- `test_summary_TIMESTAMP.txt` - Text summary
- `unit_tests_TIMESTAMP.json` - JSON results for unit tests
- `integration_tests_TIMESTAMP.json` - JSON results for integration tests
- `quality_suite_TIMESTAMP.json` - JSON results for quality suite
- `test_report_TIMESTAMP.html` - HTML report (if --html used)

### Reading Reports

#### Text Summary

```
============================================================
OpenAxis Quality Test Summary
============================================================
Timestamp: 2024-01-15 10:30:45

Overall Results:
  Total Test Suites: 4
  Passed: 4
  Failed: 0
  Total Duration: 12.34s

Test Suite Results:
✓ PASS     Unit Tests                    (5.23s)
✓ PASS     Integration Tests             (3.45s)
✓ PASS     Quality Suite                 (2.89s)
✓ PASS     Code Quality                  (0.77s)
============================================================
🎉 ALL TESTS PASSED!
============================================================
```

#### HTML Report

Open `test_reports/test_report_TIMESTAMP.html` in a browser for:
- Interactive test results
- Failure details with stack traces
- Test duration charts
- Coverage visualization

---

## Best Practices

### Do's ✓

- Write tests before fixing bugs (TDD)
- Use descriptive test names
- Test one thing per test
- Use fixtures for setup/teardown
- Mock external dependencies
- Keep tests fast and focused
- Add markers for test organization
- Update tests when changing code

### Don'ts ✗

- Don't write tests that depend on each other
- Don't use hardcoded file paths
- Don't skip tests without good reason
- Don't test implementation details
- Don't use time.sleep() in tests
- Don't ignore test failures
- Don't commit commented-out tests

---

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [OpenAxis Architecture Docs](architecture/README.md)
- [Contributing Guide](../CONTRIBUTING.md)

---

## Getting Help

If you encounter issues with testing:

1. Check this guide for common issues
2. Review existing tests for examples
3. Ask in team chat or open an issue
4. Consult pytest documentation

Happy Testing! 🧪
