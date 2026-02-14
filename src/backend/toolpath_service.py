"""
Toolpath generation service for OpenAxis backend.

Handles toolpath slicing and generation.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from openaxis.slicing import PlanarSlicer, Toolpath, InfillPattern
    from openaxis.core.geometry import GeometryLoader
    SLICING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Slicing modules not available: {e}")
    SLICING_AVAILABLE = False


class ToolpathService:
    """Service for handling toolpath generation"""

    def __init__(self):
        self.toolpaths: Dict[str, Any] = {}

    def generate_toolpath(
        self,
        geometry_path: str,
        params: Optional[Dict[str, Any]] = None,
        part_position: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Generate toolpath from geometry.

        Args:
            geometry_path: Path to geometry file
            params: Slicing parameters
            part_position: [x, y, z] offset in mm (Z-up) — mesh is translated
                           *before* slicing so waypoints are generated in-place.

        Returns:
            Dictionary with toolpath data
        """
        if not SLICING_AVAILABLE:
            raise Exception("Slicing modules not available")

        # Default parameters
        if params is None:
            params = {}

        layer_height = params.get('layerHeight', 2.0)
        extrusion_width = params.get('extrusionWidth', 2.5)
        wall_count = params.get('wallCount', 2)
        infill_density = params.get('infillDensity', 0.2)
        infill_pattern = params.get('infillPattern', 'lines')

        try:
            # Load geometry
            mesh = GeometryLoader.load(geometry_path)

            # Translate mesh to part position before slicing so that the
            # slicer produces waypoints already at the correct location.
            if part_position and len(part_position) >= 3:
                ox, oy, oz = part_position[0], part_position[1], part_position[2]
                if ox != 0 or oy != 0 or oz != 0:
                    from openaxis.core.geometry import TransformationUtilities
                    mesh = TransformationUtilities.translate(mesh, [ox, oy, oz])

            # Create slicer
            pattern_map = {
                'lines': InfillPattern.LINES,
                'grid': InfillPattern.GRID,
                'triangles': InfillPattern.TRIANGLES,
                'hexagons': InfillPattern.HEXAGONS,
            }

            slicer = PlanarSlicer(
                layer_height=layer_height,
                extrusion_width=extrusion_width,
                wall_count=wall_count,
                infill_density=infill_density,
                infill_pattern=pattern_map.get(infill_pattern, InfillPattern.LINES),
            )

            # Generate toolpath
            toolpath = slicer.slice(mesh)

            # Post-process: optimize segment order for smooth printing
            # (nearest-neighbor reordering + cross-layer continuity)
            toolpath.optimize_segment_order()

            # Insert explicit travel segments between non-adjacent segments
            # (creates continuous motion for simulation)
            toolpath.insert_travel_segments()

            # Convert toolpath to JSON-serializable format
            toolpath_data = self._toolpath_to_dict(toolpath, params)

            # Store toolpath
            toolpath_id = str(hash(geometry_path + str(params)))
            self.toolpaths[toolpath_id] = toolpath_data

            return toolpath_data

        except Exception as e:
            raise Exception(f"Failed to generate toolpath: {e}")

    def _toolpath_to_dict(self, toolpath: 'Toolpath', params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Toolpath object to dictionary.

        Args:
            toolpath: Toolpath object
            params: Original parameters

        Returns:
            Dictionary representation
        """
        segments_data = []

        for segment in toolpath.segments:
            seg_dict = {
                'type': segment.type.value if hasattr(segment.type, 'value') else str(segment.type),
                'layer': segment.layer_index,
                'points': [[float(p[0]), float(p[1]), float(p[2])] for p in segment.points],
                'speed': float(segment.speed) if segment.speed else 1000.0,
                'extrusionRate': float(segment.flow_rate) if segment.flow_rate else 1.0,
            }
            segments_data.append(seg_dict)

        toolpath_data = {
            'id': str(hash(str(segments_data))),
            'layerHeight': float(toolpath.layer_height),
            'totalLayers': int(toolpath.total_layers),
            'processType': str(toolpath.process_type),
            'segments': segments_data,
            'statistics': {
                'totalSegments': len(segments_data),
                'totalPoints': sum(len(s['points']) for s in segments_data),
                'layerCount': toolpath.total_layers,
                'estimatedTime': self._estimate_time(segments_data),
                'estimatedMaterial': self._estimate_material(segments_data),
            },
            'params': params,
        }

        return toolpath_data

    def _estimate_time(self, segments: List[Dict[str, Any]]) -> float:
        """Estimate total print time in seconds"""
        total_time = 0.0
        for segment in segments:
            points = segment['points']
            speed = segment.get('speed', 1000.0)  # mm/min

            # Calculate path length
            length = 0.0
            for i in range(1, len(points)):
                p1 = points[i-1]
                p2 = points[i]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                dz = p2[2] - p1[2]
                length += (dx*dx + dy*dy + dz*dz) ** 0.5

            # Time = distance / speed (convert mm/min to mm/sec)
            total_time += (length / speed) * 60

        return round(total_time, 2)

    def _estimate_material(self, segments: List[Dict[str, Any]]) -> float:
        """Estimate material usage (relative units)"""
        total_material = 0.0
        for segment in segments:
            points = segment['points']
            extrusion_rate = segment.get('extrusionRate', 1.0)

            # Calculate path length
            length = 0.0
            for i in range(1, len(points)):
                p1 = points[i-1]
                p2 = points[i]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                dz = p2[2] - p1[2]
                length += (dx*dx + dy*dy + dz*dz) ** 0.5

            total_material += length * extrusion_rate

        return round(total_material, 2)

    def get_toolpath(self, toolpath_id: str) -> Optional[Dict[str, Any]]:
        """Get toolpath by ID"""
        return self.toolpaths.get(toolpath_id)

    def export_gcode(self, toolpath_id: str, output_path: str) -> str:
        """
        Export toolpath as G-code.

        Args:
            toolpath_id: ID of toolpath
            output_path: Output file path

        Returns:
            Path to exported G-code file
        """
        toolpath_data = self.toolpaths.get(toolpath_id)
        if not toolpath_data:
            raise ValueError(f"Toolpath not found: {toolpath_id}")

        # TODO: Implement G-code export
        # For now, return placeholder
        return output_path
