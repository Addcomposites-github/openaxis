"""
Simulation service for OpenAxis backend.

Manages simulation state and provides trajectory data for the frontend.
This service runs simulation computations (IK, trajectory) and serves
results to the UI - the actual 3D rendering happens in Three.js.
"""

import sys
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from openaxis.slicing.toolpath import Toolpath, ToolpathSegment
    TOOLPATH_AVAILABLE = True
except ImportError:
    TOOLPATH_AVAILABLE = False


class SimulationService:
    """Service for managing simulation state and trajectory playback."""

    def __init__(self):
        self._simulations: Dict[str, Dict[str, Any]] = {}
        self._current_sim_id: Optional[str] = None

    def create_simulation(
        self,
        toolpath_data: Dict[str, Any],
        robot_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new simulation from toolpath data.

        Extracts waypoints from the toolpath and prepares the trajectory
        for frontend playback (joint angles over time).
        """
        sim_id = f"sim_{int(time.time())}"

        # Extract waypoints from toolpath segments
        waypoints = []
        segment_info = []
        current_time = 0.0
        prev_end_point = None  # Track the last point to add inter-segment travel time

        for seg in toolpath_data.get("segments", []):
            points = seg.get("points", [])
            speed = seg.get("speed", 50.0)  # mm/s
            seg_type = seg.get("type", "perimeter")

            if not points:
                continue

            # Add travel time between segments when there's a gap
            if prev_end_point is not None:
                first_pt = points[0]
                dx = first_pt[0] - prev_end_point[0]
                dy = first_pt[1] - prev_end_point[1]
                dz = first_pt[2] - prev_end_point[2]
                gap_dist = (dx**2 + dy**2 + dz**2) ** 0.5
                if gap_dist > 0.1:  # mm threshold
                    # Use travel speed (faster than print speed) for gaps
                    travel_speed = max(speed, 200.0)  # At least 200 mm/s for travel
                    current_time += gap_dist / travel_speed

            for i, pt in enumerate(points):
                if i > 0:
                    # Calculate time from distance and speed BEFORE adding waypoint
                    prev = points[i - 1]
                    dx = pt[0] - prev[0]
                    dy = pt[1] - prev[1]
                    dz = pt[2] - prev[2]
                    dist = (dx**2 + dy**2 + dz**2) ** 0.5
                    current_time += dist / max(speed, 0.1)

                waypoints.append({
                    "position": pt,
                    "time": current_time,
                    "segmentType": seg_type,
                    "layer": seg.get("layer", 0),
                })

            prev_end_point = points[-1]

        simulation = {
            "id": sim_id,
            "status": "ready",
            "totalTime": current_time,
            "currentTime": 0.0,
            "speed": 1.0,
            "waypoints": waypoints,
            "totalWaypoints": len(waypoints),
            "toolpath": toolpath_data,
            "robotConfig": robot_config,
            "createdAt": time.time(),
        }

        self._simulations[sim_id] = simulation
        self._current_sim_id = sim_id

        return {
            "id": sim_id,
            "status": "ready",
            "totalTime": round(current_time, 2),
            "totalWaypoints": len(waypoints),
            "totalSegments": len(toolpath_data.get("segments", [])),
            "totalLayers": toolpath_data.get("totalLayers", 0),
        }

    def get_simulation_state(self, sim_id: Optional[str] = None) -> Dict[str, Any]:
        """Get current simulation state."""
        sid = sim_id or self._current_sim_id
        if not sid or sid not in self._simulations:
            return {"status": "no_simulation", "error": "No active simulation"}

        sim = self._simulations[sid]
        return {
            "id": sim["id"],
            "status": sim["status"],
            "totalTime": round(sim["totalTime"], 2),
            "currentTime": round(sim["currentTime"], 2),
            "speed": sim["speed"],
            "totalWaypoints": sim["totalWaypoints"],
            "progress": round(sim["currentTime"] / max(sim["totalTime"], 0.01) * 100, 1),
        }

    def get_waypoints_in_range(
        self, start_time: float, end_time: float, sim_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get waypoints within a time range for partial playback."""
        sid = sim_id or self._current_sim_id
        if not sid or sid not in self._simulations:
            return []

        sim = self._simulations[sid]
        return [
            wp for wp in sim["waypoints"]
            if start_time <= wp["time"] <= end_time
        ]

    def get_trajectory(self, sim_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the full trajectory for frontend playback.

        Returns waypoint positions and timing so Three.js can animate the robot.
        """
        sid = sim_id or self._current_sim_id
        if not sid or sid not in self._simulations:
            return {"waypoints": [], "totalTime": 0}

        sim = self._simulations[sid]
        return {
            "waypoints": sim["waypoints"],
            "totalTime": round(sim["totalTime"], 2),
            "totalWaypoints": sim["totalWaypoints"],
        }

    def set_playback(self, current_time: float, speed: float = 1.0, sim_id: Optional[str] = None):
        """Update playback position."""
        sid = sim_id or self._current_sim_id
        if sid and sid in self._simulations:
            self._simulations[sid]["currentTime"] = current_time
            self._simulations[sid]["speed"] = speed
            self._simulations[sid]["status"] = "playing"

    def stop_playback(self, sim_id: Optional[str] = None):
        """Stop playback."""
        sid = sim_id or self._current_sim_id
        if sid and sid in self._simulations:
            self._simulations[sid]["status"] = "stopped"

    def list_simulations(self) -> List[Dict[str, Any]]:
        """List all simulations."""
        return [
            {
                "id": sim["id"],
                "status": sim["status"],
                "totalTime": round(sim["totalTime"], 2),
                "createdAt": sim["createdAt"],
            }
            for sim in self._simulations.values()
        ]
