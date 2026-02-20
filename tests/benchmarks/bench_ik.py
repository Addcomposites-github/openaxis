"""
IK solver benchmarks using pytest-benchmark.

Measures performance of the roboticstoolbox-python IK solver at different
toolpath sizes: 100, 1K, 10K waypoints.

Run with::

    python -m pytest tests/benchmarks/bench_ik.py -v --benchmark-sort=name

Results are printed as a table and can be saved as JSON::

    python -m pytest tests/benchmarks/bench_ik.py --benchmark-json=benchmark-results.json
"""

import sys
from pathlib import Path

import pytest

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from backend.robot_service import RobotService
    ROBOT_SERVICE_AVAILABLE = True
except ImportError:
    ROBOT_SERVICE_AVAILABLE = False

pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.skipif(not ROBOT_SERVICE_AVAILABLE, reason="RobotService not available"),
]


def _generate_linear_waypoints(n: int) -> list:
    """Generate a linear path of n waypoints in robot workspace."""
    # Linear path along X from 1.5m to 2.5m, Z at 0.5m (well within IRB 6700 reach)
    waypoints = []
    for i in range(n):
        t = i / max(n - 1, 1)
        x = 1.5 + t * 1.0  # X: 1.5 to 2.5m
        y = 0.0
        z = 0.5
        waypoints.append([x, y, z])
    return waypoints


@pytest.fixture(scope="module")
def robot_service():
    """Create a RobotService for benchmarking."""
    config_dir = str(Path(__file__).parent.parent.parent / "config")
    return RobotService(config_dir=config_dir)


class TestIKBenchmark:
    """IK solver performance benchmarks."""

    def test_ik_100_waypoints(self, robot_service, benchmark):
        """Benchmark IK solve for 100 waypoints."""
        waypoints = _generate_linear_waypoints(100)
        result = benchmark(
            robot_service.solve_toolpath_ik,
            waypoints,
            initial_guess=[0, -0.5, 0.5, 0, -0.5, 0],
            tcp_offset=[0, 0, 0.15, 0, 0, 0],
        )
        assert result["reachableCount"] > 50, "At least 50% should be reachable"

    def test_ik_1000_waypoints(self, robot_service, benchmark):
        """Benchmark IK solve for 1,000 waypoints."""
        waypoints = _generate_linear_waypoints(1000)
        result = benchmark.pedantic(
            robot_service.solve_toolpath_ik,
            args=(waypoints,),
            kwargs={
                "initial_guess": [0, -0.5, 0.5, 0, -0.5, 0],
                "tcp_offset": [0, 0, 0.15, 0, 0, 0],
            },
            rounds=3,
            iterations=1,
        )
        assert result["reachableCount"] > 500

    def test_ik_10000_waypoints(self, robot_service, benchmark):
        """Benchmark IK solve for 10,000 waypoints."""
        waypoints = _generate_linear_waypoints(10000)
        result = benchmark.pedantic(
            robot_service.solve_toolpath_ik,
            args=(waypoints,),
            kwargs={
                "initial_guess": [0, -0.5, 0.5, 0, -0.5, 0],
                "tcp_offset": [0, 0, 0.15, 0, 0, 0],
            },
            rounds=1,
            iterations=1,
        )
        assert result["reachableCount"] > 5000


class TestFKBenchmark:
    """FK solver performance benchmarks."""

    def test_fk_single(self, robot_service, benchmark):
        """Benchmark a single FK computation."""
        result = benchmark(
            robot_service.forward_kinematics,
            [0, -0.5, 0.5, 0, -0.5, 0],
        )
        assert result["valid"] is True
