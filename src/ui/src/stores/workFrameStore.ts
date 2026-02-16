/**
 * workFrameStore — Zustand store for work frames (coordinate systems).
 *
 * Work frames define coordinate systems for part placement and
 * post-processor output. Replaces the simple workTablePosition/Size.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

// ─── Types ────────────────────────────────────────────────────────────────────

export type AlignmentMethod =
  | 'manual'
  | 'z_plus_x'
  | 'z_plus_y'
  | 'x_plus_y'
  | '3planes'
  | 'offset'
  | 'project';

export interface WorkFrame {
  id: string;
  name: string;
  position: [number, number, number];     // mm, world coordinates
  rotation: [number, number, number];     // euler degrees
  size: [number, number, number];         // visual bounding box (m for scene)
  alignmentMethod: AlignmentMethod;
  childPartIds: string[];
  isDefault: boolean;
  visible: boolean;
  color: string;                          // hex color for gizmo
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

let _nextId = 1;
function generateFrameId(): string {
  return `wf_${Date.now()}_${_nextId++}`;
}

// ─── Default Frame ────────────────────────────────────────────────────────────

const DEFAULT_FRAME: WorkFrame = {
  id: 'default_workframe',
  name: 'Build Platform',
  position: [2000, 0, 0],       // 2m from robot in X (mm)
  rotation: [0, 0, 0],
  size: [1.5, 0.05, 1.5],       // meters (scene units for rendering)
  alignmentMethod: 'manual',
  childPartIds: [],
  isDefault: true,
  visible: true,
  color: '#3b82f6',
};

// ─── Store ───────────────────────────────────────────────────────────────────

interface WorkFrameState {
  frames: WorkFrame[];
  activeFrameId: string;

  // Actions
  addFrame: (name?: string) => string;
  removeFrame: (id: string) => void;
  updateFrame: (id: string, updates: Partial<WorkFrame>) => void;
  setActiveFrame: (id: string) => void;
  assignPartToFrame: (partId: string, frameId: string) => void;
  removePartFromFrame: (partId: string) => void;
  getActiveFrame: () => WorkFrame;
  getFrameForPart: (partId: string) => WorkFrame | undefined;

  // Position helpers (convert mm to scene meters)
  getFrameScenePosition: (id: string) => [number, number, number];
}

export const useWorkFrameStore = create<WorkFrameState>()(
  persist(
    immer((set, get) => ({
      frames: [DEFAULT_FRAME],
      activeFrameId: 'default_workframe',

      addFrame: (name?: string) => {
        const id = generateFrameId();
        const frameCount = get().frames.length;
        set((state) => {
          state.frames.push({
            id,
            name: name || `Work Frame ${frameCount + 1}`,
            position: [2000 + frameCount * 500, 0, 0],
            rotation: [0, 0, 0],
            size: [1.0, 0.05, 1.0],
            alignmentMethod: 'manual',
            childPartIds: [],
            isDefault: false,
            visible: true,
            color: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'][frameCount % 5],
          });
        });
        return id;
      },

      removeFrame: (id: string) => {
        const { frames } = get();
        const frame = frames.find((f) => f.id === id);
        if (!frame || frame.isDefault) return; // Cannot remove default frame

        set((state) => {
          // Move orphaned parts to default frame
          const removedFrame = state.frames.find((f) => f.id === id);
          if (removedFrame) {
            const defaultFrame = state.frames.find((f) => f.isDefault);
            if (defaultFrame) {
              defaultFrame.childPartIds.push(...removedFrame.childPartIds);
            }
          }
          state.frames = state.frames.filter((f) => f.id !== id);
          if (state.activeFrameId === id) {
            state.activeFrameId = state.frames[0]?.id || 'default_workframe';
          }
        });
      },

      updateFrame: (id: string, updates: Partial<WorkFrame>) => {
        set((state) => {
          const frame = state.frames.find((f) => f.id === id);
          if (frame) {
            Object.assign(frame, updates);
          }
        });
      },

      setActiveFrame: (id: string) => {
        set((state) => {
          state.activeFrameId = id;
        });
      },

      assignPartToFrame: (partId: string, frameId: string) => {
        set((state) => {
          // Remove from any existing frame
          for (const frame of state.frames) {
            frame.childPartIds = frame.childPartIds.filter((p) => p !== partId);
          }
          // Add to target frame
          const target = state.frames.find((f) => f.id === frameId);
          if (target) {
            target.childPartIds.push(partId);
          }
        });
      },

      removePartFromFrame: (partId: string) => {
        set((state) => {
          for (const frame of state.frames) {
            frame.childPartIds = frame.childPartIds.filter((p) => p !== partId);
          }
        });
      },

      getActiveFrame: () => {
        const { frames, activeFrameId } = get();
        return frames.find((f) => f.id === activeFrameId) || frames[0] || DEFAULT_FRAME;
      },

      getFrameForPart: (partId: string) => {
        const { frames } = get();
        return frames.find((f) => f.childPartIds.includes(partId));
      },

      getFrameScenePosition: (id: string) => {
        const { frames } = get();
        const frame = frames.find((f) => f.id === id);
        if (!frame) return [0, 0, 0];
        // Convert from mm (Z-up) to scene meters (Y-up)
        // mm Z-up: [x, y, z] → scene Y-up: [x*0.001, z*0.001, -y*0.001]
        return [
          frame.position[0] * 0.001,
          frame.position[2] * 0.001,
          -frame.position[1] * 0.001,
        ];
      },
    })),
    {
      name: 'openaxis-workframes',
      partialize: (state) => ({
        frames: state.frames,
        activeFrameId: state.activeFrameId,
      }),
    },
  ),
);
