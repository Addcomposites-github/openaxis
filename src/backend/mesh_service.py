"""
Mesh operations service for OpenAxis backend.

Wraps mesh_operations module with undo support and JSON-serializable
results for the REST API.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from openaxis.geometry.mesh_operations import (
        boolean_union,
        boolean_subtract,
        boolean_intersect,
        repair_mesh,
        analyze_mesh,
        offset_mesh,
    )
    from openaxis.core.geometry import GeometryLoader, GeometryConverter, BoundingBox
    MESH_OPS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Mesh operations not available: {e}")
    MESH_OPS_AVAILABLE = False

logger = logging.getLogger(__name__)


class MeshService:
    """Service wrapping mesh operations with undo stack and geometry store."""

    MAX_UNDO = 20

    def __init__(self) -> None:
        # geometry_id -> COMPAS Mesh
        self._meshes: Dict[str, Any] = {}
        # geometry_id -> list of previous mesh states (for undo)
        self._undo_stacks: Dict[str, list] = {}

    # ------------------------------------------------------------------
    # Geometry store helpers
    # ------------------------------------------------------------------

    def store_mesh(self, geometry_id: str, mesh: Any) -> None:
        """Store a COMPAS mesh by ID."""
        self._meshes[geometry_id] = mesh

    def get_mesh(self, geometry_id: str) -> Optional[Any]:
        """Retrieve a stored COMPAS mesh."""
        return self._meshes.get(geometry_id)

    def _push_undo(self, geometry_id: str) -> None:
        """Push current mesh state onto undo stack before mutation."""
        mesh = self._meshes.get(geometry_id)
        if mesh is None:
            return
        stack = self._undo_stacks.setdefault(geometry_id, [])
        stack.append(mesh.copy())
        # Trim to max size
        if len(stack) > self.MAX_UNDO:
            self._undo_stacks[geometry_id] = stack[-self.MAX_UNDO:]

    def undo(self, geometry_id: str) -> Optional[Dict[str, Any]]:
        """Undo the last mesh operation on the given geometry."""
        stack = self._undo_stacks.get(geometry_id, [])
        if not stack:
            return None
        prev = stack.pop()
        self._meshes[geometry_id] = prev
        return self._mesh_to_info(geometry_id, prev)

    # ------------------------------------------------------------------
    # Boolean operations
    # ------------------------------------------------------------------

    def boolean(
        self,
        geometry_id_a: str,
        geometry_id_b: str,
        operation: str,
        result_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform a boolean operation on two stored meshes.

        Args:
            geometry_id_a: ID of mesh A.
            geometry_id_b: ID of mesh B.
            operation: 'union', 'subtract', or 'intersect'.
            result_id: Optional ID for the result mesh (defaults to A's ID).

        Returns:
            Info dict for the result mesh.
        """
        if not MESH_OPS_AVAILABLE:
            raise RuntimeError("Mesh operations module not available")

        mesh_a = self._meshes.get(geometry_id_a)
        mesh_b = self._meshes.get(geometry_id_b)
        if mesh_a is None:
            raise ValueError(f"Mesh not found: {geometry_id_a}")
        if mesh_b is None:
            raise ValueError(f"Mesh not found: {geometry_id_b}")

        ops = {
            "union": boolean_union,
            "subtract": boolean_subtract,
            "intersect": boolean_intersect,
        }
        fn = ops.get(operation)
        if fn is None:
            raise ValueError(f"Unknown boolean operation: {operation}")

        rid = result_id or geometry_id_a
        self._push_undo(rid)

        result_mesh = fn(mesh_a, mesh_b)
        self._meshes[rid] = result_mesh

        logger.info("Boolean %s: %s op %s -> %s", operation, geometry_id_a, geometry_id_b, rid)
        return self._mesh_to_info(rid, result_mesh)

    # ------------------------------------------------------------------
    # Repair
    # ------------------------------------------------------------------

    def repair(self, geometry_id: str) -> Dict[str, Any]:
        """Repair a stored mesh (fill holes, fix normals, remove degenerate faces)."""
        if not MESH_OPS_AVAILABLE:
            raise RuntimeError("Mesh operations module not available")

        mesh = self._meshes.get(geometry_id)
        if mesh is None:
            raise ValueError(f"Mesh not found: {geometry_id}")

        self._push_undo(geometry_id)

        repaired, report = repair_mesh(mesh)
        self._meshes[geometry_id] = repaired

        info = self._mesh_to_info(geometry_id, repaired)
        info["repairReport"] = report
        return info

    # ------------------------------------------------------------------
    # Analyze
    # ------------------------------------------------------------------

    def analyze(self, geometry_id: str) -> Dict[str, Any]:
        """Analyze mesh quality without modifying it."""
        if not MESH_OPS_AVAILABLE:
            raise RuntimeError("Mesh operations module not available")

        mesh = self._meshes.get(geometry_id)
        if mesh is None:
            raise ValueError(f"Mesh not found: {geometry_id}")

        return analyze_mesh(mesh)

    # ------------------------------------------------------------------
    # Offset
    # ------------------------------------------------------------------

    def offset(self, geometry_id: str, distance: float) -> Dict[str, Any]:
        """Offset a mesh uniformly. Positive = outward, negative = inward."""
        if not MESH_OPS_AVAILABLE:
            raise RuntimeError("Mesh operations module not available")

        mesh = self._meshes.get(geometry_id)
        if mesh is None:
            raise ValueError(f"Mesh not found: {geometry_id}")

        self._push_undo(geometry_id)

        result = offset_mesh(mesh, distance)
        self._meshes[geometry_id] = result

        return self._mesh_to_info(geometry_id, result)

    # ------------------------------------------------------------------
    # Load from file
    # ------------------------------------------------------------------

    def load_from_file(self, geometry_id: str, file_path: str) -> Dict[str, Any]:
        """Load a geometry file and store under geometry_id."""
        if not MESH_OPS_AVAILABLE:
            raise RuntimeError("Mesh operations module not available")

        mesh = GeometryLoader.load(file_path)
        self._meshes[geometry_id] = mesh
        return self._mesh_to_info(geometry_id, mesh)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _mesh_to_info(geometry_id: str, mesh: Any) -> Dict[str, Any]:
        """Convert a COMPAS mesh to a JSON-serializable info dict."""
        try:
            tmesh = GeometryConverter.compas_to_trimesh(mesh)
            bounds = tmesh.bounds.tolist()
            size = (tmesh.bounds[1] - tmesh.bounds[0]).tolist()
            return {
                "id": geometry_id,
                "vertices": len(tmesh.vertices),
                "faces": len(tmesh.faces),
                "isWatertight": bool(tmesh.is_watertight),
                "bounds": {"min": bounds[0], "max": bounds[1]},
                "size": size,
                "volume": float(tmesh.volume) if tmesh.is_volume else None,
                "surfaceArea": float(tmesh.area),
            }
        except Exception:
            return {"id": geometry_id, "vertices": 0, "faces": 0}
