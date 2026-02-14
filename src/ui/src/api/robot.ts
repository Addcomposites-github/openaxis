import { apiClient, ApiResponse } from './client';

export interface RobotConfig {
  name: string;
  manufacturer: string;
  type: string;
  baseFrame?: string;
  toolFrame?: string;
  urdfPath?: string;
  dof?: number;
  maxPayload?: number;
  maxReach?: number;
  jointLimits?: Record<string, Record<string, number>>;
  communication?: Record<string, any>;
}

export interface JointLimits {
  jointNames: string[];
  limits: Record<string, { min: number; max: number }>;
}

export interface FKResult {
  position: { x: number; y: number; z: number };
  orientation: { xaxis: number[]; yaxis: number[]; zaxis: number[] };
  valid: boolean;
  mock?: boolean;
  error?: string;
}

export interface IKResult {
  solution: number[] | null;
  jointNames?: string[];
  valid: boolean;
  error?: string;
}

export interface TrajectoryIKResult {
  trajectory: number[][];
  reachability: boolean[];
  reachableCount: number;
  totalPoints: number;
  reachabilityPercent: number;
  error?: string;
}

export interface RobotState {
  connected: boolean;
  enabled: boolean;
  moving: boolean;
  joint_positions: number[];
  tcp_position: number[];
  tcp_orientation: number[];
}

/**
 * Get robot configuration
 */
export async function getRobotConfig(robotName: string = 'abb_irb6700'): Promise<RobotConfig> {
  const response = await apiClient.get<ApiResponse<RobotConfig>>(`/api/robot/config?name=${robotName}`);
  if (response.data.status === 'success' && response.data.data) {
    return response.data.data;
  }
  throw new Error(response.data.error || 'Failed to get robot config');
}

/**
 * Get available robot configurations
 */
export async function getAvailableRobots(): Promise<string[]> {
  const response = await apiClient.get<ApiResponse<string[]>>('/api/robot/available');
  return response.data.data || [];
}

/**
 * Get joint limits for the current robot
 */
export async function getJointLimits(): Promise<JointLimits> {
  const response = await apiClient.get<ApiResponse<JointLimits>>('/api/robot/joint-limits');
  if (response.data.status === 'success' && response.data.data) {
    return response.data.data;
  }
  throw new Error(response.data.error || 'Failed to get joint limits');
}

/**
 * Get current robot state
 */
export async function getRobotState(): Promise<RobotState> {
  const response = await apiClient.get<ApiResponse<RobotState>>('/api/robot/state');
  if (response.data.status === 'success' && response.data.data) {
    return response.data.data;
  }
  throw new Error(response.data.error || 'Failed to get robot state');
}

/**
 * Load a robot model on the backend for IK operations
 */
export async function loadRobot(robotName: string = 'abb_irb6700'): Promise<boolean> {
  const response = await apiClient.post<ApiResponse>('/api/robot/load', { name: robotName });
  return response.data.status === 'success' && response.data.data?.loaded === true;
}

/**
 * Compute forward kinematics
 */
export async function computeFK(jointValues: number[]): Promise<FKResult> {
  const response = await apiClient.post<ApiResponse<FKResult>>('/api/robot/fk', { jointValues });
  if (response.data.status === 'success' && response.data.data) {
    return response.data.data;
  }
  throw new Error(response.data.error || 'FK computation failed');
}

/**
 * Compute inverse kinematics
 */
export async function computeIK(
  targetPosition: [number, number, number],
  targetOrientation?: number[],
  initialGuess?: number[]
): Promise<IKResult> {
  const response = await apiClient.post<ApiResponse<IKResult>>('/api/robot/ik', {
    targetPosition,
    targetOrientation,
    initialGuess,
  });
  if (response.data.status === 'success' && response.data.data) {
    return response.data.data;
  }
  throw new Error(response.data.error || 'IK computation failed');
}

/**
 * Solve IK for a full toolpath trajectory (batch)
 * @param tcpOffset - [x, y, z, rx, ry, rz] in meters/radians — shifts target so flange
 *                    reaches the position that places the tool tip at each waypoint
 */
export async function solveTrajectoryIK(
  waypoints: [number, number, number][],
  initialGuess?: number[],
  tcpOffset?: number[],
): Promise<TrajectoryIKResult> {
  const response = await apiClient.post<ApiResponse<TrajectoryIKResult>>('/api/robot/solve-trajectory', {
    waypoints,
    initialGuess,
    tcpOffset,
  }, { timeout: 300000 }); // 5 min — IK for large toolpaths can be slow
  if (response.data.status === 'success' && response.data.data) {
    return response.data.data;
  }
  throw new Error(response.data.error || 'Trajectory IK failed');
}
