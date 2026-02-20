import { apiClient, ApiResponse } from './client';

export interface PipelineStepResult {
  name: string;
  success: boolean;
  error: string | null;
  duration: number;
}

export interface PipelineResult {
  success: boolean;
  toolpathData: any | null;
  simulationData: any | null;
  trajectoryData: any | null;
  errors: string[];
  timings: Record<string, number>;
  stepCompleted: string;
  steps: PipelineStepResult[];
}

/**
 * Execute the end-to-end manufacturing pipeline.
 *
 * Chains: geometry load -> slice -> simulation -> IK solve
 * Each step delegates to proven libraries via the backend service layer.
 *
 * @param geometryPath - Server-side path to geometry file
 * @param slicingParams - Slicing configuration parameters
 * @param tcpOffset - TCP offset [x, y, z, rx, ry, rz] in meters
 * @param partPosition - Part position [x, y, z] in mm
 */
export async function executePipeline(params: {
  geometryPath: string;
  slicingParams?: Record<string, any>;
  robotName?: string;
  tcpOffset?: number[];
  partPosition?: number[];
}): Promise<PipelineResult> {
  const response = await apiClient.post<ApiResponse<PipelineResult>>(
    '/api/pipeline/execute',
    params,
    { timeout: 600000 }, // 10 minutes — slicing + IK can be slow
  );
  if (response.data.status === 'success' && response.data.data) {
    return response.data.data;
  }
  throw new Error(response.data.error || 'Pipeline execution failed');
}
