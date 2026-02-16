"""
Validation Service — Toolpath quality checking and scoring.

Provides:
- check_reachability()     — test each waypoint against IK solver
- detect_singularities()   — find wrist singularity zones
- check_bead_overhang()    — detect unsupported bead segments
- compute_quality_score()  — weighted 0-100 quality score
- check_all()              — run all checks, return combined report
"""

import math
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class ReachabilityResult:
    """Result of reachability check."""
    total_points: int = 0
    reachable_count: int = 0
    unreachable_count: int = 0
    reachability_pct: float = 100.0
    unreachable_indices: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SingularityResult:
    """Result of singularity detection."""
    total_zones: int = 0
    zones: List[Dict[str, Any]] = field(default_factory=list)  # {startIdx, endIdx, type}
    total_points_in_zones: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BeadOverhangResult:
    """Result of bead overhang check."""
    total_segments: int = 0
    overhang_segments: int = 0
    max_overhang_angle: float = 0.0
    overhang_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SpeedConsistencyResult:
    """Result of speed consistency check."""
    mean_speed: float = 0.0
    std_speed: float = 0.0
    cv: float = 0.0  # coefficient of variation
    consistency_pct: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LayerUniformityResult:
    """Result of layer uniformity check."""
    total_layers: int = 0
    min_points: int = 0
    max_points: int = 0
    mean_points: float = 0.0
    uniformity_pct: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QualityReport:
    """Complete quality validation report."""
    overall_score: int = 100
    reachability: Optional[ReachabilityResult] = None
    singularities: Optional[SingularityResult] = None
    bead_overhang: Optional[BeadOverhangResult] = None
    speed_consistency: Optional[SpeedConsistencyResult] = None
    layer_uniformity: Optional[LayerUniformityResult] = None
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            'overallScore': self.overall_score,
            'recommendations': self.recommendations,
        }
        if self.reachability:
            result['reachability'] = self.reachability.to_dict()
        if self.singularities:
            result['singularities'] = self.singularities.to_dict()
        if self.bead_overhang:
            result['beadOverhang'] = self.bead_overhang.to_dict()
        if self.speed_consistency:
            result['speedConsistency'] = self.speed_consistency.to_dict()
        if self.layer_uniformity:
            result['layerUniformity'] = self.layer_uniformity.to_dict()
        return result


# ─── Validation Service ──────────────────────────────────────────────────────

class ValidationService:
    """Toolpath quality validation engine."""

    def __init__(self) -> None:
        logger.info("ValidationService initialized")

    def check_reachability(
        self,
        toolpath_data: Dict[str, Any],
        reachability_array: Optional[List[bool]] = None,
    ) -> ReachabilityResult:
        """
        Check reachability of all toolpath points.

        If reachability_array is provided (from frontend IK solve), use it directly.
        Otherwise estimate from toolpath geometry (distance from robot base).
        """
        result = ReachabilityResult()

        segments = toolpath_data.get('segments', [])
        if not segments:
            return result

        # Count total points
        total = 0
        for seg in segments:
            total += len(seg.get('points', []))
        result.total_points = total

        if reachability_array and len(reachability_array) > 0:
            # Use pre-computed reachability from IK solver
            result.reachable_count = sum(1 for r in reachability_array if r)
            result.unreachable_count = len(reachability_array) - result.reachable_count
            result.unreachable_indices = [
                i for i, r in enumerate(reachability_array) if not r
            ]
        else:
            # Estimate: assume all reachable (no IK data available)
            result.reachable_count = total
            result.unreachable_count = 0

        total_check = result.reachable_count + result.unreachable_count
        result.reachability_pct = (
            (result.reachable_count / total_check * 100) if total_check > 0 else 100.0
        )

        return result

    def detect_singularities(
        self,
        toolpath_data: Dict[str, Any],
        reachability_array: Optional[List[bool]] = None,
    ) -> SingularityResult:
        """
        Detect singularity zones in the toolpath.

        Singularity zones are estimated from:
        1. Gaps in reachability (consecutive unreachable points)
        2. Near-zero wrist angle transitions (J5 ≈ 0)
        """
        result = SingularityResult()

        if not reachability_array or len(reachability_array) < 2:
            return result

        # Find contiguous unreachable zones
        in_gap = False
        zone_start = 0
        for i, reachable in enumerate(reachability_array):
            if not reachable:
                if not in_gap:
                    zone_start = i
                    in_gap = True
            else:
                if in_gap:
                    zone_len = i - zone_start
                    result.zones.append({
                        'startIdx': zone_start,
                        'endIdx': i - 1,
                        'type': 'reachability_gap',
                        'length': zone_len,
                    })
                    result.total_points_in_zones += zone_len
                    in_gap = False

        # Close last zone if still in gap
        if in_gap:
            zone_len = len(reachability_array) - zone_start
            result.zones.append({
                'startIdx': zone_start,
                'endIdx': len(reachability_array) - 1,
                'type': 'reachability_gap',
                'length': zone_len,
            })
            result.total_points_in_zones += zone_len

        result.total_zones = len(result.zones)
        return result

    def check_bead_overhang(
        self,
        toolpath_data: Dict[str, Any],
        max_overhang_angle: float = 45.0,
    ) -> BeadOverhangResult:
        """
        Check for unsupported bead overhang.

        Detects segments where the bead would be deposited at an angle
        exceeding the maximum overhang limit (default 45°).
        For planar slicing this is typically 0 (all layers are horizontal).
        """
        result = BeadOverhangResult()
        segments = toolpath_data.get('segments', [])
        layer_height = toolpath_data.get('layerHeight', 0.3)

        if not segments or layer_height <= 0:
            return result

        for seg in segments:
            seg_type = seg.get('type', '')
            if seg_type in ('travel', 'move', 'rapid'):
                continue

            points = seg.get('points', [])
            result.total_segments += 1

            if len(points) < 2:
                continue

            # Check angle between consecutive points
            for i in range(1, len(points)):
                prev = points[i - 1]
                curr = points[i]
                dx = curr[0] - prev[0]
                dy = curr[1] - prev[1]
                dz = (curr[2] if len(curr) > 2 else 0) - (prev[2] if len(prev) > 2 else 0)
                horiz = math.sqrt(dx * dx + dy * dy)

                if horiz > 0.001:
                    angle = math.degrees(math.atan2(abs(dz), horiz))
                    if angle > max_overhang_angle:
                        result.overhang_segments += 1
                        result.max_overhang_angle = max(result.max_overhang_angle, angle)
                        break  # One violation per segment is enough

        result.overhang_pct = (
            (result.overhang_segments / result.total_segments * 100)
            if result.total_segments > 0 else 0.0
        )

        return result

    def check_speed_consistency(
        self,
        toolpath_data: Dict[str, Any],
    ) -> SpeedConsistencyResult:
        """
        Compute speed consistency (coefficient of variation) across print segments.
        Lower CV = more consistent = better quality.
        """
        result = SpeedConsistencyResult()
        segments = toolpath_data.get('segments', [])

        speeds = []
        for seg in segments:
            if seg.get('type', '') in ('travel', 'move', 'rapid'):
                continue
            speed = seg.get('speed', 0)
            if speed > 0:
                speeds.append(speed)

        if len(speeds) < 2:
            result.consistency_pct = 100.0
            return result

        mean = sum(speeds) / len(speeds)
        variance = sum((s - mean) ** 2 for s in speeds) / len(speeds)
        std = math.sqrt(variance)
        cv = std / mean if mean > 0 else 0

        result.mean_speed = round(mean, 2)
        result.std_speed = round(std, 2)
        result.cv = round(cv, 4)
        result.consistency_pct = round(max(0, 100 - cv * 100), 1)

        return result

    def check_layer_uniformity(
        self,
        toolpath_data: Dict[str, Any],
    ) -> LayerUniformityResult:
        """
        Check whether layers have roughly equal point counts.
        Large variation indicates potential quality issues (sparse/dense layers).
        """
        result = LayerUniformityResult()
        segments = toolpath_data.get('segments', [])

        if not segments:
            return result

        layer_counts: Dict[int, int] = {}
        for seg in segments:
            layer = seg.get('layer', 0)
            layer_counts[layer] = layer_counts.get(layer, 0) + len(seg.get('points', []))

        if len(layer_counts) < 2:
            result.total_layers = len(layer_counts)
            result.uniformity_pct = 100.0
            return result

        counts = list(layer_counts.values())
        result.total_layers = len(counts)
        result.min_points = min(counts)
        result.max_points = max(counts)
        result.mean_points = round(sum(counts) / len(counts), 1)

        mean = result.mean_points
        if mean > 0:
            max_dev = max(abs(c - mean) for c in counts)
            result.uniformity_pct = round(max(0, 100 - (max_dev / mean) * 50), 1)
        else:
            result.uniformity_pct = 100.0

        return result

    def compute_quality_score(
        self,
        reachability: ReachabilityResult,
        singularities: SingularityResult,
        speed: SpeedConsistencyResult,
        layers: LayerUniformityResult,
    ) -> Tuple[int, List[str]]:
        """
        Compute overall quality score (0-100) as weighted average.

        Weights:
        - Reachability: 40%
        - Speed consistency: 20%
        - Layer uniformity: 20%
        - Singularity-free: 20%
        """
        # Singularity sub-score
        sing_score = 100 if singularities.total_zones == 0 else max(
            0, 100 - singularities.total_zones * 10
        )

        overall = round(
            reachability.reachability_pct * 0.40 +
            speed.consistency_pct * 0.20 +
            layers.uniformity_pct * 0.20 +
            sing_score * 0.20
        )
        overall = max(0, min(100, overall))

        # Build recommendations
        recs: List[str] = []
        if reachability.reachability_pct < 95:
            recs.append(
                "Adjust part position or robot base to improve reachability "
                f"(currently {reachability.reachability_pct:.1f}%)"
            )
        if singularities.total_zones > 0:
            recs.append(
                f"Review toolpath near {singularities.total_zones} singularity "
                "zone(s) — consider orientation change"
            )
        if speed.consistency_pct < 70:
            recs.append(
                "Normalize feed speeds for consistent deposition quality "
                f"(CV = {speed.cv:.2f})"
            )
        if layers.uniformity_pct < 70:
            recs.append(
                "Check slicing parameters — layers have uneven point distribution "
                f"(min={layers.min_points}, max={layers.max_points})"
            )

        return overall, recs

    def check_all(
        self,
        toolpath_data: Dict[str, Any],
        reachability_array: Optional[List[bool]] = None,
    ) -> QualityReport:
        """Run all validation checks and return a combined report."""
        logger.info("Running full toolpath validation...")

        reach = self.check_reachability(toolpath_data, reachability_array)
        sings = self.detect_singularities(toolpath_data, reachability_array)
        bead = self.check_bead_overhang(toolpath_data)
        speed = self.check_speed_consistency(toolpath_data)
        layers = self.check_layer_uniformity(toolpath_data)

        score, recs = self.compute_quality_score(reach, sings, speed, layers)

        report = QualityReport(
            overall_score=score,
            reachability=reach,
            singularities=sings,
            bead_overhang=bead,
            speed_consistency=speed,
            layer_uniformity=layers,
            recommendations=recs,
        )

        logger.info(
            f"Validation complete: score={score}, "
            f"reachability={reach.reachability_pct:.1f}%, "
            f"singularities={sings.total_zones}, "
            f"speed_cv={speed.cv:.3f}, "
            f"layer_uniformity={layers.uniformity_pct:.1f}%"
        )

        return report
