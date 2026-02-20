"""
Geometry processing service for OpenAxis backend.

Handles geometry loading, conversion, and processing.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openaxis.core.logging import get_logger

logger = get_logger(__name__)

try:
    from openaxis.core.geometry import GeometryLoader, GeometryConverter, BoundingBox
    from openaxis.core.exceptions import GeometryError
    import trimesh
    GEOMETRY_AVAILABLE = True
except ImportError as e:
    logger.warning("geometry_modules_unavailable", error=str(e))
    GEOMETRY_AVAILABLE = False


class GeometryService:
    """Service for handling geometry operations"""

    def __init__(self):
        self.loaded_geometries: Dict[str, Any] = {}

    def load_geometry(self, file_path: str) -> Dict[str, Any]:
        """
        Load geometry from file and return metadata.

        Args:
            file_path: Path to geometry file

        Returns:
            Dictionary with geometry metadata
        """
        if not GEOMETRY_AVAILABLE:
            raise Exception("Geometry modules not available")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_format = path.suffix.lower()

        # For STEP files, we need to convert them to a format Three.js can handle
        if file_format in ['.step', '.stp']:
            return self._load_step_file(path)
        else:
            # For STL, OBJ, etc. - load directly
            return self._load_mesh_file(path)

    def _load_step_file(self, path: Path) -> Dict[str, Any]:
        """
        Load STEP file and convert to STL for frontend.

        Args:
            path: Path to STEP file

        Returns:
            Dictionary with geometry info including converted STL path
        """
        try:
            # Load STEP with trimesh (requires optional dependencies)
            mesh = trimesh.load(str(path))

            if isinstance(mesh, trimesh.Scene):
                # Combine all geometries
                mesh = trimesh.util.concatenate(
                    [geom for geom in mesh.geometry.values()
                     if isinstance(geom, trimesh.Trimesh)]
                )

            # Create temporary STL file
            temp_dir = Path(tempfile.gettempdir()) / "openaxis_converted"
            temp_dir.mkdir(exist_ok=True)

            temp_stl = temp_dir / f"{path.stem}_converted.stl"
            mesh.export(str(temp_stl))

            # Get mesh info
            bounds = mesh.bounds
            dimensions = bounds[1] - bounds[0]

            geometry_id = str(hash(str(path)))

            geometry_data = {
                'id': geometry_id,
                'originalPath': str(path),
                'convertedPath': str(temp_stl),
                'format': 'step',
                'converted': True,
                'convertedFormat': 'stl',
                'vertices': len(mesh.vertices),
                'faces': len(mesh.faces),
                'dimensions': {
                    'x': float(dimensions[0]),
                    'y': float(dimensions[1]),
                    'z': float(dimensions[2])
                },
                'center': {
                    'x': float(mesh.centroid[0]),
                    'y': float(mesh.centroid[1]),
                    'z': float(mesh.centroid[2])
                }
            }

            self.loaded_geometries[geometry_id] = geometry_data
            return geometry_data

        except Exception as e:
            raise GeometryError(f"Failed to load STEP file: {e}")

    def _load_mesh_file(self, path: Path) -> Dict[str, Any]:
        """
        Load STL, OBJ, or other mesh file.

        Args:
            path: Path to mesh file

        Returns:
            Dictionary with geometry metadata
        """
        try:
            # Load with trimesh
            mesh = trimesh.load(str(path))

            if isinstance(mesh, trimesh.Scene):
                mesh = trimesh.util.concatenate(
                    [geom for geom in mesh.geometry.values()
                     if isinstance(geom, trimesh.Trimesh)]
                )

            # Get mesh info
            bounds = mesh.bounds
            dimensions = bounds[1] - bounds[0]

            geometry_id = str(hash(str(path)))

            geometry_data = {
                'id': geometry_id,
                'filePath': str(path),
                'format': path.suffix.lower().replace('.', ''),
                'converted': False,
                'vertices': len(mesh.vertices),
                'faces': len(mesh.faces),
                'dimensions': {
                    'x': float(dimensions[0]),
                    'y': float(dimensions[1]),
                    'z': float(dimensions[2])
                },
                'center': {
                    'x': float(mesh.centroid[0]),
                    'y': float(mesh.centroid[1]),
                    'z': float(mesh.centroid[2])
                }
            }

            self.loaded_geometries[geometry_id] = geometry_data
            return geometry_data

        except Exception as e:
            raise GeometryError(f"Failed to load mesh file: {e}")

    def get_geometry(self, geometry_id: str) -> Optional[Dict[str, Any]]:
        """Get loaded geometry by ID"""
        return self.loaded_geometries.get(geometry_id)

    def export_as_stl(self, geometry_id: str, output_path: str) -> str:
        """
        Export geometry as STL.

        Args:
            geometry_id: ID of loaded geometry
            output_path: Output file path

        Returns:
            Path to exported STL file
        """
        if not GEOMETRY_AVAILABLE:
            raise Exception("Geometry modules not available")

        geometry = self.loaded_geometries.get(geometry_id)
        if not geometry:
            raise ValueError(f"Geometry not found: {geometry_id}")

        # If already converted, use that
        if geometry.get('converted'):
            return geometry['convertedPath']

        # Otherwise export
        # TODO: Implement actual export
        return geometry['filePath']
