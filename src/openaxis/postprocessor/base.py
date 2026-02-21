"""
PostProcessorBase — Abstract base class for all post processors.

Provides an event-hook architecture where users can inject custom code
at key points in the program (start, end, layer change, process on/off,
before/after each point).

Template variables available in event hooks:
  {layerIndex}  — current layer number (0-based)
  {x}, {y}, {z} — current point position (mm)
  {rx}, {ry}, {rz} — current point orientation (degrees, if available)
  {speed}       — feed speed for this segment (mm/s or mm/min depending on format)
  {depositionFactor} — extrusion/deposition multiplier
  {segmentType} — 'perimeter', 'infill', 'travel', etc.
  {time}        — estimated timestamp (seconds from start)
  {toolName}    — tool center point name
"""

import datetime
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class EventHooks:
    """
    Customizable code snippets injected at event points.
    Each string may contain template variables like {x}, {y}, {z}, {speed}.
    """
    program_start: str = ""
    program_end: str = ""
    layer_start: str = ""
    layer_end: str = ""
    process_on: str = ""     # e.g., arc on, extrusion start
    process_off: str = ""    # e.g., arc off, extrusion stop
    before_point: str = ""   # injected before each motion command
    after_point: str = ""    # injected after each motion command
    tool_change: str = ""    # tool change event
    retract: str = ""        # retraction event
    prime: str = ""          # priming event

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'EventHooks':
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in valid_fields})


@dataclass
class PostProcessorConfig:
    """Configuration for a post processor instance."""
    format_name: str = "gcode"           # 'rapid', 'krl', 'fanuc', 'gcode'
    file_extension: str = ".gcode"
    line_ending: str = "\n"              # '\n' or '\r\n'

    # Motion parameters
    default_speed: float = 1000.0        # mm/min for G-code, mm/s for robot
    travel_speed: float = 5000.0         # rapid move speed
    approach_speed: float = 500.0        # approach/retract speed

    # Zone / blending
    zone_data: str = "z5"               # RAPID: fine, z0, z1, z5, z10, z50, z100, z200
    blending: float = 5.0               # KRL: C_DIS mm / Fanuc: CNT

    # Tool
    tool_name: str = "tool0"
    work_object: str = "wobj0"

    # Units
    position_units: str = "mm"
    speed_units: str = "mm/min"         # 'mm/min' or 'mm/s'

    # Event hooks
    hooks: EventHooks = field(default_factory=EventHooks)

    # Metadata
    program_name: str = "OpenAxisProgram"
    comment_prefix: str = "; "

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'PostProcessorConfig':
        hooks_data = d.pop('hooks', {})
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        config = cls(**{k: v for k, v in d.items() if k in valid_fields})
        if hooks_data:
            config.hooks = EventHooks.from_dict(hooks_data)
        return config


@dataclass
class PointData:
    """Data for a single toolpath point, passed to event hooks."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    rz: float = 0.0
    speed: float = 1000.0
    deposition_factor: float = 1.0
    segment_type: str = "perimeter"
    layer_index: int = 0
    point_index: int = 0
    time_estimate: float = 0.0
    is_first_in_segment: bool = False
    is_last_in_segment: bool = False
    # Slicing plane normal in slicer frame (Z-up mm). [0,0,1] for planar slicing.
    # This is the "up" direction of the print layer — the tool Z-axis must align
    # with this normal so the robot approaches perpendicular to the print plane.
    # IMPORTANT: Currently hardcoded to [0,0,1] for all planar slicing operations.
    # This assumption is only valid when the robot base frame Z-axis is parallel to
    # the build plate normal (i.e. robot standing on a flat floor, build plate flat).
    # For tilted build plates, external-axis positioners, or non-planar slicers the
    # normal must come from the actual slicer plane geometry. Do NOT change the
    # IK target orientation without updating this field to carry the real normal.
    layer_normal: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 1.0))

    def template_vars(self, tool_name: str = "tool0") -> Dict[str, Any]:
        return {
            'x': f"{self.x:.3f}",
            'y': f"{self.y:.3f}",
            'z': f"{self.z:.3f}",
            'rx': f"{self.rx:.3f}",
            'ry': f"{self.ry:.3f}",
            'rz': f"{self.rz:.3f}",
            'speed': f"{self.speed:.1f}",
            'depositionFactor': f"{self.deposition_factor:.4f}",
            'segmentType': self.segment_type,
            'layerIndex': str(self.layer_index),
            'time': f"{self.time_estimate:.1f}",
            'toolName': tool_name,
            'pointIndex': str(self.point_index),
        }


class PostProcessorBase(ABC):
    """
    Abstract base class for post processors.

    Subclasses implement format-specific methods:
    - header() / footer()
    - linear_move() / rapid_move()
    - process_on() / process_off()
    - comment()
    """

    def __init__(self, config: Optional[PostProcessorConfig] = None):
        self.config = config or PostProcessorConfig()
        self._lines: List[str] = []
        self._current_layer: int = -1
        self._time_estimate: float = 0.0

    @property
    def format_name(self) -> str:
        return self.config.format_name

    @property
    def file_extension(self) -> str:
        return self.config.file_extension

    # ── Abstract methods (must be implemented by subclasses) ───────────

    @abstractmethod
    def header(self, toolpath_data: Dict[str, Any]) -> List[str]:
        """Generate program header lines."""
        ...

    @abstractmethod
    def footer(self) -> List[str]:
        """Generate program footer lines."""
        ...

    @abstractmethod
    def linear_move(self, pt: PointData) -> List[str]:
        """Generate a linear (process) move command."""
        ...

    @abstractmethod
    def rapid_move(self, pt: PointData) -> List[str]:
        """Generate a rapid (travel) move command."""
        ...

    @abstractmethod
    def comment(self, text: str) -> str:
        """Format a comment line."""
        ...

    # ── Optional overrides ────────────────────────────────────────────

    def process_on_code(self, pt: PointData) -> List[str]:
        """Code to turn on deposition/welding process."""
        return []

    def process_off_code(self, pt: PointData) -> List[str]:
        """Code to turn off deposition/welding process."""
        return []

    def layer_change_code(self, layer: int) -> List[str]:
        """Code injected at layer transitions."""
        return [self.comment(f"Layer {layer}")]

    # ── Normal → frame conversion ────────────────────────────────────

    @staticmethod
    def normal_to_zyx_euler(normal: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Convert a slicing plane normal vector to ZYX Euler angles (degrees).

        The normal defines the tool Z-axis direction (approach direction). We build
        a rotation matrix with Z = -normal (tool pointing into the surface), then
        extract ZYX Euler angles (A, B, C for KUKA; W, P, R for Fanuc; rz, ry, rx
        for the generic representation used in RAPID quaternion conversion).

        HARDCODED CAVEAT: For planar Z-up slicing, normal = [0,0,1] always, giving
        A=0, B=180, C=0 (or equivalent). This is hardcoded and only correct when:
          1. The build plate is horizontal (parallel to the robot base XY plane)
          2. The robot base Z-axis is vertical (robot standing on a flat floor)
        For tilted build plates, positioners, or non-planar slicers the normal must
        come from the actual slicer plane geometry. Do NOT assume [0,0,1] in those cases.

        Returns: (rz_deg, ry_deg, rx_deg) — ZYX Euler angles in degrees.
        Equivalent to KUKA A, B, C convention.

        Reference: Siciliano et al., "Robotics: Modelling, Planning and Control",
        Springer 2010, §2.7 (Euler angle extraction from rotation matrix).
        """
        nx, ny, nz = normal
        norm = math.sqrt(nx * nx + ny * ny + nz * nz)
        if norm < 1e-9:
            return (0.0, 180.0, 0.0)  # Degenerate — default tool-down
        nx, ny, nz = nx / norm, ny / norm, nz / norm

        # Tool Z-axis = -normal (tool approaches from above)
        tz_x, tz_y, tz_z = -nx, -ny, -nz

        # Pick an arbitrary X that is not collinear with tool_z
        if abs(tz_x) < 0.9:
            arb = (1.0, 0.0, 0.0)
        else:
            arb = (0.0, 1.0, 0.0)

        # tool_y = tool_z × arb  (normalized)
        ty_x = tz_y * arb[2] - tz_z * arb[1]
        ty_y = tz_z * arb[0] - tz_x * arb[2]
        ty_z = tz_x * arb[1] - tz_y * arb[0]
        ty_len = math.sqrt(ty_x * ty_x + ty_y * ty_y + ty_z * ty_z)
        ty_x, ty_y, ty_z = ty_x / ty_len, ty_y / ty_len, ty_z / ty_len

        # tool_x = tool_y × tool_z  (normalized)
        tx_x = ty_y * tz_z - ty_z * tz_y
        tx_y = ty_z * tz_x - ty_x * tz_z
        tx_z = ty_x * tz_y - ty_y * tz_x

        # Rotation matrix R = [tool_x | tool_y | tool_z] (columns)
        # R[row][col]: R[0][0]=tx_x, R[1][0]=tx_y, R[2][0]=tx_z, etc.
        r00, r10, r20 = tx_x, tx_y, tx_z
        r01, r11, r21 = ty_x, ty_y, ty_z
        r02, r12, r22 = tz_x, tz_y, tz_z

        # ZYX Euler extraction: rz (A), ry (B), rx (C)
        # Reference: Siciliano et al., §2.7
        ry = math.atan2(-r20, math.sqrt(r00 * r00 + r10 * r10))
        if abs(math.cos(ry)) > 1e-6:
            rz = math.atan2(r10, r00)
            rx = math.atan2(r21, r22)
        else:
            # Gimbal lock
            rz = math.atan2(-r01, r11)
            rx = 0.0

        return (math.degrees(rz), math.degrees(ry), math.degrees(rx))

    # ── Hook expansion ────────────────────────────────────────────────

    def _expand_hook(self, hook_template: str, pt: Optional[PointData] = None) -> List[str]:
        """Expand template variables in a hook string."""
        if not hook_template.strip():
            return []
        template_vars = pt.template_vars(self.config.tool_name) if pt else {}
        try:
            expanded = hook_template.format(**template_vars)
        except (KeyError, IndexError):
            expanded = hook_template  # Leave unresolved variables as-is
        return [line for line in expanded.split('\n') if line.strip()]

    # ── Main generation pipeline ──────────────────────────────────────

    def generate(self, toolpath_data: Dict[str, Any]) -> str:
        """
        Generate the complete post-processed program.

        Parameters:
            toolpath_data: Dict with 'segments', 'layerHeight', 'totalLayers', etc.

        Returns:
            Complete program as a string.
        """
        self._lines = []
        self._current_layer = -1
        self._time_estimate = 0.0

        segments = toolpath_data.get('segments', [])
        if not segments:
            return ""

        # Header
        self._lines.extend(self.header(toolpath_data))
        self._lines.extend(self._expand_hook(self.config.hooks.program_start))

        # Process segments
        global_point_idx = 0
        prev_was_process = False

        for seg_idx, seg in enumerate(segments):
            seg_type = seg.get('type', 'perimeter')
            seg_layer = seg.get('layer', 0)
            seg_speed = seg.get('speed', self.config.default_speed)
            points = seg.get('points', [])
            extrusion_rate = seg.get('extrusionRate', 1.0)
            # Slicing plane normal for this segment.
            # HARDCODED CAVEAT: planar slicer always produces [0,0,1] (world Z-up).
            # This is only valid when the build plate is flat and the robot base Z
            # is parallel to the build plate normal. For tilted build plates, external
            # axes (positioners), angled slicing, or any non-planar strategy this
            # value must come from the slicer's own plane geometry — not assumed.
            # Future work: non-planar slicers must populate seg['normal'] explicitly.
            seg_normal: Tuple[float, float, float] = tuple(seg.get('normal', [0.0, 0.0, 1.0]))  # type: ignore[assignment]

            if not points:
                continue

            # Layer change
            if seg_layer != self._current_layer:
                if self._current_layer >= 0:
                    self._lines.extend(self._expand_hook(self.config.hooks.layer_end))
                self._current_layer = seg_layer
                self._lines.extend(self.layer_change_code(seg_layer))
                self._lines.extend(self._expand_hook(self.config.hooks.layer_start))

            is_travel = seg_type.lower() in ('travel', 'move', 'rapid')

            # Process on/off transitions
            if is_travel and prev_was_process:
                self._lines.extend(self.process_off_code(PointData()))
                self._lines.extend(self._expand_hook(self.config.hooks.process_off))
                prev_was_process = False
            elif not is_travel and not prev_was_process:
                first_pt = PointData(
                    x=points[0][0], y=points[0][1],
                    z=points[0][2] if len(points[0]) > 2 else 0,
                    speed=seg_speed,
                    segment_type=seg_type,
                    layer_index=seg_layer,
                    layer_normal=seg_normal,
                )
                self._lines.extend(self.process_on_code(first_pt))
                self._lines.extend(self._expand_hook(self.config.hooks.process_on, first_pt))
                prev_was_process = True

            # Segment type comment
            self._lines.append(self.comment(f"{seg_type.capitalize()} segment"))

            # Points
            for pi, pt_raw in enumerate(points):
                pt = PointData(
                    x=pt_raw[0],
                    y=pt_raw[1],
                    z=pt_raw[2] if len(pt_raw) > 2 else 0,
                    speed=seg_speed,
                    deposition_factor=extrusion_rate if not is_travel else 0,
                    segment_type=seg_type,
                    layer_index=seg_layer,
                    point_index=global_point_idx,
                    time_estimate=self._time_estimate,
                    is_first_in_segment=(pi == 0),
                    is_last_in_segment=(pi == len(points) - 1),
                    layer_normal=seg_normal,
                )

                # Before-point hook
                self._lines.extend(self._expand_hook(self.config.hooks.before_point, pt))

                # Motion command
                if is_travel:
                    self._lines.extend(self.rapid_move(pt))
                else:
                    if pi == 0:
                        # First point of segment: rapid approach
                        self._lines.extend(self.rapid_move(pt))
                    else:
                        self._lines.extend(self.linear_move(pt))

                # After-point hook
                self._lines.extend(self._expand_hook(self.config.hooks.after_point, pt))

                global_point_idx += 1

        # Final process off
        if prev_was_process:
            self._lines.extend(self.process_off_code(PointData()))
            self._lines.extend(self._expand_hook(self.config.hooks.process_off))

        # Layer end
        if self._current_layer >= 0:
            self._lines.extend(self._expand_hook(self.config.hooks.layer_end))

        # Program end hook + footer
        self._lines.extend(self._expand_hook(self.config.hooks.program_end))
        self._lines.extend(self.footer())

        return self.config.line_ending.join(self._lines)
