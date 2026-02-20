"""
Coordinate Verification Oracle — independent ground-truth calculator.

This module computes expected values WITHOUT using the OpenAxis codebase.
It is used to verify that the OpenAxis pipeline (slicer → IK → FK) produces
internally consistent results.

What makes this an independent oracle (not circular):
  1. DH parameters: from the ABB IRB 6700 URDF/datasheet via roboticstoolbox-python
     standard robot library. These are manufacturer-specified — not LLM-generated.
     Reference: Peter Corke, "Robotics, Vision and Control", Springer 2023.

  2. DH transform formula: from Craig, "Introduction to Robotics", 3rd ed., eq. 3.6.
     This is a textbook identity — not novel code.

  3. Coordinate transform (slicer → robot frame): a direct Python transcription of
     units.ts:waypointToRobotFrame(). Pure arithmetic — independently verifiable by
     inspection of the TypeScript source.

What this oracle CANNOT verify:
  - Whether ORNL Slicer 2 put the perimeter in the geometrically correct location.
    That requires a human-verified fixture (see tests/fixtures/README.md).

Usage pattern (DO use):
    # Pipeline produces IK joints for a known slicer position
    joints = pipeline.solve_ik(waypoint)

    # Oracle independently computes where those joints place the TCP
    target_m = oracle.slicer_to_robot_frame(waypoint["position"], build_plate, robot_pos)
    result = oracle.verify_ik_solution(joints, target_m)
    assert result["within_tolerance"], f"IK error {result['error_mm']:.2f}mm"

Usage pattern (DO NOT use):
    # Running the code and writing the result as the expected value is NOT a test.
    toolpath = slicer.slice(stl)
    assert toolpath.layers[0].z == 2.0  # ← if you got 2.0 by running this code,
                                         #   this proves nothing.
"""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np

# ---------------------------------------------------------------------------
# ABB IRB 6700 — DH Parameters
#
# Source: roboticstoolbox-python standard robot library, IRB6700 model.
# Reference: Peter Corke, "Robotics, Vision and Control", Springer 2023.
# Values confirmed against config/urdf/abb_irb6700.urdf and
# src/backend/robot_service.py:_create_irb6700_dh().
#
# Format: (d_metres, a_metres, alpha_radians)
# ---------------------------------------------------------------------------
IRB6700_DH: list[tuple[float, float, float]] = [
    (0.780,   0.320, -math.pi / 2),   # Joint 1: base rotation
    (0.000,   1.125,  0.000),          # Joint 2: shoulder
    (0.000,   0.200, -math.pi / 2),   # Joint 3: elbow
    (1.1425,  0.000,  math.pi / 2),   # Joint 4: wrist 1
    (0.000,   0.000, -math.pi / 2),   # Joint 5: wrist 2
    (0.200,   0.000,  0.000),          # Joint 6: wrist 3 / flange
]

# Joint limits in radians — from config/urdf/abb_irb6700.urdf and
# robot_service.py:_create_irb6700_dh(), cross-referenced with ABB datasheet.
IRB6700_QLIM: list[tuple[float, float]] = [
    (-math.radians(170), math.radians(170)),   # J1: ±170°
    (-math.radians(65),  math.radians(85)),    # J2: -65° to +85°
    (-math.radians(180), math.radians(70)),    # J3: -180° to +70°
    (-math.radians(300), math.radians(300)),   # J4: ±300°
    (-math.radians(130), math.radians(130)),   # J5: ±130°
    (-math.radians(360), math.radians(360)),   # J6: ±360°
]

# Default TCP Z offset for the WAAM torch tool (from config/robots/abb_irb6700.yaml)
TCP_Z_OFFSET_M: float = 0.150


# ---------------------------------------------------------------------------
# DH Transform
# ---------------------------------------------------------------------------

def dh_transform(theta: float, d: float, a: float, alpha: float) -> np.ndarray:
    """
    Standard Denavit-Hartenberg homogeneous transform matrix for one joint.

    Formula: Craig, "Introduction to Robotics", 3rd ed., eq. 3.6.
    This is a textbook identity — not novel code.

    Args:
        theta: Joint angle (radians)
        d:     Link offset along Z (metres)
        a:     Link length along X (metres)
        alpha: Twist angle about X (radians)

    Returns:
        4×4 numpy array — homogeneous transform from frame i-1 to frame i.
    """
    ct, st = math.cos(theta), math.sin(theta)
    ca, sa = math.cos(alpha), math.sin(alpha)
    return np.array([
        [ct,    -st * ca,  st * sa,   a * ct],
        [st,     ct * ca, -ct * sa,   a * st],
        [0.0,    sa,       ca,        d     ],
        [0.0,    0.0,      0.0,       1.0   ],
    ])


# ---------------------------------------------------------------------------
# Forward Kinematics
# ---------------------------------------------------------------------------

def fk_from_joints(
    joint_angles_rad: list[float],
    tcp_z_m: float = TCP_Z_OFFSET_M,
) -> dict:
    """
    Independent forward kinematics using ABB IRB 6700 DH parameters.

    This does NOT call robot_service.py. It is a separate implementation of
    the same math, using the same published DH parameters, for cross-checking.

    The TCP offset is applied as a pure Z translation in the tool frame
    (matching how robot_service.py sets robot.tool = SE3(0, 0, tcp_z)).

    Args:
        joint_angles_rad: 6-element list [j1..j6] in radians.
        tcp_z_m:          TCP Z offset in metres (default: 0.150 m = 150 mm torch).

    Returns:
        {
            "position_m":  [x, y, z] — TCP in robot base frame, metres, Z-up.
            "transform":   4×4 numpy array — full homogeneous transform T_0_tcp.
        }
    """
    if len(joint_angles_rad) != 6:
        raise ValueError(f"Expected 6 joint angles, got {len(joint_angles_rad)}")

    T = np.eye(4)
    for q, (d, a, alpha) in zip(joint_angles_rad, IRB6700_DH):
        T = T @ dh_transform(q, d, a, alpha)

    # Apply TCP Z offset along the tool Z axis (post-multiply pure translation)
    T_tcp = np.eye(4)
    T_tcp[2, 3] = tcp_z_m
    T = T @ T_tcp

    return {
        "position_m": [float(T[0, 3]), float(T[1, 3]), float(T[2, 3])],
        "transform": T,
    }


# ---------------------------------------------------------------------------
# Coordinate Transform: Slicer → Robot Frame
# ---------------------------------------------------------------------------

def slicer_to_robot_frame(
    slicer_pos_mm: Tuple[float, float, float],
    build_plate_origin_scene_m: Tuple[float, float, float],
    robot_pos_scene_m: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> Tuple[float, float, float]:
    """
    Convert slicer output coordinates to robot base frame.

    This is a Python transcription of units.ts:waypointToRobotFrame().
    It is pure arithmetic — verifiable by reading the TypeScript source.

    Transform chain (matching units.ts exactly):
      Step 1: slicer (mm, Z-up) → scene (metres, Y-up, world position)
        sceneX = buildPlateOrigin[0] + slicerX * 0.001
        sceneY = buildPlateOrigin[1] + slicerZ * 0.001   ← slicer Z → scene Y
        sceneZ = buildPlateOrigin[2] - slicerY * 0.001   ← slicer Y → scene -Z

      Step 2: scene (Y-up) → robot base (Z-up)
        Subtract robot position offset.
        Invert the robot wrapper's X-axis rotation (-90°):
        [x, y, z]_scene → [x, -z, y]_robot

    Args:
        slicer_pos_mm:              [x, y, z] from ORNL Slicer 2, mm, Z-up.
        build_plate_origin_scene_m: Build plate position in Three.js scene,
                                    [x, y, z] Y-up metres.
        robot_pos_scene_m:          Robot base position in Three.js scene,
                                    [x, y, z] Y-up metres (default: origin).

    Returns:
        (x, y, z) in metres, Z-up, robot base frame — ready for IK input.
    """
    sx, sy, sz = slicer_pos_mm
    bx, by, bz = build_plate_origin_scene_m
    rx, ry, rz = robot_pos_scene_m

    # Step 1: slicer mm Z-up → scene metres Y-up
    scene_x = bx + sx * 0.001
    scene_y = by + sz * 0.001    # slicer Z → scene Y
    scene_z = bz - sy * 0.001   # slicer Y → scene -Z

    # Step 2: scene Y-up → robot base Z-up
    dx = scene_x - rx
    dy = scene_y - ry
    dz = scene_z - rz

    robot_x = dx
    robot_y = -dz
    robot_z = dy

    return (robot_x, robot_y, robot_z)


# ---------------------------------------------------------------------------
# IK Solution Verifier
# ---------------------------------------------------------------------------

def verify_ik_solution(
    joint_angles_rad: list[float],
    target_robot_frame_m: Tuple[float, float, float],
    tolerance_m: float = 0.002,
    tcp_z_m: float = TCP_Z_OFFSET_M,
) -> dict:
    """
    Verify that a set of joint angles places the TCP at the target position.

    Uses the independent FK oracle (not robot_service.py) to compute where
    the TCP actually ends up. The difference is the IK position error.

    This is the FK-IK roundtrip check: FK(IK(target)) ≈ target.
    It is the one check with genuine mathematical ground truth — it is the
    definition of what a correct IK solution means.

    Args:
        joint_angles_rad:       6-element list in radians.
        target_robot_frame_m:   [x, y, z] in metres, robot base frame, Z-up.
        tolerance_m:            Acceptable position error in metres (default 2 mm).
        tcp_z_m:                TCP Z offset in metres.

    Returns:
        {
            "fk_position_m":    [x, y, z] where FK places the TCP (metres),
            "target_m":         [x, y, z] the intended target (metres),
            "error_m":          Euclidean distance error (metres),
            "error_mm":         Same in millimetres (for readability),
            "within_tolerance": bool — True if error ≤ tolerance_m,
            "tolerance_m":      The tolerance used,
        }
    """
    fk = fk_from_joints(joint_angles_rad, tcp_z_m)
    fk_pos = fk["position_m"]
    tx, ty, tz = target_robot_frame_m

    error = math.sqrt(
        (fk_pos[0] - tx) ** 2 +
        (fk_pos[1] - ty) ** 2 +
        (fk_pos[2] - tz) ** 2
    )

    return {
        "fk_position_m": fk_pos,
        "target_m": list(target_robot_frame_m),
        "error_m": error,
        "error_mm": error * 1000.0,
        "within_tolerance": error <= tolerance_m,
        "tolerance_m": tolerance_m,
    }


# ---------------------------------------------------------------------------
# Joint Limit Checker
# ---------------------------------------------------------------------------

def joints_within_limits(joint_angles_rad: list[float]) -> dict:
    """
    Check that all joint angles are within the ABB IRB 6700 URDF limits.

    Limits are from config/urdf/abb_irb6700.urdf and robot_service.py,
    cross-referenced against the ABB product specification.

    Args:
        joint_angles_rad: 6-element list in radians.

    Returns:
        {
            "all_within":  bool,
            "violations":  list of dicts, one per out-of-limit joint:
                {
                    "joint":     int (1-indexed),
                    "value_deg": float,
                    "limit_deg": (min_deg, max_deg),
                }
        }
    """
    violations = []
    for i, (q, (lo, hi)) in enumerate(zip(joint_angles_rad, IRB6700_QLIM)):
        if not (lo <= q <= hi):
            violations.append({
                "joint": i + 1,
                "value_deg": math.degrees(q),
                "limit_deg": (math.degrees(lo), math.degrees(hi)),
            })
    return {
        "all_within": len(violations) == 0,
        "violations": violations,
    }
