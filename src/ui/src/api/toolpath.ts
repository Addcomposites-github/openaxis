import axios from 'axios';

const API_BASE_URL = 'http://localhost:8080';

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
 */
export async function generateToolpath(
  geometryPath: string,
  params: SlicingParams
): Promise<ToolpathData> {
  const response = await axios.post(`${API_BASE_URL}/api/toolpath/generate`, {
    geometryPath,
    params
  });

  if (response.data.status === 'success') {
    return response.data.data;
  } else {
    throw new Error(response.data.error || 'Failed to generate toolpath');
  }
}

/**
 * Get toolpath by ID
 */
export async function getToolpath(toolpathId: string): Promise<ToolpathData> {
  const response = await axios.get(`${API_BASE_URL}/api/toolpath/${toolpathId}`);

  if (response.data.status === 'success') {
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
  const response = await axios.post(`${API_BASE_URL}/api/toolpath/export-gcode`, {
    toolpathId,
    outputPath
  });

  if (response.data.status === 'success') {
    return response.data.data.gcodeFile;
  } else {
    throw new Error(response.data.error || 'Failed to export G-code');
  }
}

/**
 * Check backend health
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/health`, {
      timeout: 2000
    });
    return response.data.status === 'ok';
  } catch (error) {
    return false;
  }
}
