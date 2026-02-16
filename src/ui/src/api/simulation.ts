import { apiClient, ApiResponse } from './client';

export interface SimulationInfo {
  id: string;
  status: 'ready' | 'playing' | 'stopped' | 'no_simulation';
  totalTime: number;
  currentTime?: number;
  speed?: number;
  totalWaypoints: number;
  totalSegments?: number;
  totalLayers?: number;
  progress?: number;
  error?: string;
}

export interface Waypoint {
  position: [number, number, number];
  time: number;
  segmentType: string;
  layer: number;
}

export interface TrajectoryData {
  waypoints: Waypoint[];
  totalTime: number;
  totalWaypoints: number;
}

/**
 * Create a new simulation from a toolpath
 */
export async function createSimulation(toolpathId: string): Promise<SimulationInfo> {
  const response = await apiClient.post<ApiResponse<SimulationInfo>>('/api/simulation/create', {
    toolpathId,
  });
  if (response.data.status === 'success' && response.data.data) {
    return response.data.data;
  }
  throw new Error(response.data.error || 'Failed to create simulation');
}

/**
 * Get current simulation state
 */
export async function getSimulationState(simId?: string): Promise<SimulationInfo> {
  const url = simId ? `/api/simulation/state?id=${simId}` : '/api/simulation/state';
  const response = await apiClient.get<ApiResponse<SimulationInfo>>(url);
  if (response.data.status === 'success' && response.data.data) {
    return response.data.data;
  }
  throw new Error(response.data.error || 'Failed to get simulation state');
}

/**
 * Get the full trajectory for playback
 */
export async function getTrajectory(simId?: string): Promise<TrajectoryData> {
  const url = simId ? `/api/simulation/trajectory?id=${simId}` : '/api/simulation/trajectory';
  const response = await apiClient.get<ApiResponse<TrajectoryData>>(url);
  if (response.data.status === 'success' && response.data.data) {
    return response.data.data;
  }
  throw new Error(response.data.error || 'Failed to get trajectory');
}

/**
 * Start simulation playback
 */
export async function startSimulation(toolpathId?: string): Promise<SimulationInfo> {
  const response = await apiClient.post<ApiResponse<SimulationInfo>>('/api/simulation/start', {
    toolpathId,
  });
  if (response.data.status === 'success' && response.data.data) {
    return response.data.data;
  }
  throw new Error(response.data.error || 'Failed to start simulation');
}

/**
 * Stop simulation playback
 */
export async function stopSimulation(): Promise<void> {
  await apiClient.post('/api/simulation/stop');
}

/**
 * List all simulations
 */
export async function listSimulations(): Promise<SimulationInfo[]> {
  const response = await apiClient.get<ApiResponse<SimulationInfo[]>>('/api/simulation/list');
  return response.data.data || [];
}
