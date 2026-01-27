/**
 * IPC utilities for communicating between Electron renderer and Python backend
 */

import type { IPCRequest, IPCResponse, APIResponse } from '../types';

// Check if we're running in Electron
const isElectron = typeof window !== 'undefined' && window.electron !== undefined;

/**
 * Send a request to the Python backend via Electron IPC
 */
export async function sendPythonRequest<T = any>(
  method: string,
  params?: any
): Promise<APIResponse<T>> {
  if (!isElectron) {
    // Fallback for development without Electron
    console.warn('Running without Electron, using mock data');
    return {
      status: 'success',
      data: {} as T,
    };
  }

  try {
    const response = await window.electron.invoke('python-request', {
      method,
      params,
    });

    return response;
  } catch (error) {
    console.error('IPC Error:', error);
    return {
      status: 'error',
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * API functions for interacting with the Python backend
 */
export const api = {
  // Project Management
  projects: {
    list: () => sendPythonRequest('projects.list'),
    get: (id: string) => sendPythonRequest('projects.get', { id }),
    create: (project: any) => sendPythonRequest('projects.create', project),
    update: (id: string, updates: any) => sendPythonRequest('projects.update', { id, ...updates }),
    delete: (id: string) => sendPythonRequest('projects.delete', { id }),
  },

  // Geometry Management
  geometry: {
    import: (filePath: string) => sendPythonRequest('geometry.import', { filePath }),
    export: (id: string, format: string) => sendPythonRequest('geometry.export', { id, format }),
    analyze: (id: string) => sendPythonRequest('geometry.analyze', { id }),
  },

  // Toolpath Generation
  toolpath: {
    generate: (geometryId: string, params: any) =>
      sendPythonRequest('toolpath.generate', { geometryId, params }),
    optimize: (toolpathId: string) => sendPythonRequest('toolpath.optimize', { toolpathId }),
    export: (toolpathId: string, format: string) =>
      sendPythonRequest('toolpath.export', { toolpathId, format }),
  },

  // Simulation
  simulation: {
    start: (toolpathId: string) => sendPythonRequest('simulation.start', { toolpathId }),
    step: (steps: number) => sendPythonRequest('simulation.step', { steps }),
    checkCollisions: () => sendPythonRequest('simulation.check_collisions'),
    getState: () => sendPythonRequest('simulation.get_state'),
  },

  // Robot Control
  robot: {
    connect: (ipAddress: string, port: number) =>
      sendPythonRequest('robot.connect', { ipAddress, port }),
    disconnect: () => sendPythonRequest('robot.disconnect'),
    getState: () => sendPythonRequest('robot.get_state'),
    home: () => sendPythonRequest('robot.home'),
    enable: () => sendPythonRequest('robot.enable'),
    disable: () => sendPythonRequest('robot.disable'),
    moveTo: (position: number[]) => sendPythonRequest('robot.move_to', { position }),
    executeToolpath: (toolpathId: string) =>
      sendPythonRequest('robot.execute_toolpath', { toolpathId }),
  },

  // Process Control
  process: {
    getParameters: (processType: string) =>
      sendPythonRequest('process.get_parameters', { processType }),
    setParameters: (processType: string, params: any) =>
      sendPythonRequest('process.set_parameters', { processType, params }),
    start: () => sendPythonRequest('process.start'),
    pause: () => sendPythonRequest('process.pause'),
    stop: () => sendPythonRequest('process.stop'),
  },

  // Monitoring
  monitoring: {
    getSensorData: () => sendPythonRequest('monitoring.get_sensor_data'),
    getSystemStatus: () => sendPythonRequest('monitoring.get_system_status'),
    getAlerts: () => sendPythonRequest('monitoring.get_alerts'),
    dismissAlert: (id: string) => sendPythonRequest('monitoring.dismiss_alert', { id }),
  },

  // Settings
  settings: {
    get: () => sendPythonRequest('settings.get'),
    update: (settings: any) => sendPythonRequest('settings.update', settings),
  },
};

/**
 * Subscribe to events from the Python backend
 */
export function subscribeToEvent(event: string, callback: (data: any) => void): () => void {
  if (!isElectron) {
    return () => {};
  }

  const handler = (_event: any, data: any) => callback(data);
  window.electron.on(event, handler);

  // Return unsubscribe function
  return () => {
    window.electron.off(event, handler);
  };
}

// Type declarations for Electron API
declare global {
  interface Window {
    electron: {
      invoke: (channel: string, ...args: any[]) => Promise<any>;
      on: (channel: string, callback: (...args: any[]) => void) => void;
      off: (channel: string, callback: (...args: any[]) => void) => void;
      send: (channel: string, ...args: any[]) => void;
    };
  }
}
