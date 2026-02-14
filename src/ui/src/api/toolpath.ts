import { apiClient, ApiResponse, checkHealth as checkHealthBase } from './client';

export interface ToolpathSegment {
  type: string;
  layer: number;
  points: [number, number, number][];
  speed: number;
  extrusionRate: number;
}

export interface ToolpathData {
  id: string;
  layerHeight: number;
  totalLayers: number;
  processType: string;
  segments: ToolpathSegment[];
  statistics: {
    totalSegments: number;
    totalPoints: number;
    layerCount: number;
    estimatedTime: number;
    estimatedMaterial: number;
  };
  params: any;
}

export interface SlicingParams {
  layerHeight: number;
  extrusionWidth: number;
  wallCount: number;
  infillDensity: number;
  infillPattern: string;
  processType: string;
}

/**
 * Generate toolpath from geometry file
 * @param partPosition Optional [x, y, z] in mm (Z-up) to offset all waypoints
 */
export async function generateToolpath(
  geometryPath: string,
  params: SlicingParams,
  partPosition?: { x: number; y: number; z: number }
): Promise<ToolpathData> {
  const response = await apiClient.post<ApiResponse<ToolpathData>>('/api/toolpath/generate', {
    geometryPath,
    params,
    ...(partPosition && { partPosition: [partPosition.x, partPosition.y, partPosition.z] }),
  });

  if (response.data.status === 'success' && response.data.data) {
    return response.data.data;
  } else {
    throw new Error(response.data.error || 'Failed to generate toolpath');
  }
}

/**
 * Get toolpath by ID
 */
export async function getToolpath(toolpathId: string): Promise<ToolpathData> {
  const response = await apiClient.get<ApiResponse<ToolpathData>>(`/api/toolpath/${toolpathId}`);

  if (response.data.status === 'success' && response.data.data) {
    return response.data.data;
  } else {
    throw new Error(response.data.error || 'Toolpath not found');
  }
}

/**
 * Export toolpath as G-code
 */
export async function exportGCode(
  toolpathId: string,
  outputPath: string
): Promise<string> {
  const response = await apiClient.post<ApiResponse<{ gcodeFile: string; lines: number; size: number }>>('/api/toolpath/export-gcode', {
    toolpathId,
    outputPath
  });

  if (response.data.status === 'success' && response.data.data) {
    return response.data.data.gcodeFile;
  } else {
    throw new Error(response.data.error || 'Failed to export G-code');
  }
}

/**
 * Upload a geometry file to the backend and return the server-side path.
 */
export async function uploadGeometryFile(file: File): Promise<string> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<ApiResponse<{ serverPath: string }>>('/api/geometry/upload-file', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

  if (response.data.status === 'success' && response.data.data) {
    return response.data.data.serverPath;
  } else {
    throw new Error(response.data.error || 'Failed to upload geometry file');
  }
}

/**
 * Check backend health
 */
export async function checkHealth(): Promise<boolean> {
  const result = await checkHealthBase();
  return result.ok;
}
