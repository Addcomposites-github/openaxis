import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { persist } from 'zustand/middleware';
import type { ToolpathSegment } from '../components/ToolpathRenderer';
import type { TrajectoryData } from '../api/simulation';

// ─── Types ───────────────────────────────────────────────────────────────────

export type WorkspaceMode = 'setup' | 'geometry' | 'toolpath' | 'simulation';

export interface CellSetup {
  robot: {
    basePosition: [number, number, number];
    baseRotation: [number, number, number]; // degrees
    model: string;
  };
  endEffector: {
    type: 'waam_torch' | 'pellet_extruder' | 'spindle' | 'none';
    offset: [number, number, number, number, number, number];
    mass: number;
  };
  externalAxis: {
    enabled: boolean;
    type: 'positioner_2axis' | 'linear_track' | 'turntable' | 'none';
    position: [number, number, number];
    rotation: [number, number, number];
  };
  workTableSize: [number, number, number];
  workTablePosition: [number, number, number];
}

/** Serializable part data (no THREE.Mesh refs). */
export interface GeometryPartData {
  id: string;
  name: string;
  visible: boolean;
  color: string;
  fileUrl?: string;
  fileType?: 'stl' | 'obj' | 'box';
  dimensions?: { x: number; y: number; z: number };
  position?: { x: number; y: number; z: number };
  rotation?: { x: number; y: number; z: number };
  scale?: { x: number; y: number; z: number };
  onPlate?: boolean;
  boundsValid?: boolean;
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
  params?: any;
}

export interface SimState {
  isRunning: boolean;
  currentTime: number;
  totalTime: number;
  speed: number;
  collisionDetected: boolean;
}

export type SimMode = 'manual' | 'toolpath';
export type IKStatus = 'idle' | 'computing' | 'ready' | 'failed' | 'fallback';

// ─── Store Interface ─────────────────────────────────────────────────────────

interface WorkspaceState {
  // Active mode (replaces route-based navigation for 3D pages)
  mode: WorkspaceMode;

  // Cell Setup (from RobotSetup)
  cellSetup: CellSetup;

  // Geometry (from GeometryEditor)
  geometryParts: GeometryPartData[];
  selectedPartId: string | null;
  transformMode: 'translate' | 'rotate' | 'scale';

  // Toolpath (from ToolpathEditor)
  toolpathData: ToolpathData | null;
  currentLayer: number;
  showAllLayers: boolean;

  // Simulation (from Simulation.tsx)
  simMode: SimMode;
  simState: SimState;
  jointAngles: Record<string, number>;
  jointTrajectory: number[][] | null;
  reachability: boolean[] | null;
  ikStatus: IKStatus;
  trajectory: TrajectoryData | null;

  // Actions — Mode
  setMode: (mode: WorkspaceMode) => void;

  // Actions — Cell Setup
  setCellSetup: (setup: CellSetup) => void;
  updateCellSetup: (updates: Partial<CellSetup>) => void;

  // Actions — Geometry
  addGeometryPart: (part: GeometryPartData) => void;
  removeGeometryPart: (id: string) => void;
  updateGeometryPart: (id: string, updates: Partial<GeometryPartData>) => void;
  setSelectedPartId: (id: string | null) => void;
  setTransformMode: (mode: 'translate' | 'rotate' | 'scale') => void;
  setGeometryParts: (parts: GeometryPartData[]) => void;

  // Actions — Toolpath
  setToolpathData: (data: ToolpathData | null) => void;
  setCurrentLayer: (layer: number) => void;
  setShowAllLayers: (show: boolean) => void;

  // Actions — Simulation
  setSimMode: (mode: SimMode) => void;
  setSimState: (updates: Partial<SimState>) => void;
  setJointAngles: (angles: Record<string, number>) => void;
  setJointAngle: (name: string, value: number) => void;
  setJointTrajectory: (traj: number[][] | null) => void;
  setReachability: (reach: boolean[] | null) => void;
  setIKStatus: (status: IKStatus) => void;
  setTrajectory: (traj: TrajectoryData | null) => void;
}

// ─── Default Values ──────────────────────────────────────────────────────────

const defaultCellSetup: CellSetup = {
  robot: {
    basePosition: [0, 0, 0],
    baseRotation: [-90, 0, 0],
    model: 'abb_irb6700',
  },
  endEffector: {
    type: 'waam_torch',
    offset: [0, 0, 0.15, 0, 0, 0],
    mass: 5.0,
  },
  externalAxis: {
    enabled: false,
    type: 'none',
    position: [0, 0, 0],
    rotation: [0, 0, 0],
  },
  workTableSize: [1.5, 0.05, 1.5],
  workTablePosition: [2, 0.025, 0],
};

const defaultJointAngles: Record<string, number> = {
  joint_1: 0.79,
  joint_2: -0.53,
  joint_3: 1.57,
  joint_4: 0,
  joint_5: 0.79,
  joint_6: 0,
};

// ─── Store ───────────────────────────────────────────────────────────────────

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    immer((set) => ({
      // ── Initial State ────────────────────────────────────────────────────

      mode: 'setup' as WorkspaceMode,
      cellSetup: defaultCellSetup,

      geometryParts: [],
      selectedPartId: null,
      transformMode: 'translate' as const,

      toolpathData: null,
      currentLayer: 0,
      showAllLayers: false,

      simMode: 'manual' as SimMode,
      simState: {
        isRunning: false,
        currentTime: 0,
        totalTime: 300,
        speed: 1.0,
        collisionDetected: false,
      },
      jointAngles: defaultJointAngles,
      jointTrajectory: null,
      reachability: null,
      ikStatus: 'idle' as IKStatus,
      trajectory: null,

      // ── Actions ──────────────────────────────────────────────────────────

      setMode: (mode) =>
        set((state) => {
          state.mode = mode;
        }),

      setCellSetup: (setup) =>
        set((state) => {
          state.cellSetup = setup;
        }),

      updateCellSetup: (updates) =>
        set((state) => {
          Object.assign(state.cellSetup, updates);
        }),

      addGeometryPart: (part) =>
        set((state) => {
          state.geometryParts.push(part);
        }),

      removeGeometryPart: (id) =>
        set((state) => {
          state.geometryParts = state.geometryParts.filter((p) => p.id !== id);
          if (state.selectedPartId === id) {
            state.selectedPartId = null;
          }
          // Clean up file from in-memory cache + IndexedDB (async, non-blocking)
          _geometryFiles.delete(id);
          _idbDelete(id).catch(() => {});
        }),

      updateGeometryPart: (id, updates) =>
        set((state) => {
          const idx = state.geometryParts.findIndex((p) => p.id === id);
          if (idx !== -1) {
            Object.assign(state.geometryParts[idx], updates);
          }
        }),

      setSelectedPartId: (id) =>
        set((state) => {
          state.selectedPartId = id;
        }),

      setTransformMode: (mode) =>
        set((state) => {
          state.transformMode = mode;
        }),

      setGeometryParts: (parts) =>
        set((state) => {
          state.geometryParts = parts;
        }),

      setToolpathData: (data) =>
        set((state) => {
          state.toolpathData = data;
        }),

      setCurrentLayer: (layer) =>
        set((state) => {
          state.currentLayer = layer;
        }),

      setShowAllLayers: (show) =>
        set((state) => {
          state.showAllLayers = show;
        }),

      setSimMode: (mode) =>
        set((state) => {
          state.simMode = mode;
        }),

      setSimState: (updates) =>
        set((state) => {
          Object.assign(state.simState, updates);
        }),

      setJointAngles: (angles) =>
        set((state) => {
          state.jointAngles = angles;
        }),

      setJointAngle: (name, value) =>
        set((state) => {
          state.jointAngles[name] = value;
        }),

      setJointTrajectory: (traj) =>
        set((state) => {
          state.jointTrajectory = traj;
        }),

      setReachability: (reach) =>
        set((state) => {
          state.reachability = reach;
        }),

      setIKStatus: (status) =>
        set((state) => {
          state.ikStatus = status;
        }),

      setTrajectory: (traj) =>
        set((state) => {
          // Skip if same reference (no-op)
          if (state.trajectory === traj) return;

          // Check if the trajectory data is equivalent (prevents duplicate API calls
          // in React strict mode from resetting IK state)
          const isEquivalent = traj && state.trajectory &&
            traj.totalTime === state.trajectory.totalTime &&
            traj.waypoints?.length === state.trajectory.waypoints?.length;

          if (isEquivalent) {
            // Same data, different object — just update the reference, don't reset IK
            state.trajectory = traj;
            return;
          }

          state.trajectory = traj;
          // Only reset IK state when trajectory genuinely changes
          state.jointTrajectory = null;
          state.reachability = null;
          state.ikStatus = 'idle';
        }),
    })),
    {
      name: 'openaxis-workspace',
      partialize: (state) => ({
        mode: state.mode,
        cellSetup: state.cellSetup,
        // Persist geometry part metadata but NOT file URLs (non-serializable blob URLs)
        geometryParts: state.geometryParts.map((p) => ({
          ...p,
          fileUrl: undefined, // blob URLs are not valid across sessions
        })),
        currentLayer: state.currentLayer,
        showAllLayers: state.showAllLayers,
        simMode: state.simMode,
        jointAngles: state.jointAngles,
      }),
    }
  )
);

// ─── Persistent geometry file store (IndexedDB + in-memory cache) ────────────
//
// Files are stored in IndexedDB so they survive page reloads.  The in-memory
// Map acts as a fast synchronous cache; on startup we hydrate it from IDB.

import {
  saveGeometryFile as _idbSave,
  loadAllGeometryFiles as _idbLoadAll,
  deleteGeometryFile as _idbDelete,
} from './geometryDB';

const _geometryFiles = new Map<string, File>();

/** Whether the initial hydration from IndexedDB has completed. */
let _hydrated = false;

/** Promise that resolves once hydration is done. Await this before any
 *  operation that requires geometry files to be available. */
let _hydratePromise: Promise<void> | null = null;

/**
 * Store a geometry file — writes to both the in-memory cache and IndexedDB.
 * The IDB write is fire-and-forget; the in-memory cache is updated synchronously.
 */
export function storeGeometryFile(partId: string, file: File) {
  _geometryFiles.set(partId, file);
  // Persist to IndexedDB in background (non-blocking)
  _idbSave(partId, file).catch((e) =>
    console.error('[GeometryStore] Failed to persist file to IndexedDB:', e),
  );
}

/**
 * Get a geometry file from the in-memory cache.
 * Returns undefined if the file hasn't been loaded/stored yet.
 */
export function getGeometryFile(partId: string): File | undefined {
  return _geometryFiles.get(partId);
}

/**
 * Remove a geometry file from both in-memory cache and IndexedDB.
 */
export function removeGeometryFile(partId: string) {
  _geometryFiles.delete(partId);
  _idbDelete(partId).catch((e) =>
    console.error('[GeometryStore] Failed to delete file from IndexedDB:', e),
  );
}

/**
 * Hydrate the in-memory file cache from IndexedDB.
 * Called once on app startup; also recreates blob URLs on the parts
 * in the workspace store.  Returns the number of files restored.
 */
export async function hydrateGeometryFiles(): Promise<number> {
  if (_hydrated) return _geometryFiles.size;

  if (!_hydratePromise) {
    _hydratePromise = (async () => {
      try {
        const files = await _idbLoadAll();
        const store = useWorkspaceStore.getState();
        const parts = store.geometryParts;
        let restored = 0;

        for (const [partId, file] of files) {
          _geometryFiles.set(partId, file);

          // Recreate blob URL on the matching part
          const part = parts.find((p) => p.id === partId);
          if (part && !part.fileUrl) {
            const blobUrl = URL.createObjectURL(file);
            store.updateGeometryPart(partId, { fileUrl: blobUrl });
            restored++;
          }
        }

        console.log(
          `[GeometryStore] Hydrated ${files.size} files from IndexedDB, ` +
          `restored blob URLs on ${restored} parts`,
        );
      } catch (e) {
        console.error('[GeometryStore] Hydration failed:', e);
      } finally {
        _hydrated = true;
      }
    })();
  }

  await _hydratePromise;
  return _geometryFiles.size;
}

/** Check whether geometry file hydration has completed. */
export function isGeometryHydrated(): boolean {
  return _hydrated;
}
