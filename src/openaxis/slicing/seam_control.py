"""
Seam Control — Layer start point selection and seam shape generation.

Provides 3 seam placement modes:
1. guided    — All layers start at a user-specified angle/position
2. distributed — Start points are evenly distributed around the perimeter
3. random    — Random start point per layer (reduces visible seam line)

And 4 seam shapes:
1. straight  — No modification (default)
2. zigzag    — Zigzag offset at seam point
3. triangular — Triangular indent at seam
4. sine      — Sinusoidal wave at seam region
"""

import math
import random
from typing import List, Optional, Tuple

Point2D = Tuple[float, float]
Polyline = List[Point2D]


# ─── Seam Placement ──────────────────────────────────────────────────────────

def find_nearest_point_index(
    contour: Polyline,
    target: Point2D,
) -> int:
    """Find the index of the point in contour nearest to target."""
    best_idx = 0
    best_dist = float('inf')
    for i, pt in enumerate(contour):
        dist = (pt[0] - target[0]) ** 2 + (pt[1] - target[1]) ** 2
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    return best_idx


def rotate_contour(contour: Polyline, start_index: int) -> Polyline:
    """Rotate contour so that start_index becomes the first point."""
    if not contour or start_index == 0:
        return list(contour)
    n = len(contour)
    # Check if contour is closed (first == last)
    is_closed = (
        len(contour) > 1 and
        abs(contour[0][0] - contour[-1][0]) < 1e-6 and
        abs(contour[0][1] - contour[-1][1]) < 1e-6
    )
    if is_closed:
        # Remove duplicate closing point, rotate, then re-close
        open_contour = contour[:-1]
        n = len(open_contour)
        idx = start_index % n
        rotated = open_contour[idx:] + open_contour[:idx]
        rotated.append(rotated[0])  # Re-close
        return rotated
    else:
        idx = start_index % n
        return contour[idx:] + contour[:idx]


def place_seam_guided(
    contour: Polyline,
    angle_deg: float = 0.0,
    center: Optional[Point2D] = None,
) -> Polyline:
    """
    Guided seam: start contour at a specific angular position relative to center.

    Parameters:
        contour: Perimeter polyline.
        angle_deg: Angle in degrees (0 = +X direction).
        center: Center point (default = centroid of contour).
    """
    if not contour:
        return contour

    if center is None:
        cx = sum(p[0] for p in contour) / len(contour)
        cy = sum(p[1] for p in contour) / len(contour)
        center = (cx, cy)

    # Find a target point far in the specified direction
    angle_rad = math.radians(angle_deg)
    far = 1e6
    target = (center[0] + far * math.cos(angle_rad), center[1] + far * math.sin(angle_rad))

    idx = find_nearest_point_index(contour, target)
    return rotate_contour(contour, idx)


def place_seam_distributed(
    contour: Polyline,
    layer: int,
    total_layers: int = 100,
) -> Polyline:
    """
    Distributed seam: evenly space start points around the perimeter.
    Each layer starts at a different position.
    """
    if not contour or len(contour) < 2:
        return contour

    n = len(contour)
    # Distribute evenly
    offset = int((layer / max(total_layers, 1)) * n) % n
    return rotate_contour(contour, offset)


def place_seam_random(
    contour: Polyline,
    layer: int,
    seed: int = 42,
) -> Polyline:
    """
    Random seam: each layer starts at a random position.
    Uses deterministic seed + layer for reproducibility.
    """
    if not contour or len(contour) < 2:
        return contour

    rng = random.Random(seed + layer)
    idx = rng.randint(0, len(contour) - 1)
    return rotate_contour(contour, idx)


# ─── Seam Shapes ──────────────────────────────────────────────────────────────

def apply_seam_shape_straight(contour: Polyline, **_: object) -> Polyline:
    """No modification — standard seam."""
    return contour


def apply_seam_shape_zigzag(
    contour: Polyline,
    amplitude: float = 0.5,
    frequency: int = 3,
) -> Polyline:
    """
    Zigzag seam shape: offset points near the seam in alternating directions.
    Affects the first/last few points of the contour.
    """
    if not contour or len(contour) < 4:
        return contour

    result = list(contour)
    n_affected = min(frequency * 2, len(result) // 4)

    for i in range(n_affected):
        if i >= len(result):
            break
        # Compute normal at this point
        next_i = min(i + 1, len(result) - 1)
        dx = result[next_i][0] - result[i][0]
        dy = result[next_i][1] - result[i][1]
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1e-10:
            continue
        nx, ny = -dy / length, dx / length
        sign = 1 if (i % 2 == 0) else -1
        result[i] = (
            result[i][0] + sign * amplitude * nx,
            result[i][1] + sign * amplitude * ny,
        )

    return result


def apply_seam_shape_triangular(
    contour: Polyline,
    depth: float = 1.0,
) -> Polyline:
    """
    Triangular seam shape: create a triangular indent at the seam point.
    """
    if not contour or len(contour) < 4:
        return contour

    result = list(contour)
    # Move first point inward to create indent
    if len(result) >= 3:
        # Direction from point 1 to point 0
        dx = result[0][0] - result[1][0]
        dy = result[0][1] - result[1][1]
        length = math.sqrt(dx * dx + dy * dy)
        if length > 1e-10:
            # Normal pointing inward
            nx, ny = -dy / length, dx / length
            result[0] = (
                result[0][0] + depth * nx,
                result[0][1] + depth * ny,
            )
    return result


def apply_seam_shape_sine(
    contour: Polyline,
    amplitude: float = 0.3,
    wavelength: float = 5.0,
) -> Polyline:
    """
    Sine wave seam shape: sinusoidal offset near the seam region.
    """
    if not contour or len(contour) < 4:
        return contour

    result = list(contour)
    n_affected = min(20, len(result) // 4)

    cum_dist = 0.0
    for i in range(1, n_affected + 1):
        if i >= len(result):
            break
        dx = result[i][0] - result[i - 1][0]
        dy = result[i][1] - result[i - 1][1]
        seg_len = math.sqrt(dx * dx + dy * dy)
        cum_dist += seg_len

        if seg_len < 1e-10:
            continue

        # Normal
        nx, ny = -dy / seg_len, dx / seg_len
        offset = amplitude * math.sin(2 * math.pi * cum_dist / wavelength)
        result[i] = (
            result[i][0] + offset * nx,
            result[i][1] + offset * ny,
        )

    return result


# ─── Registry ─────────────────────────────────────────────────────────────────

SEAM_MODES = {
    'guided': place_seam_guided,
    'distributed': place_seam_distributed,
    'random': place_seam_random,
}

SEAM_SHAPES = {
    'straight': apply_seam_shape_straight,
    'zigzag': apply_seam_shape_zigzag,
    'triangular': apply_seam_shape_triangular,
    'sine': apply_seam_shape_sine,
}


def apply_seam(
    contour: Polyline,
    mode: str = 'guided',
    shape: str = 'straight',
    layer: int = 0,
    **kwargs: object,
) -> Polyline:
    """
    Apply seam placement and shape to a contour.

    Parameters:
        contour: Perimeter polyline.
        mode: Seam placement mode ('guided', 'distributed', 'random').
        shape: Seam shape ('straight', 'zigzag', 'triangular', 'sine').
        layer: Current layer index.
        **kwargs: Additional parameters for mode/shape functions
                  (angle_deg, total_layers, center, seed, amplitude, etc.)
    """
    import inspect

    # Apply placement mode — pass only accepted kwargs
    mode_fn = SEAM_MODES.get(mode, place_seam_guided)
    mode_sig = inspect.signature(mode_fn)
    mode_params = set(mode_sig.parameters.keys()) - {'contour'}

    # Build mode kwargs from layer + user kwargs
    mode_kwargs: dict = {}
    if 'layer' in mode_params:
        mode_kwargs['layer'] = layer
    for k, v in kwargs.items():
        if k in mode_params:
            mode_kwargs[k] = v

    placed = mode_fn(contour, **mode_kwargs)

    # Apply shape — pass only accepted kwargs
    shape_fn = SEAM_SHAPES.get(shape, apply_seam_shape_straight)
    shape_sig = inspect.signature(shape_fn)
    shape_params = set(shape_sig.parameters.keys()) - {'contour'}

    shape_kwargs: dict = {}
    for k, v in kwargs.items():
        if k in shape_params:
            shape_kwargs[k] = v

    shaped = shape_fn(placed, **shape_kwargs)

    return shaped
