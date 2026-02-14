import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { persist } from 'zustand/middleware';
import type { RobotConfiguration, RobotState } from '../types';

interface RobotStoreState {
  configuration: RobotConfiguration | null;
  baseRotation: [number, number, number]; // degrees, for Z-up → Y-up conversion
  state: RobotState;
  isConnecting: boolean;

  // Actions
  setConfiguration: (config: RobotConfiguration) => void;
  setBaseRotation: (rotation: [number, number, number]) => void;
  setState: (state: Partial<RobotState>) => void;
  connect: (ipAddress: string, port: number) => Promise<void>;
  disconnect: () => Promise<void>;
  home: () => Promise<void>;
  enable: () => Promise<void>;
  disable: () => Promise<void>;
  moveTo: (position: [number, number, number]) => Promise<void>;
  updateJointPositions: (positions: number[]) => void;
  updateTCPPosition: (position: [number, number, number], orientation: [number, number, number]) => void;
}

export const useRobotStore = create<RobotStoreState>()(
  persist(
  immer((set, get) => ({
    configuration: null,
    baseRotation: [-90, 0, 0] as [number, number, number], // Default: Z-up URDF → Y-up Three.js
    state: {
      connected: false,
      enabled: false,
      moving: false,
      error: null,
      jointPositions: [0, 0, 0, 0, 0, 0],
      tcpPosition: [0, 0, 0],
      tcpOrientation: [0, 0, 0],
    },
    isConnecting: false,

    setConfiguration: (config) =>
      set((state) => {
        state.configuration = config;
      }),

    setBaseRotation: (rotation) =>
      set((state) => {
        state.baseRotation = rotation;
      }),

    setState: (updates) =>
      set((state) => {
        state.state = { ...state.state, ...updates };
      }),

    connect: async (ipAddress, port) => {
      set((state) => {
        state.isConnecting = true;
        state.state.error = null;
      });

      try {
        // TODO: Connect via Python backend
        // await window.electron.invoke('robot-connect', { ipAddress, port });

        // Simulate connection
        await new Promise((resolve) => setTimeout(resolve, 1000));

        set((state) => {
          state.state.connected = true;
          state.isConnecting = false;
        });
      } catch (error) {
        set((state) => {
          state.state.error = error instanceof Error ? error.message : 'Connection failed';
          state.state.connected = false;
          state.isConnecting = false;
        });
      }
    },

    disconnect: async () => {
      try {
        // TODO: Disconnect via Python backend
        // await window.electron.invoke('robot-disconnect');

        set((state) => {
          state.state.connected = false;
          state.state.enabled = false;
          state.state.moving = false;
        });
      } catch (error) {
        set((state) => {
          state.state.error = error instanceof Error ? error.message : 'Disconnect failed';
        });
      }
    },

    home: async () => {
      const { state: robotState } = get();
      if (!robotState.connected) {
        throw new Error('Robot not connected');
      }

      try {
        // TODO: Home via Python backend
        // await window.electron.invoke('robot-home');

        set((state) => {
          state.state.moving = true;
        });

        // Simulate homing
        await new Promise((resolve) => setTimeout(resolve, 2000));

        set((state) => {
          state.state.jointPositions = [0, 0, 0, 0, 0, 0];
          state.state.moving = false;
        });
      } catch (error) {
        set((state) => {
          state.state.error = error instanceof Error ? error.message : 'Homing failed';
          state.state.moving = false;
        });
      }
    },

    enable: async () => {
      try {
        // TODO: Enable via Python backend
        // await window.electron.invoke('robot-enable');

        set((state) => {
          state.state.enabled = true;
        });
      } catch (error) {
        set((state) => {
          state.state.error = error instanceof Error ? error.message : 'Enable failed';
        });
      }
    },

    disable: async () => {
      try {
        // TODO: Disable via Python backend
        // await window.electron.invoke('robot-disable');

        set((state) => {
          state.state.enabled = false;
        });
      } catch (error) {
        set((state) => {
          state.state.error = error instanceof Error ? error.message : 'Disable failed';
        });
      }
    },

    moveTo: async (position) => {
      const { state: robotState } = get();
      if (!robotState.connected || !robotState.enabled) {
        throw new Error('Robot not ready for motion');
      }

      try {
        // TODO: Move via Python backend
        // await window.electron.invoke('robot-move-to', position);

        set((state) => {
          state.state.moving = true;
        });

        // Simulate movement
        await new Promise((resolve) => setTimeout(resolve, 1500));

        set((state) => {
          state.state.tcpPosition = position;
          state.state.moving = false;
        });
      } catch (error) {
        set((state) => {
          state.state.error = error instanceof Error ? error.message : 'Movement failed';
          state.state.moving = false;
        });
      }
    },

    updateJointPositions: (positions) =>
      set((state) => {
        state.state.jointPositions = positions;
      }),

    updateTCPPosition: (position, orientation) =>
      set((state) => {
        state.state.tcpPosition = position;
        state.state.tcpOrientation = orientation;
      }),
  })),
  {
    name: 'openaxis-robot-store',
    partialize: (state) => ({
      configuration: state.configuration,
      baseRotation: state.baseRotation,
    }),
  })
);
