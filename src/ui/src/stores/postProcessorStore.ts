/**
 * postProcessorStore — Persisted Zustand store for post processor configuration.
 *
 * Manages:
 * - Selected export format (gcode, rapid, krl, fanuc)
 * - Event hooks (customizable code snippets)
 * - Format-specific settings (speed, zone, blending, tool name)
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { persist } from 'zustand/middleware';

// ─── Types ───────────────────────────────────────────────────────────────────

export type ExportFormat = 'gcode' | 'rapid' | 'krl' | 'fanuc';

export interface EventHooks {
  programStart: string;
  programEnd: string;
  layerStart: string;
  layerEnd: string;
  processOn: string;
  processOff: string;
  beforePoint: string;
  afterPoint: string;
  toolChange: string;
  retract: string;
  prime: string;
}

export interface PostProcessorConfig {
  format: ExportFormat;
  programName: string;

  // Motion
  defaultSpeed: number;       // mm/min for G-code, mm/s for robot
  travelSpeed: number;
  approachSpeed: number;

  // Zone / blending
  zoneData: string;           // RAPID zone (fine, z0, z5, z10, z50, z100, z200)
  blending: number;           // KRL C_DIS or Fanuc CNT

  // Tool
  toolName: string;
  workObject: string;

  // Event hooks
  hooks: EventHooks;
}

export interface FormatInfo {
  id: ExportFormat;
  name: string;
  description: string;
  extension: string;
  vendor: string;
}

// ─── Store Interface ─────────────────────────────────────────────────────────

interface PostProcessorState {
  config: PostProcessorConfig;
  availableFormats: FormatInfo[];
  lastExportResult: {
    content: string;
    extension: string;
    lines: number;
    size: number;
  } | null;

  // Actions
  setFormat: (format: ExportFormat) => void;
  setConfig: (updates: Partial<PostProcessorConfig>) => void;
  setHook: (hook: keyof EventHooks, value: string) => void;
  setLastExportResult: (result: PostProcessorState['lastExportResult']) => void;
  resetConfig: () => void;
}

// ─── Defaults ────────────────────────────────────────────────────────────────

const defaultHooks: EventHooks = {
  programStart: '',
  programEnd: '',
  layerStart: '',
  layerEnd: '',
  processOn: '',
  processOff: '',
  beforePoint: '',
  afterPoint: '',
  toolChange: '',
  retract: '',
  prime: '',
};

const defaultConfig: PostProcessorConfig = {
  format: 'gcode',
  programName: 'OpenAxisProgram',
  defaultSpeed: 1000,
  travelSpeed: 5000,
  approachSpeed: 500,
  zoneData: 'z5',
  blending: 5.0,
  toolName: 'tool0',
  workObject: 'wobj0',
  hooks: { ...defaultHooks },
};

const defaultFormats: FormatInfo[] = [
  { id: 'gcode', name: 'G-code', description: 'Standard G-code for CNC and 3D printing', extension: '.gcode', vendor: 'Generic' },
  { id: 'rapid', name: 'ABB RAPID', description: 'ABB robot program with MoveL/MoveJ', extension: '.mod', vendor: 'ABB' },
  { id: 'krl', name: 'KUKA KRL', description: 'KUKA robot program with LIN/PTP', extension: '.src', vendor: 'KUKA' },
  { id: 'fanuc', name: 'Fanuc LS', description: 'Fanuc robot program with J/L instructions', extension: '.ls', vendor: 'Fanuc' },
];

// ─── Store ───────────────────────────────────────────────────────────────────

export const usePostProcessorStore = create<PostProcessorState>()(
  persist(
    immer((set) => ({
      config: { ...defaultConfig },
      availableFormats: defaultFormats,
      lastExportResult: null,

      setFormat: (format) =>
        set((state) => {
          state.config.format = format;
          // Apply format-specific defaults
          switch (format) {
            case 'rapid':
              state.config.toolName = 'tool0';
              state.config.workObject = 'wobj0';
              state.config.zoneData = 'z5';
              break;
            case 'krl':
              state.config.toolName = 'TOOL_DATA[1]';
              state.config.workObject = 'BASE_DATA[1]';
              state.config.blending = 5.0;
              break;
            case 'fanuc':
              state.config.toolName = 'UTOOL[1]';
              state.config.workObject = 'UFRAME[1]';
              state.config.blending = 50;
              break;
            case 'gcode':
              state.config.toolName = 'tool0';
              state.config.workObject = 'wobj0';
              break;
          }
        }),

      setConfig: (updates) =>
        set((state) => {
          Object.assign(state.config, updates);
        }),

      setHook: (hook, value) =>
        set((state) => {
          state.config.hooks[hook] = value;
        }),

      setLastExportResult: (result) =>
        set((state) => {
          state.lastExportResult = result;
        }),

      resetConfig: () =>
        set((state) => {
          state.config = { ...defaultConfig };
        }),
    })),
    {
      name: 'openaxis-postprocessor',
      partialize: (state) => ({
        config: state.config,
      }),
    }
  )
);
