import axios from 'axios';
import toast from 'react-hot-toast';

export const API_BASE_URL = 'http://localhost:8080';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Global error interceptor — shows toast for network failures and 5xx errors.
// Individual callers still receive the rejected promise for specific handling.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
      // Network error (backend unreachable)
      toast.error('Backend not reachable. Is the server running?', { id: 'network-error' });
    } else if (error.response.status >= 500) {
      const msg = error.response.data?.error || 'Internal server error';
      toast.error(`Server error: ${msg}`, { id: 'server-error' });
    }
    return Promise.reject(error);
  },
);

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
