/**
 * API client for OpenAxis backend
 */

const API_BASE_URL = 'http://localhost:8080/api';

export interface ApiResponse<T> {
  status: 'success' | 'error';
  data?: T;
  error?: string;
}

export interface GeometryData {
  id: string;
  filePath?: string;
  convertedPath?: string;
  format: string;
  converted: boolean;
  vertices?: number;
  faces?: number;
  dimensions?: {
    x: number;
    y: number;
    z: number;
  };
  center?: {
    x: number;
    y: number;
    z: number;
  };
}

export interface ToolpathSegment {
  type: string;
  layer: number;
  points: number[][];
  speed: number;
  extrusionRate: number;
}

export interface ToolpathData {
  id: string;
  layerHeight: number;
  totalLayers: number;
  processType: string;
  segments: ToolpathSegment[];
  statistics?: {
    totalSegments: number;
    totalPoints: number;
    layerCount: number;
    estimatedTime: number;
    estimatedMaterial: number;
  };
  params?: Record<string, any>;
}

export interface ToolpathParams {
  layerHeight?: number;
  extrusionWidth?: number;
  wallCount?: number;
  infillDensity?: number;
  infillPattern?: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`);
      return await response.json();
    } catch (error) {
      return {
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  async post<T>(endpoint: string, data: any): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      return await response.json();
    } catch (error) {
      return {
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  // Health check
  async health(): Promise<ApiResponse<{ version: string }>> {
    return this.get('/health');
  }

  // Geometry operations
  async importGeometry(filePath: string): Promise<ApiResponse<GeometryData>> {
    return this.post('/geometry/import', { filePath });
  }

  // Toolpath operations
  async generateToolpath(
    geometryPath: string,
    params?: ToolpathParams
  ): Promise<ApiResponse<ToolpathData>> {
    return this.post('/toolpath/generate', {
      geometryPath,
      params: params || {},
    });
  }

  async getToolpath(toolpathId: string): Promise<ApiResponse<ToolpathData>> {
    return this.get(`/toolpath/${toolpathId}`);
  }

  // Robot operations
  async getRobotState(): Promise<ApiResponse<any>> {
    return this.get('/robot/state');
  }

  async connectRobot(ipAddress: string, port: number): Promise<ApiResponse<any>> {
    return this.post('/robot/connect', { ipAddress, port });
  }

  async disconnectRobot(): Promise<ApiResponse<any>> {
    return this.post('/robot/disconnect', {});
  }

  // Monitoring
  async getSensorData(): Promise<ApiResponse<any>> {
    return this.get('/monitoring/sensors');
  }

  async getSystemData(): Promise<ApiResponse<any>> {
    return this.get('/monitoring/system');
  }
}

export const api = new ApiClient();
export default api;
