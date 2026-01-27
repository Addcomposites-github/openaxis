#!/usr/bin/env python3
"""
OpenAxis System Diagnostics
===========================

Comprehensive system check to validate OpenAxis installation and configuration.

Usage:
    python scripts/diagnose_system.py
"""

import sys
import os
from pathlib import Path
import importlib
import platform


class SystemDiagnostics:
    """Diagnostic checks for OpenAxis system"""

    def __init__(self):
        self.results = []
        self.errors = []
        self.warnings = []

    def check(self, name: str, test_func, critical: bool = False):
        """Run a diagnostic check"""
        try:
            result = test_func()
            self.results.append({
                "name": name,
                "status": "[PASS]" if result else "[FAIL]",
                "passed": result,
                "critical": critical
            })
            return result
        except Exception as e:
            self.results.append({
                "name": name,
                "status": "[ERROR]",
                "passed": False,
                "critical": critical,
                "error": str(e)
            })
            if critical:
                self.errors.append(f"{name}: {e}")
            else:
                self.warnings.append(f"{name}: {e}")
            return False

    def print_results(self):
        """Print diagnostic results"""
        print("\n" + "=" * 80)
        print("OpenAxis System Diagnostics Report")
        print("=" * 80)

        print(f"\nSystem Information:")
        print(f"  Platform: {platform.system()} {platform.release()}")
        print(f"  Python: {sys.version.split()[0]}")
        print(f"  Working Directory: {os.getcwd()}")

        print(f"\nDiagnostic Results:")
        print("-" * 80)

        for result in self.results:
            critical_mark = " [CRITICAL]" if result.get("critical") else ""
            print(f"{result['status']:10} {result['name']}{critical_mark}")
            if "error" in result:
                print(f"           Error: {result['error']}")

        print("\n" + "=" * 80)

        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        print(f"Results: {passed}/{total} checks passed")

        if self.errors:
            print(f"\n[X] CRITICAL ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings:
            print(f"\n[!] WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")

        print("=" * 80)

        return len(self.errors) == 0


def check_python_version():
    """Check Python version is 3.10+"""
    version = sys.version_info
    return version.major == 3 and version.minor >= 10


def check_openaxis_installed():
    """Check if openaxis package is installed"""
    try:
        import openaxis
        return True
    except ImportError:
        return False


def check_core_modules():
    """Check if core modules can be imported"""
    try:
        from openaxis.core.config import ConfigManager
        from openaxis.core.project import Project
        from openaxis.core.robot import RobotLoader
        from openaxis.core.geometry import GeometryLoader
        return True
    except ImportError:
        return False


def check_slicing_modules():
    """Check if slicing modules can be imported"""
    try:
        from openaxis.slicing.planar_slicer import PlanarSlicer
        from openaxis.slicing.toolpath import Toolpath
        from openaxis.slicing.gcode import GCodeGenerator
        return True
    except ImportError:
        return False


def check_process_modules():
    """Check if process modules can be imported"""
    try:
        from openaxis.processes.waam import WAAMProcess
        from openaxis.processes.pellet import PelletExtrusionProcess
        from openaxis.processes.milling import MillingProcess
        return True
    except ImportError:
        return False


def check_simulation_modules():
    """Check if simulation modules can be imported"""
    try:
        from openaxis.simulation.environment import SimulationEnvironment
        return True
    except ImportError:
        return False


def check_motion_modules():
    """Check if motion planning modules can be imported"""
    try:
        from openaxis.motion.kinematics import IKSolver
        from openaxis.motion.planner import CartesianPlanner
        from openaxis.motion.collision import CollisionChecker
        return True
    except ImportError:
        return False


def check_compas_installed():
    """Check if COMPAS is installed"""
    try:
        import compas
        return True
    except ImportError:
        return False


def check_compas_fab_installed():
    """Check if compas_fab is installed"""
    try:
        import compas_fab
        return True
    except ImportError:
        return False


def check_pybullet_installed():
    """Check if PyBullet is installed"""
    try:
        import pybullet
        return True
    except ImportError:
        return False


def check_trimesh_installed():
    """Check if trimesh is installed"""
    try:
        import trimesh
        return True
    except ImportError:
        return False


def check_numpy_installed():
    """Check if numpy is installed"""
    try:
        import numpy
        return True
    except ImportError:
        return False


def check_scipy_installed():
    """Check if scipy is installed"""
    try:
        import scipy
        return True
    except ImportError:
        return False


def check_config_directory():
    """Check if config directory exists"""
    config_dir = Path("config")
    return config_dir.exists() and config_dir.is_dir()


def check_robot_configs():
    """Check if robot configuration files exist"""
    robot_dir = Path("config/robots")
    if not robot_dir.exists():
        return False
    configs = list(robot_dir.glob("*.yaml"))
    return len(configs) > 0


def check_process_configs():
    """Check if process configuration files exist"""
    process_dir = Path("config/processes")
    if not process_dir.exists():
        return False
    configs = list(process_dir.glob("*.yaml"))
    return len(configs) > 0


def check_test_directory():
    """Check if test directory exists"""
    test_dir = Path("tests")
    return test_dir.exists() and test_dir.is_dir()


def check_pytest_installed():
    """Check if pytest is installed"""
    try:
        import pytest
        return True
    except ImportError:
        return False


def check_backend_server():
    """Check if backend server file exists"""
    server_file = Path("src/backend/server.py")
    return server_file.exists()


def check_ui_directory():
    """Check if UI directory exists"""
    ui_dir = Path("src/ui")
    return ui_dir.exists() and ui_dir.is_dir()


def check_examples_directory():
    """Check if examples directory exists"""
    examples_dir = Path("examples")
    if not examples_dir.exists():
        return False
    examples = list(examples_dir.glob("*.py"))
    return len(examples) > 0


def main():
    """Run all diagnostics"""
    diag = SystemDiagnostics()

    # Critical checks
    diag.check("Python 3.10+", check_python_version, critical=True)
    diag.check("OpenAxis package installed", check_openaxis_installed, critical=True)

    # Core dependencies
    diag.check("NumPy installed", check_numpy_installed, critical=True)
    diag.check("SciPy installed", check_scipy_installed)
    diag.check("Trimesh installed", check_trimesh_installed)
    diag.check("COMPAS installed", check_compas_installed)
    diag.check("COMPAS FAB installed", check_compas_fab_installed)
    diag.check("PyBullet installed", check_pybullet_installed)

    # OpenAxis modules
    diag.check("Core modules", check_core_modules, critical=True)
    diag.check("Slicing modules", check_slicing_modules, critical=True)
    diag.check("Process modules", check_process_modules)
    diag.check("Simulation modules", check_simulation_modules)
    diag.check("Motion planning modules", check_motion_modules)

    # Configuration
    diag.check("Config directory", check_config_directory)
    diag.check("Robot configurations", check_robot_configs)
    diag.check("Process configurations", check_process_configs)

    # Development
    diag.check("Test directory", check_test_directory)
    diag.check("pytest installed", check_pytest_installed)
    diag.check("Backend server", check_backend_server)
    diag.check("UI directory", check_ui_directory)
    diag.check("Examples directory", check_examples_directory)

    # Print results
    success = diag.print_results()

    if success:
        print("\n[OK] System is ready for OpenAxis development!")
        print("\nNext steps:")
        print("  1. Run tests: python -m pytest tests/")
        print("  2. Run quality suite: python scripts/run_quality_tests.py")
        print("  3. Start backend: python src/backend/server.py")
        return 0
    else:
        print("\n[X] System has critical errors. Please fix them before continuing.")
        print("\nTo fix:")
        print("  1. Install missing dependencies: pip install -e .")
        print("  2. Check Python version: python --version")
        print("  3. Verify OpenAxis is in PYTHONPATH")
        return 1


if __name__ == "__main__":
    sys.exit(main())
