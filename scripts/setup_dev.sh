#!/bin/bash
# OpenAxis Development Environment Setup
# Run this script to set up your development environment

set -e

echo "============================================"
echo "  OpenAxis Development Environment Setup"
echo "============================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
check_prereqs() {
    echo "Checking prerequisites..."
    
    # Check for conda
    if ! command -v conda &> /dev/null; then
        echo -e "${RED}Error: conda is not installed.${NC}"
        echo "Please install Miniconda or Anaconda first:"
        echo "  https://docs.conda.io/en/latest/miniconda.html"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} conda found"
    
    # Check for git
    if ! command -v git &> /dev/null; then
        echo -e "${RED}Error: git is not installed.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} git found"
    
    # Check for Docker (optional but recommended)
    if command -v docker &> /dev/null; then
        echo -e "${GREEN}✓${NC} docker found (optional)"
    else
        echo -e "${YELLOW}!${NC} docker not found (optional, needed for ROS2)"
    fi
    
    echo ""
}

# Create conda environment
create_conda_env() {
    echo "Creating conda environment 'openaxis'..."
    
    if conda env list | grep -q "^openaxis "; then
        echo -e "${YELLOW}Environment 'openaxis' already exists.${NC}"
        read -p "Do you want to remove and recreate it? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            conda env remove -n openaxis -y
        else
            echo "Skipping environment creation."
            return
        fi
    fi
    
    conda create -n openaxis python=3.10 -y
    echo -e "${GREEN}✓${NC} Conda environment created"
}

# Install Python dependencies
install_python_deps() {
    echo ""
    echo "Installing Python dependencies..."
    
    # Activate environment
    eval "$(conda shell.bash hook)"
    conda activate openaxis
    
    # Install core dependencies
    pip install --upgrade pip
    
    # COMPAS ecosystem
    pip install compas>=2.0 compas_fab>=0.28
    
    # Simulation
    pip install pybullet>=3.2
    pip install pybullet_industrial>=1.0
    
    # Geometry processing
    pip install trimesh
    pip install python-fcl
    pip install scipy
    pip install numpy
    
    # Development tools
    pip install pytest pytest-cov pytest-asyncio
    pip install black isort flake8 mypy
    pip install pre-commit
    pip install mkdocs mkdocs-material mkdocstrings[python]
    
    # Optional: Robot Raconteur
    pip install RobotRaconteur robotraconteurcompanion
    
    echo -e "${GREEN}✓${NC} Python dependencies installed"
}

# Setup pre-commit hooks
setup_precommit() {
    echo ""
    echo "Setting up pre-commit hooks..."
    
    eval "$(conda shell.bash hook)"
    conda activate openaxis
    
    if [ -f ".pre-commit-config.yaml" ]; then
        pre-commit install
        echo -e "${GREEN}✓${NC} Pre-commit hooks installed"
    else
        echo -e "${YELLOW}!${NC} No .pre-commit-config.yaml found, skipping"
    fi
}

# Create directory structure
create_directories() {
    echo ""
    echo "Ensuring directory structure..."
    
    mkdir -p src/core
    mkdir -p src/slicing
    mkdir -p src/motion
    mkdir -p src/simulation
    mkdir -p src/hardware
    mkdir -p src/ui
    mkdir -p tests/unit
    mkdir -p tests/integration
    mkdir -p tests/e2e
    mkdir -p config/robots
    mkdir -p config/processes
    mkdir -p docs/api
    mkdir -p docs/guides
    
    echo -e "${GREEN}✓${NC} Directory structure created"
}

# Print final instructions
print_instructions() {
    echo ""
    echo "============================================"
    echo -e "${GREEN}  Setup Complete!${NC}"
    echo "============================================"
    echo ""
    echo "To activate the environment:"
    echo "  conda activate openaxis"
    echo ""
    echo "To run tests:"
    echo "  pytest tests/"
    echo ""
    echo "To start development:"
    echo "  1. Read docs/ROADMAP.md for the development plan"
    echo "  2. Check docs/architecture/system-architecture.md"
    echo "  3. Start with Phase 1.1 tasks"
    echo ""
    echo "For ROS2 components, see scripts/setup_ros2.sh"
    echo ""
}

# Main
main() {
    check_prereqs
    create_conda_env
    install_python_deps
    setup_precommit
    create_directories
    print_instructions
}

main "$@"
