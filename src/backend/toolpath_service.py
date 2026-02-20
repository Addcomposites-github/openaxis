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

from openaxis.core.logging import get_logger

logger = get_logger(__name__)

try:
    from openaxis.slicing import PlanarSlicer, Toolpath, InfillPattern
    from openaxis.slicing.slicer_factory import get_slicer, SLICER_REGISTRY
    from openaxis.core.geometry import GeometryLoader
    SLICING_AVAILABLE = True
except ImportError as e:
    logger.warning("slicing_modules_unavailable", error=str(e))
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
        infill_pattern = params.get('infillPattern', 'grid')

        # Advanced params (Sprint 5)
        wall_width = params.get('wallWidth', None)
        print_speed = params.get('printSpeed', 1000.0)
        travel_speed = params.get('travelSpeed', 5000.0)
        seam_mode = params.get('seamMode', 'guided')
        seam_shape = params.get('seamShape', 'straight')
        seam_angle = params.get('seamAngle', 0.0)
        lead_in_distance = params.get('leadInDistance', 0.0)
        lead_in_angle = params.get('leadInAngle', 45.0)
        lead_out_distance = params.get('leadOutDistance', 0.0)
        lead_out_angle = params.get('leadOutAngle', 45.0)

        # Sprint 9: Support generation
        support_enabled = params.get('supportEnabled', False)
        support_threshold = params.get('supportThreshold', 45.0)
        support_density = params.get('supportDensity', 0.15)

        # Sprint 7: Strategy selection
        strategy = params.get('strategy', 'planar')
        slice_angle = params.get('sliceAngle', 0.0)

        try:
            # Load geometry
            mesh = GeometryLoader.load(geometry_path)

            # ── Centre the mesh at origin using trimesh (library-backed) ─────
            # The frontend centres geometry at import time (centerOnPlate).
            # We replicate the same logic here: centre XY at origin, lift bottom to Z=0.
            # The frontend handles positioning via its scene graph — the backend always
            # slices at origin and does NOT apply part_position.
            import trimesh as _tm
            from openaxis.core.geometry import GeometryConverter
            _tmesh = GeometryConverter.compas_to_trimesh(mesh)
            bounds = _tmesh.bounds  # [[xmin,ymin,zmin],[xmax,ymax,zmax]]
            cx = (bounds[0][0] + bounds[1][0]) / 2.0
            cy = (bounds[0][1] + bounds[1][1]) / 2.0
            lift_z = -bounds[0][2]
            _tmesh.apply_translation([-cx, -cy, lift_z])
            # Convert back to COMPAS mesh
            mesh = GeometryConverter.trimesh_to_compas(_tmesh)

            # Create slicer via factory (Sprint 7)
            pattern_map = {
                'lines': InfillPattern.LINES,
                'grid': InfillPattern.GRID,
                'triangles': InfillPattern.TRIANGLES,
                'hexagons': InfillPattern.HEXAGONS,
                'triangle_grid': InfillPattern.TRIANGLES,
                'radial': InfillPattern.CONCENTRIC,
                'offset': InfillPattern.CONCENTRIC,
                'hexgrid': InfillPattern.HEXAGONS,
                'medial': InfillPattern.LINES,
                'zigzag': InfillPattern.ZIGZAG,
            }

            if strategy == 'planar' or strategy not in SLICER_REGISTRY:
                # Full-featured planar slicer with all Sprint 5 advanced params
                slicer = PlanarSlicer(
                    layer_height=layer_height,
                    extrusion_width=extrusion_width,
                    wall_count=wall_count,
                    infill_density=infill_density,
                    infill_pattern=pattern_map.get(infill_pattern, InfillPattern.LINES),
                    support_enabled=support_enabled,
                    wall_width=wall_width,
                    print_speed=print_speed,
                    travel_speed=travel_speed,
                    seam_mode=seam_mode,
                    seam_shape=seam_shape,
                    seam_angle=seam_angle,
                    lead_in_distance=lead_in_distance,
                    lead_in_angle=lead_in_angle,
                    lead_out_distance=lead_out_distance,
                    lead_out_angle=lead_out_angle,
                    infill_pattern_name=infill_pattern,
                )
            elif strategy == 'angled':
                slicer = get_slicer(
                    strategy,
                    layer_height=layer_height,
                    extrusion_width=extrusion_width,
                    slice_angle=slice_angle,
                    wall_count=wall_count,
                    infill_density=infill_density,
                )
            elif strategy == 'radial':
                slicer = get_slicer(
                    strategy,
                    layer_height=layer_height,
                    extrusion_width=extrusion_width,
                )
            elif strategy == 'curve':
                slicer = get_slicer(
                    strategy,
                    layer_height=layer_height,
                    extrusion_width=extrusion_width,
                )
            elif strategy == 'revolved':
                slicer = get_slicer(
                    strategy,
                    layer_height=layer_height,
                    extrusion_width=extrusion_width,
                )
            else:
                # Fallback — use factory with basic params
                slicer = get_slicer(
                    strategy,
                    layer_height=layer_height,
                    extrusion_width=extrusion_width,
                )

            # Generate toolpath
            toolpath = slicer.slice(mesh)

            # Debug: log first segment's first few points
            if toolpath.segments:
                seg0 = toolpath.segments[0]
                pts = [(float(p.x), float(p.y), float(p.z)) for p in seg0.points[:3]]
                logger.debug("toolpath_first_segment", type=str(seg0.type), points=pts)
                logger.debug("toolpath_summary", segments=len(toolpath.segments), layers=toolpath.total_layers)

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
                'direction': getattr(segment, 'direction', 'cw'),
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
