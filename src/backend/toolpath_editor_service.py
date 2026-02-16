"""
Toolpath editor service for OpenAxis backend.

Provides in-memory editing operations on toolpath data: speed overrides,
extrusion rate changes, segment deletion, reversal, delays, and splitting.

Toolpath data format:
    {
        "segments": [
            {
                "type": str,           # e.g. "perimeter", "infill", "travel"
                "layer": int,          # layer number
                "points": [[x,y,z]],   # list of [x, y, z] coordinates
                "speed": float,        # mm/s
                "extrusionRate": float, # extrusion multiplier / flow rate
                "direction": str,      # e.g. "forward", "reverse"
                ...                    # additional metadata allowed
            },
            ...
        ],
        ...  # other top-level keys preserved as-is
    }

Each editing method mutates the supplied toolpath_data dict in place and
returns it so callers can chain or inspect the result directly.
"""

import copy
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ToolpathEditorService:
    """Service for interactive toolpath editing operations.

    All methods operate on toolpath_data dicts whose ``segments`` key
    contains a list of segment dicts (see module docstring for format).
    Methods mutate the dict in place *and* return it for convenience.
    """

    # ------------------------------------------------------------------
    # Speed override
    # ------------------------------------------------------------------

    def apply_speed_override(
        self,
        toolpath_data: Dict[str, Any],
        segment_indices: List[int],
        new_speed: float,
    ) -> Dict[str, Any]:
        """Set the speed of selected segments to *new_speed* (mm/s).

        Parameters
        ----------
        toolpath_data : dict
            Toolpath dict with a ``segments`` list.
        segment_indices : list[int]
            Zero-based indices of segments to modify.
        new_speed : float
            New speed value in mm/s.  Must be positive.

        Returns
        -------
        dict
            The mutated *toolpath_data*.
        """
        if new_speed <= 0:
            logger.warning("apply_speed_override called with non-positive speed %.4f; clamping to 0.1", new_speed)
            new_speed = 0.1

        segments = toolpath_data.get("segments", [])
        applied = 0

        for idx in segment_indices:
            if 0 <= idx < len(segments):
                segments[idx]["speed"] = new_speed
                applied += 1
            else:
                logger.warning("apply_speed_override: segment index %d out of range (0..%d)", idx, len(segments) - 1)

        logger.info(
            "apply_speed_override: set speed=%.2f mm/s on %d/%d requested segments",
            new_speed, applied, len(segment_indices),
        )
        return toolpath_data

    # ------------------------------------------------------------------
    # Deposition / extrusion rate override
    # ------------------------------------------------------------------

    def apply_deposition_override(
        self,
        toolpath_data: Dict[str, Any],
        segment_indices: List[int],
        new_rate: float,
    ) -> Dict[str, Any]:
        """Set the extrusion rate of selected segments to *new_rate*.

        Parameters
        ----------
        toolpath_data : dict
            Toolpath dict with a ``segments`` list.
        segment_indices : list[int]
            Zero-based indices of segments to modify.
        new_rate : float
            New extrusion rate.  Must be non-negative.

        Returns
        -------
        dict
            The mutated *toolpath_data*.
        """
        if new_rate < 0:
            logger.warning("apply_deposition_override called with negative rate %.4f; clamping to 0.0", new_rate)
            new_rate = 0.0

        segments = toolpath_data.get("segments", [])
        applied = 0

        for idx in segment_indices:
            if 0 <= idx < len(segments):
                segments[idx]["extrusionRate"] = new_rate
                applied += 1
            else:
                logger.warning("apply_deposition_override: segment index %d out of range (0..%d)", idx, len(segments) - 1)

        logger.info(
            "apply_deposition_override: set extrusionRate=%.4f on %d/%d requested segments",
            new_rate, applied, len(segment_indices),
        )
        return toolpath_data

    # ------------------------------------------------------------------
    # Delete segments
    # ------------------------------------------------------------------

    def delete_segments(
        self,
        toolpath_data: Dict[str, Any],
        segment_indices: List[int],
    ) -> Dict[str, Any]:
        """Remove segments at the given indices.

        Indices are evaluated against the current segment list.  Duplicate
        indices are ignored (a segment can only be deleted once).

        Parameters
        ----------
        toolpath_data : dict
            Toolpath dict with a ``segments`` list.
        segment_indices : list[int]
            Zero-based indices of segments to remove.

        Returns
        -------
        dict
            The mutated *toolpath_data* with the specified segments removed.
        """
        segments = toolpath_data.get("segments", [])
        total = len(segments)

        # Deduplicate and filter out-of-range indices
        valid_indices = sorted({idx for idx in segment_indices if 0 <= idx < total}, reverse=True)
        invalid_count = len(segment_indices) - len(valid_indices)

        if invalid_count > 0:
            logger.warning("delete_segments: %d index(es) out of range (0..%d)", invalid_count, total - 1)

        # Delete from highest index first so lower indices remain valid
        for idx in valid_indices:
            del segments[idx]

        logger.info(
            "delete_segments: removed %d segment(s), %d remaining",
            len(valid_indices), len(segments),
        )
        return toolpath_data

    # ------------------------------------------------------------------
    # Reverse segments
    # ------------------------------------------------------------------

    def reverse_segments(
        self,
        toolpath_data: Dict[str, Any],
        segment_indices: List[int],
    ) -> Dict[str, Any]:
        """Reverse the point order within selected segments.

        The ``direction`` metadata is also toggled between ``"forward"``
        and ``"reverse"`` to reflect the change.

        Parameters
        ----------
        toolpath_data : dict
            Toolpath dict with a ``segments`` list.
        segment_indices : list[int]
            Zero-based indices of segments whose points should be reversed.

        Returns
        -------
        dict
            The mutated *toolpath_data*.
        """
        segments = toolpath_data.get("segments", [])
        applied = 0

        for idx in segment_indices:
            if 0 <= idx < len(segments):
                seg = segments[idx]
                seg["points"] = list(reversed(seg.get("points", [])))
                # Toggle direction metadata
                current_dir = seg.get("direction", "forward")
                seg["direction"] = "reverse" if current_dir == "forward" else "forward"
                applied += 1
            else:
                logger.warning("reverse_segments: segment index %d out of range (0..%d)", idx, len(segments) - 1)

        logger.info(
            "reverse_segments: reversed %d/%d requested segments",
            applied, len(segment_indices),
        )
        return toolpath_data

    # ------------------------------------------------------------------
    # Add delay / dwell
    # ------------------------------------------------------------------

    def add_delay(
        self,
        toolpath_data: Dict[str, Any],
        segment_index: int,
        delay_seconds: float,
    ) -> Dict[str, Any]:
        """Attach a dwell/delay to a segment's metadata.

        The delay is stored under ``segment["delay"]`` in seconds.  If the
        segment already has a delay, the new value replaces it.

        Parameters
        ----------
        toolpath_data : dict
            Toolpath dict with a ``segments`` list.
        segment_index : int
            Zero-based index of the segment to add a delay to.
        delay_seconds : float
            Dwell time in seconds.  Must be non-negative.

        Returns
        -------
        dict
            The mutated *toolpath_data*.
        """
        if delay_seconds < 0:
            logger.warning("add_delay called with negative delay %.4f; clamping to 0.0", delay_seconds)
            delay_seconds = 0.0

        segments = toolpath_data.get("segments", [])

        if not (0 <= segment_index < len(segments)):
            logger.warning("add_delay: segment index %d out of range (0..%d)", segment_index, len(segments) - 1)
            return toolpath_data

        segments[segment_index]["delay"] = delay_seconds
        logger.info(
            "add_delay: set %.3fs delay on segment %d",
            delay_seconds, segment_index,
        )
        return toolpath_data

    # ------------------------------------------------------------------
    # Split segment
    # ------------------------------------------------------------------

    def split_segment(
        self,
        toolpath_data: Dict[str, Any],
        segment_index: int,
        split_point_index: int,
    ) -> Dict[str, Any]:
        """Split a segment into two at *split_point_index*.

        The point at *split_point_index* becomes the last point of the
        first half **and** the first point of the second half (shared
        boundary point).  All other segment metadata (type, layer, speed,
        extrusionRate, direction) is copied to the new segment.

        Parameters
        ----------
        toolpath_data : dict
            Toolpath dict with a ``segments`` list.
        segment_index : int
            Zero-based index of the segment to split.
        split_point_index : int
            Zero-based index of the point within the segment at which to
            split.  Must be >= 1 and < len(points) - 1 so that both halves
            contain at least two points.

        Returns
        -------
        dict
            The mutated *toolpath_data* with the original segment replaced
            by two consecutive segments.
        """
        segments = toolpath_data.get("segments", [])

        if not (0 <= segment_index < len(segments)):
            logger.warning("split_segment: segment index %d out of range (0..%d)", segment_index, len(segments) - 1)
            return toolpath_data

        seg = segments[segment_index]
        points = seg.get("points", [])

        if split_point_index < 1 or split_point_index >= len(points) - 1:
            logger.warning(
                "split_segment: split_point_index %d out of valid range (1..%d) for segment with %d points",
                split_point_index, len(points) - 2, len(points),
            )
            return toolpath_data

        # Build two new segments sharing the split point
        first_half_points = points[: split_point_index + 1]
        second_half_points = points[split_point_index:]

        # Copy metadata from the original segment (excluding points)
        base_meta = {k: v for k, v in seg.items() if k != "points"}

        first_seg = {**copy.deepcopy(base_meta), "points": first_half_points}
        second_seg = {**copy.deepcopy(base_meta), "points": second_half_points}

        # Replace the original segment with the two halves
        segments[segment_index: segment_index + 1] = [first_seg, second_seg]

        logger.info(
            "split_segment: split segment %d at point %d into segments of %d and %d points",
            segment_index, split_point_index,
            len(first_half_points), len(second_half_points),
        )
        return toolpath_data
