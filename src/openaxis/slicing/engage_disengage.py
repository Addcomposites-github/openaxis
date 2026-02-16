"""
Engage/Disengage — Lead-in, lead-out, and retraction for toolpath segments.

Provides:
- add_lead_in()   — Approach move before deposition starts
- add_lead_out()  — Exit move after deposition ends
- add_retract()   — Vertical retraction between travel moves
"""

import math
from typing import List, Tuple, Optional

Point3D = Tuple[float, float, float]
Polyline3D = List[Point3D]


def add_lead_in(
    segment_points: Polyline3D,
    lead_distance: float = 2.0,
    lead_angle: float = 45.0,
    approach_height: float = 1.0,
) -> Polyline3D:
    """
    Add a lead-in approach path before the first point of a segment.

    The lead-in starts above and behind the first point, approaching
    at the specified angle.

    Parameters:
        segment_points: Original segment points [(x, y, z), ...].
        lead_distance: Horizontal distance of lead-in (mm).
        lead_angle: Approach angle from horizontal (degrees).
        approach_height: Additional height above first point (mm).

    Returns:
        Modified segment points with lead-in prepended.
    """
    if not segment_points or len(segment_points) < 2:
        return segment_points

    p0 = segment_points[0]
    p1 = segment_points[1]

    # Direction from first to second point
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    length = math.sqrt(dx * dx + dy * dy)

    if length < 1e-10:
        # No direction — approach from above
        lead_point = (p0[0], p0[1], p0[2] + approach_height)
        return [lead_point] + list(segment_points)

    # Approach from behind the first point
    nx = -dx / length  # Reverse direction
    ny = -dy / length

    angle_rad = math.radians(lead_angle)
    horiz_dist = lead_distance * math.cos(angle_rad)
    vert_dist = lead_distance * math.sin(angle_rad) + approach_height

    lead_point: Point3D = (
        p0[0] + horiz_dist * nx,
        p0[1] + horiz_dist * ny,
        p0[2] + vert_dist,
    )

    return [lead_point] + list(segment_points)


def add_lead_out(
    segment_points: Polyline3D,
    lead_distance: float = 2.0,
    lead_angle: float = 45.0,
    exit_height: float = 1.0,
) -> Polyline3D:
    """
    Add a lead-out exit path after the last point of a segment.

    The lead-out continues past the last point and rises at the specified angle.

    Parameters:
        segment_points: Original segment points.
        lead_distance: Horizontal distance of lead-out (mm).
        lead_angle: Exit angle from horizontal (degrees).
        exit_height: Additional height above last point (mm).

    Returns:
        Modified segment points with lead-out appended.
    """
    if not segment_points or len(segment_points) < 2:
        return segment_points

    pN = segment_points[-1]
    pN1 = segment_points[-2]

    # Direction from second-to-last to last point
    dx = pN[0] - pN1[0]
    dy = pN[1] - pN1[1]
    length = math.sqrt(dx * dx + dy * dy)

    if length < 1e-10:
        lead_point = (pN[0], pN[1], pN[2] + exit_height)
        return list(segment_points) + [lead_point]

    nx = dx / length  # Continue in same direction
    ny = dy / length

    angle_rad = math.radians(lead_angle)
    horiz_dist = lead_distance * math.cos(angle_rad)
    vert_dist = lead_distance * math.sin(angle_rad) + exit_height

    lead_point: Point3D = (
        pN[0] + horiz_dist * nx,
        pN[1] + horiz_dist * ny,
        pN[2] + vert_dist,
    )

    return list(segment_points) + [lead_point]


def add_retract(
    point: Point3D,
    retract_height: float = 5.0,
    clearance_height: Optional[float] = None,
) -> List[Point3D]:
    """
    Generate retraction points above a given point.

    Used between travel moves to lift the tool above the workpiece.

    Parameters:
        point: Current position (x, y, z).
        retract_height: Height to retract above current Z.
        clearance_height: Absolute Z clearance (overrides retract_height if higher).

    Returns:
        List of retraction points [retract_point, clearance_point].
    """
    retract_z = point[2] + retract_height
    if clearance_height is not None:
        retract_z = max(retract_z, clearance_height)

    return [(point[0], point[1], retract_z)]


def add_engage_disengage(
    segment_points: Polyline3D,
    lead_in_distance: float = 0.0,
    lead_in_angle: float = 45.0,
    lead_out_distance: float = 0.0,
    lead_out_angle: float = 45.0,
    approach_height: float = 1.0,
) -> Polyline3D:
    """
    Apply both lead-in and lead-out to a segment.

    Parameters:
        segment_points: Original segment points.
        lead_in_distance: Lead-in distance (0 = disabled).
        lead_in_angle: Lead-in approach angle (degrees).
        lead_out_distance: Lead-out distance (0 = disabled).
        lead_out_angle: Lead-out exit angle (degrees).
        approach_height: Height offset for approach/exit.

    Returns:
        Modified segment points with lead-in/out.
    """
    result = list(segment_points)

    if lead_in_distance > 0:
        result = add_lead_in(result, lead_in_distance, lead_in_angle, approach_height)

    if lead_out_distance > 0:
        result = add_lead_out(result, lead_out_distance, lead_out_angle, approach_height)

    return result
