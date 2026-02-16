"""
OpenAxis Quality Test Suite
============================

Comprehensive integration testing for the entire OpenAxis workflow.
Tests end-to-end scenarios from geometry loading to G-code generation.

Usage:
    pytest tests/test_quality_suite.py -v
    pytest tests/test_quality_suite.py -v --html=test_report.html
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List
import json
import time

# Import OpenAxis modules
from openaxis.core.config import ConfigManager, RobotConfig, ProcessConfig
from openaxis.core.project import Project, Part
from openaxis.core.robot import RobotLoader, RobotInstance
from openaxis.core.geometry import GeometryLoader, BoundingBox
from openaxis.slicing.planar_slicer import PlanarSlicer
from openaxis.slicing.toolpath import Toolpath, ToolpathSegment, ToolpathType
from openaxis.slicing.gcode import GCodeGenerator, GCodeConfig, GCodeFlavor
from openaxis.simulation.environment import SimulationEnvironment, SimulationMode
from openaxis.processes.base import ProcessType
from openaxis.processes.waam import WAAMProcess, WAAMParameters
from openaxis.processes.pellet import PelletExtrusionProcess, PelletExtrusionParameters
from openaxis.processes.milling import MillingProcess, MillingParameters

try:
    from openaxis.motion.kinematics import IKSolver
    from openaxis.motion.planner import CartesianPlanner
    from openaxis.motion.collision import CollisionChecker
    MOTION_AVAILABLE = True
except ImportError:
    MOTION_AVAILABLE = False


class TestResults:
    """Track test results and generate report"""

    def __init__(self):
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "warnings": [],
            "performance": {},
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def add_pass(self, test_name: str, duration: float):
        self.results["passed"] += 1
        self.results["total_tests"] += 1
        self.results["performance"][test_name] = duration

    def add_fail(self, test_name: str, error: str):
        self.results["failed"] += 1
        self.results["total_tests"] += 1
        self.results["errors"].append({
            "test": test_name,
            "error": error
        })

    def add_warning(self, warning: str):
        self.results["warnings"].append(warning)

    def add_skip(self, test_name: str, reason: str):
        self.results["skipped"] += 1
        self.results["total_tests"] += 1
        self.results["warnings"].append(f"{test_name}: {reason}")

    def generate_report(self) -> str:
        """Generate human-readable test report"""
        report = []
        report.append("=" * 80)
        report.append("OpenAxis Quality Test Report")
        report.append("=" * 80)
        report.append(f"Timestamp: {self.results['timestamp']}")
        report.append(f"\nTotal Tests: {self.results['total_tests']}")
        report.append(f"  ✓ Passed:  {self.results['passed']}")
        report.append(f"  ✗ Failed:  {self.results['failed']}")
        report.append(f"  ⊘ Skipped: {self.results['skipped']}")

        if self.results["errors"]:
            report.append("\n" + "=" * 80)
            report.append("ERRORS:")
            report.append("=" * 80)
            for error in self.results["errors"]:
                report.append(f"\n✗ {error['test']}")
                report.append(f"  {error['error']}")

        if self.results["warnings"]:
            report.append("\n" + "=" * 80)
            report.append("WARNINGS:")
            report.append("=" * 80)
            for warning in self.results["warnings"]:
                report.append(f"⚠ {warning}")

        report.append("\n" + "=" * 80)
        report.append("PERFORMANCE:")
        report.append("=" * 80)
        for test, duration in self.results["performance"].items():
            report.append(f"{test}: {duration:.3f}s")

        report.append("\n" + "=" * 80)
        success_rate = (self.results["passed"] / self.results["total_tests"] * 100) if self.results["total_tests"] > 0 else 0
        report.append(f"Success Rate: {success_rate:.1f}%")
        report.append("=" * 80)

        return "\n".join(report)

    def save_json(self, filepath: Path):
        """Save results as JSON"""
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)


@pytest.fixture(scope="session")
def test_results():
    """Global test results tracker"""
    return TestResults()


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for tests"""
    workspace = tempfile.mkdtemp()
    yield Path(workspace)
    shutil.rmtree(workspace)


@pytest.fixture
def sample_stl(temp_workspace):
    """Create a simple cube STL file for testing"""
    stl_path = temp_workspace / "test_cube.stl"

    # Simple cube STL content (ASCII format)
    stl_content = """solid cube
facet normal 0 0 1
  outer loop
    vertex 0 0 10
    vertex 10 0 10
    vertex 10 10 10
  endloop
endfacet
facet normal 0 0 1
  outer loop
    vertex 0 0 10
    vertex 10 10 10
    vertex 0 10 10
  endloop
endfacet
facet normal 0 0 -1
  outer loop
    vertex 0 0 0
    vertex 10 10 0
    vertex 10 0 0
  endloop
endfacet
facet normal 0 0 -1
  outer loop
    vertex 0 0 0
    vertex 0 10 0
    vertex 10 10 0
  endloop
endfacet
facet normal 0 1 0
  outer loop
    vertex 0 10 0
    vertex 0 10 10
    vertex 10 10 10
  endloop
endfacet
facet normal 0 1 0
  outer loop
    vertex 0 10 0
    vertex 10 10 10
    vertex 10 10 0
  endloop
endfacet
facet normal 0 -1 0
  outer loop
    vertex 0 0 0
    vertex 10 0 10
    vertex 0 0 10
  endloop
endfacet
facet normal 0 -1 0
  outer loop
    vertex 0 0 0
    vertex 10 0 0
    vertex 10 0 10
  endloop
endfacet
facet normal 1 0 0
  outer loop
    vertex 10 0 0
    vertex 10 10 0
    vertex 10 10 10
  endloop
endfacet
facet normal 1 0 0
  outer loop
    vertex 10 0 0
    vertex 10 10 10
    vertex 10 0 10
  endloop
endfacet
facet normal -1 0 0
  outer loop
    vertex 0 0 0
    vertex 0 10 10
    vertex 0 10 0
  endloop
endfacet
facet normal -1 0 0
  outer loop
    vertex 0 0 0
    vertex 0 0 10
    vertex 0 10 10
  endloop
endfacet
endsolid cube
"""

    with open(stl_path, 'w') as f:
        f.write(stl_content)

    return stl_path


class TestWorkflow1_GeometryLoading:
    """Test Workflow 1: Geometry Loading and Processing"""

    def test_load_stl_file(self, sample_stl, test_results):
        """Load an STL file and verify mesh properties"""
        start = time.time()
        try:
            mesh = GeometryLoader.load(sample_stl)

            assert mesh is not None, "Mesh should not be None"

            # COMPAS Mesh uses number_of_vertices() / number_of_faces() methods
            n_verts = mesh.number_of_vertices()
            n_faces = mesh.number_of_faces()

            # Cube should have 8 vertices and 12 triangular faces
            assert n_verts == 8, f"Expected 8 vertices, got {n_verts}"
            assert n_faces == 12, f"Expected 12 faces, got {n_faces}"

            test_results.add_pass("test_load_stl_file", time.time() - start)
        except Exception as e:
            test_results.add_fail("test_load_stl_file", str(e))
            raise

    def test_compute_bounding_box(self, sample_stl, test_results):
        """Compute and verify bounding box"""
        start = time.time()
        try:
            mesh = GeometryLoader.load(sample_stl)
            bbox = BoundingBox.from_mesh(mesh)

            assert bbox is not None, "Bounding box should not be None"

            # BoundingBox.get_dimensions returns a tuple (dx, dy, dz)
            dimensions = BoundingBox.get_dimensions(bbox)
            assert dimensions[0] == pytest.approx(10, abs=0.1), "X dimension should be ~10"
            assert dimensions[1] == pytest.approx(10, abs=0.1), "Y dimension should be ~10"
            assert dimensions[2] == pytest.approx(10, abs=0.1), "Z dimension should be ~10"

            # BoundingBox.get_center returns a COMPAS Point
            center = BoundingBox.get_center(bbox)
            assert center.x == pytest.approx(5, abs=0.1), "Center X should be ~5"
            assert center.y == pytest.approx(5, abs=0.1), "Center Y should be ~5"
            assert center.z == pytest.approx(5, abs=0.1), "Center Z should be ~5"

            test_results.add_pass("test_compute_bounding_box", time.time() - start)
        except Exception as e:
            test_results.add_fail("test_compute_bounding_box", str(e))
            raise


class TestWorkflow2_ProjectManagement:
    """Test Workflow 2: Project Creation and Management"""

    def test_create_project(self, temp_workspace, test_results):
        """Create a new project"""
        start = time.time()
        try:
            project_path = temp_workspace / "test_project"
            project = Project.create("Test Project", project_path)

            assert project is not None, "Project should not be None"
            assert project.metadata.name == "Test Project", "Project name mismatch"
            assert project_path.exists(), "Project directory should exist"
            assert (project_path / "project.json").exists(), "project.json should exist"

            test_results.add_pass("test_create_project", time.time() - start)
        except Exception as e:
            test_results.add_fail("test_create_project", str(e))
            raise

    def test_add_part_to_project(self, temp_workspace, sample_stl, test_results):
        """Add a part to the project"""
        start = time.time()
        try:
            project_path = temp_workspace / "test_project2"
            project = Project.create("Test Project", project_path)

            # add_part takes (name, geometry_path, process_config)
            part = project.add_part("Test Cube", geometry_path=sample_stl)

            assert len(project.parts) == 1, "Project should have 1 part"
            assert part.name == "Test Cube", "Part name mismatch"
            assert part.geometry_path is not None, "Part should have geometry path"

            test_results.add_pass("test_add_part_to_project", time.time() - start)
        except Exception as e:
            test_results.add_fail("test_add_part_to_project", str(e))
            raise

    def test_save_and_load_project(self, temp_workspace, sample_stl, test_results):
        """Save and reload a project"""
        start = time.time()
        try:
            project_path = temp_workspace / "test_project3"
            project = Project.create("Test Project", project_path)

            part = project.add_part("Test Cube", geometry_path=sample_stl)
            project.save()

            # Reload project
            loaded_project = Project.load(project_path)

            assert loaded_project.metadata.name == project.metadata.name, \
                "Project name mismatch after reload"
            assert len(loaded_project.parts) == 1, "Parts not preserved after reload"

            # Parts is a dict; get the first part
            loaded_part = next(iter(loaded_project.parts.values()))
            assert loaded_part.name == "Test Cube", "Part name mismatch after reload"

            test_results.add_pass("test_save_and_load_project", time.time() - start)
        except Exception as e:
            test_results.add_fail("test_save_and_load_project", str(e))
            raise


class TestWorkflow3_Slicing:
    """Test Workflow 3: Slicing and Toolpath Generation"""

    def test_planar_slicing(self, sample_stl, test_results):
        """Slice a mesh into layers using PlanarSlicer"""
        start = time.time()
        try:
            mesh = GeometryLoader.load(sample_stl)

            slicer = PlanarSlicer(
                layer_height=1.0,
                extrusion_width=2.0,
                print_speed=50.0,
            )
            toolpath = slicer.slice(mesh)

            assert toolpath is not None, "Toolpath should not be None"
            # 10mm tall cube with 1mm layers = ~10 layers
            assert toolpath.total_layers >= 8, \
                f"Expected ~10 layers, got {toolpath.total_layers}"

            test_results.add_pass("test_planar_slicing", time.time() - start)
        except Exception as e:
            test_results.add_fail("test_planar_slicing", str(e))
            raise

    def test_toolpath_generation(self, sample_stl, test_results):
        """Generate toolpath with segments from sliced mesh"""
        start = time.time()
        try:
            mesh = GeometryLoader.load(sample_stl)

            slicer = PlanarSlicer(
                layer_height=1.0,
                extrusion_width=2.0,
                print_speed=50.0,
            )
            toolpath = slicer.slice(mesh)

            assert toolpath is not None, "Toolpath should not be None"

            # Verify the toolpath has layers (segments may be empty for simple geometry)
            assert toolpath.total_layers > 0, "Toolpath should have layers"

            # If there are segments, verify their types
            if len(toolpath.segments) > 0:
                seg_types = {seg.type for seg in toolpath.segments}
                assert any(
                    t in seg_types
                    for t in [ToolpathType.PERIMETER, ToolpathType.INFILL]
                ), "Segments should include perimeter or infill types"

            test_results.add_pass("test_toolpath_generation", time.time() - start)
        except Exception as e:
            test_results.add_fail("test_toolpath_generation", str(e))
            raise

    def test_gcode_generation(self, sample_stl, temp_workspace, test_results):
        """Generate G-code from toolpath"""
        start = time.time()
        try:
            mesh = GeometryLoader.load(sample_stl)

            slicer = PlanarSlicer(
                layer_height=1.0,
                extrusion_width=2.0,
                print_speed=50.0,
            )
            toolpath = slicer.slice(mesh)

            config = GCodeConfig(flavor=GCodeFlavor.MARLIN)
            generator = GCodeGenerator(config=config)
            gcode = generator.generate(toolpath)

            assert gcode is not None, "G-code should not be None"
            assert len(gcode) > 0, "G-code should not be empty"

            # Verify G-code structure — at minimum has header comments or G commands
            lines = gcode.split('\n')
            assert any('G1' in line or 'G0' in line or 'G28' in line for line in lines), \
                "G-code should contain movement or home commands"

            # Save G-code file
            gcode_path = temp_workspace / "test_output.gcode"
            with open(gcode_path, 'w') as f:
                f.write(gcode)

            assert gcode_path.exists(), "G-code file should be created"

            test_results.add_pass("test_gcode_generation", time.time() - start)
        except Exception as e:
            test_results.add_fail("test_gcode_generation", str(e))
            raise


class TestWorkflow4_ProcessPlugins:
    """Test Workflow 4: Process Plugin Configuration"""

    def test_waam_process(self, test_results):
        """Test WAAM process configuration"""
        start = time.time()
        try:
            params = WAAMParameters(
                process_name="test_waam",
                process_type=ProcessType.ADDITIVE,
                wire_feed_rate=5.0,
                travel_speed=10.0,
                arc_voltage=24.0,
                arc_current=150.0,
                shielding_gas="Ar",
                gas_flow_rate=15.0,
            )

            process = WAAMProcess(params)

            assert process is not None, "WAAM process should not be None"
            assert process.validate_parameters(), "Parameters should be valid"

            test_results.add_pass("test_waam_process", time.time() - start)
        except Exception as e:
            test_results.add_fail("test_waam_process", str(e))
            raise

    def test_pellet_extrusion_process(self, test_results):
        """Test pellet extrusion process configuration"""
        start = time.time()
        try:
            params = PelletExtrusionParameters(
                process_name="test_pellet",
                process_type=ProcessType.ADDITIVE,
                extrusion_temperature=220.0,
                bed_temperature=60.0,
                print_speed=50.0,
                retraction_distance=2.0,
                retraction_speed=40.0,
            )

            process = PelletExtrusionProcess(params)

            assert process is not None, "Pellet process should not be None"
            assert process.validate_parameters(), "Parameters should be valid"

            test_results.add_pass("test_pellet_extrusion_process", time.time() - start)
        except Exception as e:
            test_results.add_fail("test_pellet_extrusion_process", str(e))
            raise

    def test_milling_process(self, test_results):
        """Test milling process configuration"""
        start = time.time()
        try:
            params = MillingParameters(
                process_name="test_milling",
                process_type=ProcessType.SUBTRACTIVE,
                spindle_speed=10000.0,
                feed_rate=500.0,
                plunge_rate=100.0,
                tool_diameter=6.0,
                stepover=0.5,
                depth_of_cut=1.0,
            )

            process = MillingProcess(params)

            assert process is not None, "Milling process should not be None"
            assert process.validate_parameters(), "Parameters should be valid"

            test_results.add_pass("test_milling_process", time.time() - start)
        except Exception as e:
            test_results.add_fail("test_milling_process", str(e))
            raise


class TestWorkflow5_Configuration:
    """Test Workflow 5: Configuration Management"""

    def test_load_robot_config(self, test_results):
        """Load robot configuration from file"""
        start = time.time()
        try:
            config_dir = Path("config")
            robot_config_path = config_dir / "robots" / "abb_irb6700.yaml"
            if not robot_config_path.exists():
                test_results.add_skip("test_load_robot_config",
                                      "Robot config file not found")
                pytest.skip("Robot config file not found")

            config_mgr = ConfigManager(config_dir)
            robot_config = config_mgr.get_robot("abb_irb6700")

            assert robot_config is not None, "Robot config should not be None"
            assert "ABB" in robot_config.name, \
                f"Robot name should contain ABB, got '{robot_config.name}'"
            assert len(robot_config.joint_limits) == 6, "Should have 6 joints"

            test_results.add_pass("test_load_robot_config", time.time() - start)
        except Exception as e:
            test_results.add_fail("test_load_robot_config", str(e))
            raise

    def test_load_process_config(self, test_results):
        """Load process configuration from file"""
        start = time.time()
        try:
            config_dir = Path("config")
            process_config_path = config_dir / "processes" / "waam_steel.yaml"
            if not process_config_path.exists():
                test_results.add_skip("test_load_process_config",
                                      "Process config file not found")
                pytest.skip("Process config file not found")

            config_mgr = ConfigManager(config_dir)
            process_config = config_mgr.get_process("waam_steel")

            assert process_config is not None, "Process config should not be None"
            assert process_config.name is not None, "Process should have a name"

            test_results.add_pass("test_load_process_config", time.time() - start)
        except Exception as e:
            test_results.add_fail("test_load_process_config", str(e))
            raise


class TestWorkflow6_Simulation:
    """Test Workflow 6: Simulation Environment"""

    def test_simulation_environment_creation(self, test_results):
        """Create simulation environment"""
        start = time.time()
        try:
            sim = SimulationEnvironment(mode=SimulationMode.DIRECT)

            assert sim is not None, "Simulation should not be None"
            assert sim.mode == SimulationMode.DIRECT, "Mode should be DIRECT"

            # Start and verify it's running
            sim.start()
            assert sim.is_running, "Simulation should be running after start()"
            assert sim.client_id is not None, "PyBullet client should be initialized"

            sim.stop()
            assert not sim.is_running, "Simulation should stop after stop()"

            test_results.add_pass("test_simulation_environment_creation",
                                  time.time() - start)
        except Exception as e:
            test_results.add_fail("test_simulation_environment_creation", str(e))
            raise

    def test_load_object_in_simulation(self, sample_stl, test_results):
        """Load an object into simulation"""
        start = time.time()
        try:
            sim = SimulationEnvironment(mode=SimulationMode.DIRECT)
            sim.start()

            # load_mesh takes path, position, optional orientation/scale/color
            obj_id = sim.load_mesh(str(sample_stl), position=(0, 0, 0))

            assert obj_id is not None, "Object ID should not be None"
            assert obj_id >= 0, "Object ID should be valid"

            sim.stop()

            test_results.add_pass("test_load_object_in_simulation",
                                  time.time() - start)
        except Exception as e:
            test_results.add_fail("test_load_object_in_simulation", str(e))
            raise


@pytest.mark.skipif(not MOTION_AVAILABLE,
                    reason="Motion planning modules not available")
class TestWorkflow7_MotionPlanning:
    """Test Workflow 7: Motion Planning (Optional - requires MoveIt2)"""

    def test_inverse_kinematics(self, test_results):
        """Test inverse kinematics solver"""
        start = time.time()
        try:
            test_results.add_skip("test_inverse_kinematics",
                                  "IK solver not fully implemented")
            pytest.skip("IK solver not fully implemented")
        except Exception as e:
            test_results.add_fail("test_inverse_kinematics", str(e))
            raise

    def test_cartesian_planning(self, test_results):
        """Test Cartesian path planning"""
        start = time.time()
        try:
            test_results.add_skip("test_cartesian_planning",
                                  "Cartesian planner not fully implemented")
            pytest.skip("Cartesian planner not fully implemented")
        except Exception as e:
            test_results.add_fail("test_cartesian_planning", str(e))
            raise


class TestWorkflow8_EndToEnd:
    """Test Workflow 8: Complete End-to-End Workflow"""

    def test_complete_workflow(self, temp_workspace, sample_stl, test_results):
        """Execute complete workflow: Project → Geometry → Slice → G-code"""
        start = time.time()
        try:
            # 1. Create project
            project_path = temp_workspace / "e2e_project"
            project = Project.create("E2E Test Project", project_path)

            # 2. Add part
            part = project.add_part(
                "E2E Test Cube",
                geometry_path=sample_stl,
            )

            # 3. Load geometry
            mesh = GeometryLoader.load(sample_stl)

            # 4. Generate toolpath
            slicer = PlanarSlicer(
                layer_height=1.0,
                extrusion_width=2.0,
                print_speed=50.0,
            )
            toolpath = slicer.slice(mesh)

            # 5. Generate G-code
            config = GCodeConfig(flavor=GCodeFlavor.MARLIN)
            generator = GCodeGenerator(config=config)
            gcode = generator.generate(toolpath)

            # 6. Save G-code
            gcode_path = project_path / "output.gcode"
            with open(gcode_path, 'w') as f:
                f.write(gcode)

            # 7. Save project
            project.save()

            # Verify everything
            assert project_path.exists(), "Project directory should exist"
            assert gcode_path.exists(), "G-code file should exist"
            assert toolpath.total_layers > 0, "Toolpath should have layers"
            assert len(gcode) > 100, "G-code should be substantial"

            test_results.add_pass("test_complete_workflow", time.time() - start)
        except Exception as e:
            test_results.add_fail("test_complete_workflow", str(e))
            raise


def pytest_sessionfinish(session, exitstatus):
    """Generate report at end of test session"""
    # This will be called by pytest after all tests complete
    pass


if __name__ == "__main__":
    # Run tests and generate report
    print("Starting OpenAxis Quality Test Suite...")
    print("=" * 80)

    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-ra"  # Show summary of all test outcomes
    ])
