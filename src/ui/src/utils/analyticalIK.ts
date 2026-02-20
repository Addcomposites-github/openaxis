/**
 * analyticalIK.ts — IK solver interface.
 *
 * DELETED: Custom Newton-Raphson IK solver for ABB IRB 6700.
 *
 * The previous implementation was a custom 6-DOF IK solver that:
 * - Used geometric joint_1 (atan2) + numerical Newton-Raphson for joints 2-3
 * - Hardcoded wrist angles: j5 = -(j2 + j3), j4 = j6 = 0
 *   This only works for vertical-down tool orientation.
 * - Had known failures for off-axis targets (Y ≠ 0 with large tool lengths)
 * - Magic number initial guesses with no justification
 *
 * The spec calls for MoveIt2 via ROS2 for IK. The proven alternative is
 * compas_fab (Python backend) with PyBullet IK. The frontend should call
 * the backend IK endpoint instead of solving IK locally.
 *
 * For real-time simulation visualization, the frontend should:
 * 1. Request IK solution from the backend API
 * 2. Cache the trajectory result
 * 3. Interpolate between cached joint configurations for animation
 *
 * Accept the latency tradeoff: correctness > speed.
 * A wrong answer at 60fps is worse than a correct answer at 10fps.
 */

// ─── Types ──────────────────────────────────────────────────────────────

export interface IKSolution {
  jointAngles: number[];  // [j1, j2, j3, j4, j5, j6] in radians
  reachable: boolean;
  error: number;          // position error in meters
}

// ─── Backend IK API call ────────────────────────────────────────────────

/**
 * Solve IK for a single target position.
 *
 * The backend IK endpoint (POST /api/robot/ik) uses roboticstoolbox-python
 * for production-grade DH-based IK. For trajectory IK, use the
 * solveTrajectoryIK() function in api/robot.ts instead.
 *
 * This stub exists as a local fallback when the backend is unavailable.
 *
 * @param target - [x, y, z] in meters, in robot base frame (Z-up)
 * @param toolLength - end effector length in meters
 * @param prevSolution - previous solution for continuity
 * @returns IKSolution with joint angles in radians (all zeros = unreachable)
 */
export function solveIK6DOF(
  _target: [number, number, number],
  _toolLength: number = 0.15,
  _prevSolution?: number[],
): IKSolution {
  // Local stub — returns unreachable. Use backend API for real IK.
  return {
    jointAngles: [0, 0, 0, 0, 0, 0],
    reachable: false,
    error: Infinity,
  };
}

/**
 * Local fallback IK for trajectory — used when backend is unavailable.
 *
 * For production IK, use solveTrajectoryIK() in api/robot.ts which calls
 * POST /api/robot/solve-trajectory (roboticstoolbox-python backend).
 *
 * @param positions - Array of [x, y, z] in meters
 * @param toolLength - end effector length in meters
 * @returns Trajectory result with all-unreachable (stub)
 */
export function solveTrajectoryIKLocal(
  positions: [number, number, number][],
  _toolLength: number = 0.15,
): {
  trajectory: number[][];
  reachability: boolean[];
  reachableCount: number;
  totalPoints: number;
  reachabilityPercent: number;
} {
  // Local stub — returns all-unreachable. Backend does the real solving.
  const trajectory = positions.map(() => [0, 0, 0, 0, 0, 0]);
  const reachability = positions.map(() => false);

  return {
    trajectory,
    reachability,
    reachableCount: 0,
    totalPoints: positions.length,
    reachabilityPercent: 0,
  };
}
