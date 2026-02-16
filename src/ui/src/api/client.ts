import axios from 'axios';

export const API_BASE_URL = 'http://localhost:8080';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface ApiResponse<T = any> {
  status: 'success' | 'error' | 'ok';
  data?: T;
  error?: string;
  version?: string;
  services?: Record<string, boolean>;
}

/**
 * Check backend health and available services
 */
export async function checkHealth(): Promise<{
  ok: boolean;
  version: string;
  services: Record<string, boolean>;
}> {
  try {
    const response = await apiClient.get<ApiResponse>('/api/health', { timeout: 2000 });
    return {
      ok: response.data.status === 'ok',
      version: response.data.version || '0.0.0',
      services: response.data.services || {},
    };
  } catch {
    return { ok: false, version: '0.0.0', services: {} };
  }
}
