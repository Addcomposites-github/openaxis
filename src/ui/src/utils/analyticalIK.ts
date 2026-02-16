/**
 * analyticalIK.ts — 6-DOF IK solver for ABB IRB 6700.
 *
 * Uses geometric joint_1 (atan2) + numerical Newton-Raphson for joints 2-3
 * in the arm plane + nominal wrist angles (joints 4-6) for tool-down.
 *
 * The arm plane FK for joints 2-3 uses the EXACT forearm geometry:
 *   Forearm goes Z by D4=0.2m then X by A4=1.1425m (a Z-X zigzag),
 *   which the previous analytical formula mishandled.
 *
 * Newton-Raphson converges in 3-5 iterations (~10μs per point total).
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

// ─── Arm-plane FK (exact forearm geometry) ──────────────────────────────

/**
 * Compute wrist center position in the arm plane (r, z) relative to joint_2.
 *
 * The forearm kinematic chain from joint_3 is:
 *   +Z by D4 (to joint_4), then +X by A4 (to joint_5)
 * In the arm plane after j2+j3 rotation:
 *   Z direction = (cos(phi), sin(phi))
 *   X direction = (-sin(phi), cos(phi))
 * where phi = j2 + j3.
 */
function armPlaneFK(j2: number, j3: number): [number, number] {
  const phi = j2 + j3;
  const cp = Math.cos(phi), sp = Math.sin(phi);
  const wr = A2 * Math.cos(j2) + D4 * cp - A4 * sp;
  const wz = A2 * Math.sin(j2) + D4 * sp + A4 * cp;
  return [wr, wz];
}

/**
 * Jacobian of the arm-plane FK.
 * Returns [[dwr/dj2, dwr/dj3], [dwz/dj2, dwz/dj3]].
 */
function armPlaneJacobian(j2: number, j3: number): [[number, number], [number, number]] {
  const phi = j2 + j3;
  const cp = Math.cos(phi), sp = Math.sin(phi);
  const common_r = -D4 * sp - A4 * cp;  // d/dphi of (D4*cp - A4*sp)
  const common_z = D4 * cp - A4 * sp;   // d/dphi of (D4*sp + A4*cp)
  return [
    [-A2 * Math.sin(j2) + common_r, common_r],
    [A2 * Math.cos(j2) + common_z, common_z],
  ];
}

/**
 * Solve arm-plane IK numerically using Newton-Raphson.
 *
 * Finds j2, j3 such that armPlaneFK(j2, j3) ≈ (rt, st).
 * Converges in 3-5 iterations for typical robotics configurations.
 *
 * @param rt - Target horizontal distance from joint_2 (meters)
 * @param st - Target vertical distance from joint_2 (meters)
 * @param j2Init - Initial guess for j2 (radians)
 * @param j3Init - Initial guess for j3 (radians)
 * @returns Solution {j2, j3, converged}
 */
function solveArmPlane(
  rt: number,
  st: number,
  j2Init: number,
  j3Init: number,
  maxIter = 30,
): { j2: number; j3: number; converged: boolean } {
  let j2 = j2Init;
  let j3 = j3Init;
  let converged = false;

  for (let i = 0; i < maxIter; i++) {
    const [wr, wz] = armPlaneFK(j2, j3);
    const er = rt - wr;
    const ez = st - wz;
    const err = er * er + ez * ez;
    if (err < 1e-16) { converged = true; break; }

    const J = armPlaneJacobian(j2, j3);
    const det = J[0][0] * J[1][1] - J[0][1] * J[1][0];
    if (Math.abs(det) < 1e-12) break; // Near singularity

    const invDet = 1 / det;
    const dj2 = (J[1][1] * er - J[0][1] * ez) * invDet;
    const dj3 = (-J[1][0] * er + J[0][0] * ez) * invDet;
    j2 += dj2;
    j3 += dj3;

    if (err < 1e-12) { converged = true; break; }
  }

  return { j2, j3, converged };
}

// ─── IK result types ─────────────────────────────────────────────────────

export interface IKSolution {
  jointAngles: number[]; // [j1, j2, j3, j4, j5, j6] in radians
  reachable: boolean;
  error: number; // position error in meters
}

/**
 * Full 6-DOF FK: given joint angles, compute TCP position in robot base frame.
 *
 * This uses the exact forearm geometry (D4 along Z then A4 along X) and
 * assumes the tool points straight down (−Z in world) with length = D6 + toolLength.
 */
function fullFK(
  j1: number, j2: number, j3: number,
  toolLength: number,
): [number, number, number] {
  const [wr, wz] = armPlaneFK(j2, j3);
  const wristR = A1 + wr;
  const wristZ = D1 + wz;
  const c1 = Math.cos(j1);
  const s1 = Math.sin(j1);
  // Tool points down → TCP is below wrist center
  return [wristR * c1, wristR * s1, wristZ - D6 - toolLength];
}

/**
 * Solve IK for a target TCP position in the robot's Z-up base frame (meters).
 *
 * Approach:
 * - Joint 1: atan2 for base rotation
 * - Joints 2-3: Newton-Raphson numerical solver for the arm plane
 * - Joints 4-6: Nominal wrist angles for "torch pointing down" orientation
 *
 * Wrist center: since the tool points straight down, the wrist (joint_5) is
 * ABOVE the TCP by (D6 + toolLength) meters.
 *
 * @param target - [x, y, z] in meters, in robot base frame (Z-up)
 * @param toolLength - end effector length in meters (flange to TCP)
 * @param prevSolution - previous solution for continuity (seeds initial guess)
 * @returns IKSolution with joint angles in radians
 */
export function solveIK6DOF(
  target: [number, number, number],
  toolLength: number = 0.15,
  prevSolution?: number[],
): IKSolution {
  const [tx, ty, tz] = target;

  // ── Joint 1: Base rotation ──────────────────────────────────────────
  let j1 = Math.atan2(ty, tx);
  j1 = clampAngle(j1, 0);

  // ── Wrist center position ───────────────────────────────────────────
  // Tool points straight down → wrist is ABOVE TCP
  // wrist_z = tcp_z + D6 + toolLength
  const rxy = Math.sqrt(tx * tx + ty * ty);
  const wcr = rxy;     // Horizontal distance from base Z-axis
  const wcz = tz + D6 + toolLength;  // Wrist is above TCP

  // Target relative to joint_2
  const rt = wcr - A1;
  const st = wcz - D1;
  const D = Math.sqrt(rt * rt + st * st);

  // ── Reachability check ──────────────────────────────────────────────
  const maxReach = A2 + FOREARM;
  const minReach = Math.abs(A2 - FOREARM);
  const reachable = D >= minReach * 0.9 && D <= maxReach * 1.05 && D > 0.01;

  let j2 = 0;
  let j3 = 0;

  if (reachable) {
    // ── Solve joints 2-3 with Newton-Raphson ──────────────────────────
    // Try multiple initial guesses and pick the best within joint limits.

    // Compute a rough initial guess from the target direction
    const alpha = Math.atan2(st, rt);

    // Initial guesses: combinations of (elbow-up, elbow-down) × (near/far)
    const guesses: [number, number][] = [
      [alpha + 0.5, -Math.PI + 0.3],  // Elbow-up, typical for reaching out
      [alpha - 0.3, -Math.PI - 0.3],  // Variation
      [0.5, -2.5],                     // Near horizontal, forearm folded back
      [0.8, -3.0],                     // More folded
      [-0.3, -1.5],                    // Arm reaching down
      [alpha, -Math.PI * 0.8],         // Direct toward target
    ];

    // If we have a previous solution, use it as primary guess
    if (prevSolution && prevSolution.length >= 3) {
      guesses.unshift([prevSolution[1], prevSolution[2]]);
    }

    let bestErr = Infinity;
    let bestJ2 = 0;
    let bestJ3 = 0;
    let bestConverged = false;

    for (const [j2g, j3g] of guesses) {
      const sol = solveArmPlane(rt, st, j2g, j3g);
      if (!sol.converged) continue;

      const [wr, wz] = armPlaneFK(sol.j2, sol.j3);
      const err = Math.sqrt((wr - rt) ** 2 + (wz - st) ** 2);

      // Check joint limits
      const j2c = clampAngle(sol.j2, 1);
      const j3c = clampAngle(sol.j3, 2);
      const withinLimits =
        Math.abs(j2c - sol.j2) < 0.01 && Math.abs(j3c - sol.j3) < 0.01;

      // Prefer solutions within joint limits
      const penalty = withinLimits ? 0 : 10;
      const totalErr = err + penalty;

      if (totalErr < bestErr) {
        bestErr = totalErr;
        bestJ2 = sol.j2;
        bestJ3 = sol.j3;
        bestConverged = true;
      }
    }

    if (bestConverged) {
      j2 = clampAngle(bestJ2, 1);
      j3 = clampAngle(bestJ3, 2);
    } else {
      // Fallback: point arm toward target
      j2 = clampAngle(alpha, 1);
      j3 = clampAngle(-Math.PI, 2);
    }
  } else {
    // Unreachable: point arm toward target as best we can
    const alpha = Math.atan2(st, rt);
    j2 = clampAngle(alpha, 1);
    j3 = clampAngle(-Math.PI, 2);
  }

  // ── Joints 4, 5, 6: Wrist orientation ─────────────────────────────
  // For WAAM/extrusion, the tool points straight down.
  // j5 compensates j2+j3 to keep tool vertical.
  let j4 = 0;
  let j5 = -(j2 + j3);
  let j6 = 0;

  // Use previous solution for wrist continuity
  if (prevSolution && prevSolution.length >= 6) {
    j4 = prevSolution[3];
    j6 = prevSolution[5];
  }

  j4 = clampAngle(j4, 3);
  j5 = clampAngle(j5, 4);
  j6 = clampAngle(j6, 5);

  // ── Compute position error via exact FK ─────────────────────────────
  const [fkx, fky, fkz] = fullFK(j1, j2, j3, toolLength);
  const error = Math.sqrt(
    (fkx - tx) ** 2 + (fky - ty) ** 2 + (fkz - tz) ** 2,
  );

  return {
    jointAngles: [j1, j2, j3, j4, j5, j6],
    reachable: reachable && error < 0.05, // Must also pass FK check
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
