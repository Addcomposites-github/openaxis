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
