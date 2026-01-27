import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type { SimulationState, SimulationWarning } from '../types';

interface SimulationStoreState extends SimulationState {
  // Actions
  start: () => void;
  pause: () => void;
  stop: () => void;
  resume: () => void;
  setSpeed: (speed: number) => void;
  setTime: (time: number) => void;
  setLayer: (layer: number) => void;
  addWarning: (warning: SimulationWarning) => void;
  clearWarnings: () => void;
  dismissWarning: (index: number) => void;
}

export const useSimulationStore = create<SimulationStoreState>()(
  immer((set, get) => ({
    isRunning: false,
    isPaused: false,
    currentTime: 0,
    totalTime: 300,
    speed: 1.0,
    currentLayer: 0,
    totalLayers: 50,
    collisionDetected: false,
    warnings: [],

    start: () =>
      set((state) => {
        state.isRunning = true;
        state.isPaused = false;
        state.currentTime = 0;
        state.warnings = [];
      }),

    pause: () =>
      set((state) => {
        state.isPaused = true;
      }),

    stop: () =>
      set((state) => {
        state.isRunning = false;
        state.isPaused = false;
        state.currentTime = 0;
        state.currentLayer = 0;
        state.collisionDetected = false;
      }),

    resume: () =>
      set((state) => {
        state.isPaused = false;
      }),

    setSpeed: (speed) =>
      set((state) => {
        state.speed = speed;
      }),

    setTime: (time) =>
      set((state) => {
        state.currentTime = Math.max(0, Math.min(time, state.totalTime));
        // Update layer based on time
        state.currentLayer = Math.floor((time / state.totalTime) * state.totalLayers);
      }),

    setLayer: (layer) =>
      set((state) => {
        state.currentLayer = Math.max(0, Math.min(layer, state.totalLayers));
        // Update time based on layer
        state.currentTime = (layer / state.totalLayers) * state.totalTime;
      }),

    addWarning: (warning) =>
      set((state) => {
        state.warnings.push(warning);
        if (warning.type === 'collision') {
          state.collisionDetected = true;
          state.isPaused = true;
        }
      }),

    clearWarnings: () =>
      set((state) => {
        state.warnings = [];
        state.collisionDetected = false;
      }),

    dismissWarning: (index) =>
      set((state) => {
        state.warnings.splice(index, 1);
        // Check if there are any remaining collision warnings
        state.collisionDetected = state.warnings.some((w) => w.type === 'collision');
      }),
  }))
);
