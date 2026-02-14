/**
 * analyticalIK.ts — Geometric 6-DOF IK solver for ABB IRB 6700.
 *
 * Computes approximate joint angles entirely in the browser using
 * closed-form geometry. Runs in microseconds per point (vs. milliseconds
 * for the backend's numerical optimization), making it suitable as a
 * real-time fallback when the backend IK is unavailable.
 *
 * DH parameters extracted from config/urdf/abb_irb6700.urdf:
 *
 *   joint_1: origin [0, 0, 0.78],  axis Z, limits +-2.967 rad
 *   joint_2: origin [0.32, 0, 0],  axis Y, limits -1.134..+1.484 rad
 *   joint_3: origin [0, 0, 1.125], axis Y, limits -3.142..+1.222 rad
 *   joint_4: origin [0, 0, 0.2],   axis X, limits +-5.236 rad
 *   joint_5: origin [1.1425, 0, 0],axis Y, limits +-2.269 rad
 *   joint_6: origin [0.2, 0, 0],   axis X, limits +-6.283 rad
 *
 * Robot coordinate frame: Z-up, all units in METERS.
 */

// ─── Link lengths from URDF joint origins ──────────────────────────────

/** Height from base to joint_1 (shoulder center) */
const D1 = 0.78;

/** Horizontal offset from joint_1 to joint_2 axis */
const A1 = 0.32;

/** Upper arm length: joint_2 to joint_3 (along Z in link_1 frame) */
const A2 = 1.125;

/** Forearm link 1: joint_3 to joint_4 (along Z) */
const D4 = 0.2;

/** Forearm link 2: joint_4 to joint_5 (along X) */
const A4 = 1.1425;

/** Wrist length: joint_5 to joint_6 (along X) */
const D6 = 0.2;

/** Effective forearm length (joint_3 through joint_4 to joint_5) */
const FOREARM = Math.sqrt(D4 * D4 + A4 * A4);

/** Angle offset for the forearm elbow geometry */
const FOREARM_OFFSET_ANGLE = Math.atan2(D4, A4);

// ─── Joint limits from URDF ─────────────────────────────────────────────

const JOINT_LIMITS: [number, number][] = [
  [-2.96706, 2.96706],   // joint_1
  [-1.13446, 1.48353],   // joint_2
  [-3.14159, 1.22173],   // joint_3
  [-5.23599, 5.23599],   // joint_4
  [-2.26893, 2.26893],   // joint_5
  [-6.28319, 6.28319],   // joint_6
];

// ─── Helpers ─────────────────────────────────────────────────────────────

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function clampAngle(angle: number, jointIndex: number): number {
  const [lo, hi] = JOINT_LIMITS[jointIndex];
  return clamp(angle, lo, hi);
}

// ─── IK result types ─────────────────────────────────────────────────────

export interface IKSolution {
  jointAngles: number[]; // [j1, j2, j3, j4, j5, j6] in radians
  reachable: boolean;
  error: number; // position error in meters
}

/**
 * Solve IK for a target TCP position in the robot's Z-up base frame (meters).
 *
 * Uses a geometric approach:
 * - Joint 1: atan2 for base rotation
 * - Joints 2-3: 2-link planar IK (law of cosines)
 * - Joints 4-6: Nominal wrist angles for "torch pointing down" orientation
 *
 * @param target - [x, y, z] in meters, in robot base frame (Z-up)
 * @param toolLength - end effector length in meters (default 0.15)
 * @param prevSolution - previous solution for continuity (unused joints seeded)
 * @returns IKSolution with joint angles in radians
 */
export function solveIK6DOF(
  target: [number, number, number],
  toolLength: number = 0.15,
  prevSolution?: number[],
): IKSolution {
  const [tx, ty, tz] = target;

  // ── Joint 1: Base rotation ──────────────────────────────────────────
  // Project target onto XY plane to find base rotation angle
  let j1 = Math.atan2(ty, tx);
  j1 = clampAngle(j1, 0);

  // ── Wrist center position ───────────────────────────────────────────
  // Subtract tool length along Z from the target to get wrist center
  // (assumes tool points straight down in world Z)
  const wcx = tx;
  const wcy = ty;
  const wcz = tz - toolLength - D6;

  // ── Transform to the arm plane ──────────────────────────────────────
  // Distance from the base Z axis to the wrist center in the XY plane
  const rxy = Math.sqrt(wcx * wcx + wcy * wcy);

  // Horizontal distance in the arm plane from joint_2 to wrist center
  // (subtract the shoulder offset A1)
  const r = rxy - A1;

  // Vertical distance from joint_2 (at height D1) to wrist center
  const s = wcz - D1;

  // Distance from joint_2 to wrist center in the arm plane
  const D = Math.sqrt(r * r + s * s);

  // ── Reachability check ──────────────────────────────────────────────
  const maxReach = A2 + FOREARM;
  const minReach = Math.abs(A2 - FOREARM);
  const reachable = D >= minReach && D <= maxReach && D > 0.01;

  let j2 = 0;
  let j3 = 0;

  if (reachable) {
    // ── Joint 3: Elbow angle via law of cosines ─────────────────────
    // cos(elbow_internal) = (A2^2 + FOREARM^2 - D^2) / (2 * A2 * FOREARM)
    const cosElbow = clamp(
      (A2 * A2 + FOREARM * FOREARM - D * D) / (2 * A2 * FOREARM),
      -1, 1,
    );
    const elbowInternal = Math.acos(cosElbow);

    // The URDF joint_3 angle is measured differently from the internal elbow angle.
    // joint_3 = 0 when the forearm is straight along the upper arm.
    // The forearm has an angular offset (FOREARM_OFFSET_ANGLE) because it goes
    // through joint_4 at a right angle.
    j3 = Math.PI - elbowInternal - FOREARM_OFFSET_ANGLE;
    j3 = clampAngle(j3, 2);

    // ── Joint 2: Shoulder angle ─────────────────────────────────────
    // Angle from horizontal to the line connecting joint_2 to wrist center
    const alpha = Math.atan2(s, r);

    // Angle at joint_2 in the triangle (joint_2, joint_3, wrist_center)
    const cosBeta = clamp(
      (A2 * A2 + D * D - FOREARM * FOREARM) / (2 * A2 * D),
      -1, 1,
    );
    const beta = Math.acos(cosBeta);

    // joint_2 is measured from horizontal (Y axis in link_1 frame)
    // Positive = arm goes up
    j2 = alpha + beta;
    j2 = clampAngle(j2, 1);
  } else {
    // Unreachable: point arm toward target as best we can
    const alpha = Math.atan2(s, r);
    j2 = clampAngle(alpha, 1);
    j3 = clampAngle(0, 2);
  }

  // ── Joints 4, 5, 6: Wrist orientation ─────────────────────────────
  // For WAAM/extrusion, the tool typically points straight down.
  // We use nominal wrist angles that produce a downward tool orientation.
  // A more sophisticated approach would compute these from the desired
  // tool orientation, but for visualization this is sufficient.
  let j4 = 0;
  let j5 = -(j2 + j3); // Compensate shoulder+elbow to keep tool vertical
  let j6 = 0;

  // Use previous solution for continuity if available
  if (prevSolution && prevSolution.length >= 6) {
    // Keep j4 and j6 from previous solution if they were set
    j4 = prevSolution[3];
    j6 = prevSolution[5];
  }

  j4 = clampAngle(j4, 3);
  j5 = clampAngle(j5, 4);
  j6 = clampAngle(j6, 5);

  // ── Compute position error ────────────────────────────────────────
  // Rough forward kinematics check: compute approximate TCP position
  const c1 = Math.cos(j1), s1 = Math.sin(j1);
  const c2 = Math.cos(j2), s2 = Math.sin(j2);
  const c23 = Math.cos(j2 + j3), s23 = Math.sin(j2 + j3);

  // Approximate wrist position (ignoring wrist joint offsets)
  const wristR = A1 + A2 * c2 + FOREARM * c23;
  const wristZ = D1 + A2 * s2 + FOREARM * s23;
  const fkx = wristR * c1;
  const fky = wristR * s1;
  const fkz = wristZ + D6 + toolLength;

  const dx = fkx - tx;
  const dy = fky - ty;
  const dz = fkz - tz;
  const error = Math.sqrt(dx * dx + dy * dy + dz * dz);

  return {
    jointAngles: [j1, j2, j3, j4, j5, j6],
    reachable,
    error,
  };
}

/**
 * Solve IK for an entire trajectory of target positions.
 * Each solution seeds the next for smooth, continuous motion.
 *
 * @param positions - Array of [x, y, z] in meters, robot base frame (Z-up)
 * @param toolLength - End effector length in meters (default 0.15)
 * @returns Trajectory result with joint angles and reachability
 */
export function solveTrajectoryIKLocal(
  positions: [number, number, number][],
  toolLength: number = 0.15,
): {
  trajectory: number[][];
  reachability: boolean[];
  reachableCount: number;
  totalPoints: number;
  reachabilityPercent: number;
} {
  const trajectory: number[][] = [];
  const reachability: boolean[] = [];
  let prevSolution: number[] | undefined;

  for (const pos of positions) {
    const result = solveIK6DOF(pos, toolLength, prevSolution);
    trajectory.push(result.jointAngles);
    reachability.push(result.reachable);
    if (result.reachable) {
      prevSolution = result.jointAngles;
    }
  }

  const reachableCount = reachability.filter(Boolean).length;
  return {
    trajectory,
    reachability,
    reachableCount,
    totalPoints: positions.length,
    reachabilityPercent: positions.length > 0
      ? (reachableCount / positions.length) * 100
      : 0,
  };
}
