import { apiClient, ApiResponse } from './client';

export interface GeometryData {
  id: string;
  filePath?: string;
  originalPath?: string;
  convertedPath?: string;
  format: string;
  converted?: boolean;
  convertedFormat?: string;
  vertices?: number;
  faces?: number;
  dimensions?: { x: number; y: number; z: number };
  center?: { x: number; y: number; z: number };
}

/**
 * Import geometry from a file path
 */
export async function importGeometry(filePath: string): Promise<GeometryData> {
  const response = await apiClient.post<ApiResponse<GeometryData>>('/api/geometry/import', {
    filePath,
  });
  if (response.data.status === 'success' && response.data.data) {
    return response.data.data;
  }
  throw new Error(response.data.error || 'Failed to import geometry');
}
