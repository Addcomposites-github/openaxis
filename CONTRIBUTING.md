# Contributing to OpenAxis

Thank you for your interest in contributing to OpenAxis! This document provides guidelines and information for contributors.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please be respectful and constructive in all interactions.

## Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/openaxis.git
cd openaxis
git remote add upstream https://github.com/openaxis/openaxis.git
```

### 2. Set Up Development Environment

```bash
./scripts/setup_dev.sh
conda activate openaxis
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

## Development Workflow

### Making Changes

1. **Write tests first** (TDD approach encouraged)
2. **Implement your changes**
3. **Ensure all tests pass**
4. **Update documentation if needed**

### Code Standards

#### Python Code Style

- **Formatter**: Black (line length 100)
- **Import sorting**: isort
- **Linting**: flake8
- **Type checking**: mypy

```bash
# Format code
black src/ tests/
isort src/ tests/

# Check linting
flake8 src/ tests/

# Type check
mypy src/
```

#### Type Hints

All functions must have type hints:

```python
def process_toolpath(
    geometry: Mesh,
    parameters: ProcessConfig,
    validate: bool = True,
) -> Toolpath:
    """
    Process geometry into a toolpath.

    Args:
        geometry: Input mesh geometry
        parameters: Process configuration
        validate: Whether to validate output

    Returns:
        Generated toolpath
    """
    ...
```

#### Docstrings

Use Google-style docstrings for all public functions and classes:

```python
class Robot:
    """
    Represents a robot with kinematics and configuration.

    This class handles robot model loading, forward/inverse kinematics,
    and configuration management.

    Attributes:
        name: Robot name
        joints: List of joint definitions
        tool: Current tool configuration

    Example:
        >>> robot = Robot.from_urdf("path/to/robot.urdf")
        >>> fk = robot.forward_kinematics([0, 0, 0, 0, 0, 0])
    """
```

### Testing

#### Running Tests

```bash
# All unit tests
pytest tests/unit -v

# With coverage
pytest tests/unit --cov=src/openaxis --cov-report=term-missing

# Specific test
pytest tests/unit/core/test_config.py::TestConfigManager::test_load_robots -v
```

#### Test Structure

```
tests/
├── unit/           # Pure unit tests (no external deps)
│   └── core/
│       ├── test_config.py
│       └── test_project.py
├── integration/    # Tests with simulation
└── e2e/           # End-to-end tests
```

#### Writing Tests

```python
class TestMyFeature:
    """Tests for MyFeature."""

    def test_basic_functionality(self, sample_fixture):
        """Test the basic case."""
        result = my_feature(sample_fixture)
        assert result.status == "success"

    def test_edge_case(self):
        """Test edge case with empty input."""
        with pytest.raises(ValueError):
            my_feature(None)

    @pytest.mark.slow
    def test_performance(self, large_dataset):
        """Test performance with large dataset."""
        ...
```

## Submitting Changes

### Commit Messages

Use clear, descriptive commit messages:

```
feat: Add pellet extrusion process plugin

- Implement PelletProcess class
- Add configuration schema
- Add unit tests

Closes #123
```

Prefixes:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `test:` Adding tests
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

### Pull Requests

1. **Update your branch**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push your changes**
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create Pull Request**
   - Use a clear title
   - Describe what changes you made
   - Reference any related issues
   - Include screenshots for UI changes

### PR Checklist

- [ ] Tests pass locally
- [ ] Code is formatted (black, isort)
- [ ] No linting errors
- [ ] Type hints added
- [ ] Documentation updated
- [ ] Changelog updated (if significant)

## Architecture Guidelines

### Module Organization

- Keep modules focused and single-purpose
- Use the plugin system for new processes
- Follow existing patterns in the codebase

### Dependencies

- Use COMPAS for geometry operations
- Use pydantic for configuration models
- Avoid adding new dependencies without discussion

### Error Handling

```python
# Good
from openaxis.core.exceptions import ConfigurationError

def load_config(path: Path) -> Config:
    if not path.exists():
        raise ConfigurationError(
            f"Config file not found: {path}",
            details={"path": str(path)}
        )
    ...

# Avoid
def load_config(path: Path) -> Config:
    try:
        ...
    except:  # Too broad
        pass
```

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue
- **Features**: Open a GitHub Issue with `[Feature]` prefix

## Recognition

Contributors will be recognized in:
- The project README
- Release notes
- The contributors page

Thank you for contributing to OpenAxis!
