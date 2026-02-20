"""
Pipeline orchestrator for end-to-end manufacturing workflow.

Chains: geometry load -> slicer config -> slice -> toolpath -> IK solve -> trajectory

Each step delegates to existing, proven library-backed services:
- Geometry: trimesh + COMPAS (via GeometryService)
- Slicing: ORNL Slicer 2 subprocess (via ToolpathService)
- IK: roboticstoolbox-python DH solver primary, compas_fab/PyBullet fallback (via RobotService)
- Simulation: PyBullet (via SimulationService)

No custom math. All operations call library functions through existing services.

Modeled on:
- Drake's Systems pattern (declarative step chaining)
- CuraEngine's subprocess pattern (clean process boundaries)

Reference: docs/BEST_PRACTICES_REFERENCE.md Section 5
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from openaxis.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for a single pipeline run."""

    geometry_path: str
    slicing_params: Dict[str, Any] = field(default_factory=dict)
    robot_name: str = "abb_irb6700"
    tcp_offset: Optional[List[float]] = None
    part_position: Optional[List[float]] = None


@dataclass
class StepResult:
    """Result of a single pipeline step."""

    name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_s: float = 0.0


@dataclass
class PipelineResult:
    """Result of a complete pipeline run."""

    success: bool
    toolpath_data: Optional[Dict[str, Any]] = None
    simulation_data: Optional[Dict[str, Any]] = None
    trajectory_data: Optional[Dict[str, Any]] = None
    steps: List[StepResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timings: Dict[str, float] = field(default_factory=dict)
    step_completed: str = ""  # Last step that completed successfully


# Type alias for progress callback: (step_name, fraction 0.0-1.0)
ProgressCallback = Callable[[str, float], None]


def _noop_callback(step: str, pct: float) -> None:
    pass


class Pipeline:
    """End-to-end manufacturing pipeline orchestrator.

    Chains geometry loading, slicing, simulation setup, and IK solving
    into a single execution path. Each step delegates to the existing
    backend service layer — no new math or algorithms.

    Usage:
        pipeline = Pipeline(
            toolpath_service=state.toolpath_service,
            robot_service=state.robot_service,
            simulation_service=state.simulation_service,
        )
        result = pipeline.execute(PipelineConfig(geometry_path="part.stl"))
    """

    def __init__(
        self,
        toolpath_service: Any,
        robot_service: Any = None,
        simulation_service: Any = None,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        self._toolpath_service = toolpath_service
        self._robot_service = robot_service
        self._simulation_service = simulation_service
        self._progress = progress_callback or _noop_callback

    def execute(self, config: PipelineConfig) -> PipelineResult:
        """Execute the full pipeline: slice -> simulate -> IK solve.

        Each step is independent and testable in isolation.
        Partial failure returns partial results (e.g., slicing succeeds
        but IK fails — you still get the toolpath).
        """
        result = PipelineResult(success=False)

        # Step 1: Generate toolpath (geometry load + slice via ORNL Slicer 2)
        step = self._run_step(
            "slicing",
            lambda: self._toolpath_service.generate_toolpath(
                config.geometry_path,
                config.slicing_params,
                config.part_position,
            ),
        )
        result.steps.append(step)
        if not step.success:
            result.errors.append(f"Slicing failed: {step.error}")
            return result
        result.toolpath_data = step.data
        result.step_completed = "slicing"
        result.timings["slicing"] = step.duration_s

        # Step 2: Create simulation trajectory (optional)
        if self._simulation_service and result.toolpath_data:
            step = self._run_step(
                "simulation",
                lambda: self._create_simulation(result.toolpath_data),
            )
            result.steps.append(step)
            if step.success:
                result.simulation_data = step.data
                result.step_completed = "simulation"
                result.timings["simulation"] = step.duration_s
            else:
                result.errors.append(f"Simulation setup failed: {step.error}")
                # Non-fatal — continue without simulation

        # Step 3: Solve IK for all waypoints (optional)
        if self._robot_service and result.simulation_data:
            waypoints = self._extract_waypoints(result.simulation_data)
            if waypoints:
                step = self._run_step(
                    "ik_solve",
                    lambda: self._robot_service.solve_toolpath_ik(
                        waypoints,
                        tcp_offset=config.tcp_offset,
                    ),
                )
                result.steps.append(step)
                if step.success:
                    result.trajectory_data = step.data
                    result.step_completed = "ik_solve"
                    result.timings["ik_solve"] = step.duration_s
                else:
                    result.errors.append(f"IK solve failed: {step.error}")

        result.success = True
        return result

    def _run_step(self, name: str, fn: Callable) -> StepResult:
        """Execute a single pipeline step with timing and error handling."""
        self._progress(name, 0.0)
        t0 = time.perf_counter()
        try:
            data = fn()
            duration = time.perf_counter() - t0
            self._progress(name, 1.0)
            logger.info("pipeline_step_complete", step=name, duration_s=round(duration, 2))
            return StepResult(name=name, success=True, data=data, duration_s=duration)
        except Exception as e:
            duration = time.perf_counter() - t0
            logger.error("pipeline_step_failed", step=name, duration_s=round(duration, 2), error=str(e))
            return StepResult(
                name=name, success=False, error=str(e), duration_s=duration
            )

    def _create_simulation(self, toolpath_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create simulation and extract trajectory."""
        sim_info = self._simulation_service.create_simulation(toolpath_data)
        trajectory = self._simulation_service.get_trajectory(sim_info.get("id"))
        return {
            "sim_id": sim_info.get("id"),
            "trajectory": trajectory,
            "totalTime": trajectory.get("totalTime", 0),
            "totalWaypoints": trajectory.get("totalWaypoints", 0),
        }

    @staticmethod
    def _extract_waypoints(sim_data: Dict[str, Any]) -> List[List[float]]:
        """Extract position arrays from simulation trajectory data."""
        trajectory = sim_data.get("trajectory", {})
        waypoints = trajectory.get("waypoints", [])
        return [wp["position"] for wp in waypoints if "position" in wp]
