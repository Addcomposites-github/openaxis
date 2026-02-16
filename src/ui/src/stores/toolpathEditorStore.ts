/**
 * toolpathEditorStore — Zustand store for toolpath editing state.
 *
 * Manages segment selection, hover state, and an undo/redo modification stack.
 * This store is ephemeral (no persist middleware) — editor state resets on reload.
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ToolpathModification {
  type: string;
  segmentIndices: number[];
  previousValues: any;
  newValues: any;
  timestamp: number;
}

const MAX_MODIFICATION_STACK = 50;

// ─── Store Interface ──────────────────────────────────────────────────────────

interface ToolpathEditorState {
  // Selection
  selectedSegments: Set<number>;
  hoveredSegment: number | null;

  // Editing
  isEditing: boolean;

  // Undo / Redo
  modificationStack: ToolpathModification[];
  undoIndex: number; // current position in stack, -1 = nothing to undo

  // Computed
  canUndo: boolean;
  canRedo: boolean;

  // Actions — Selection
  selectSegment: (index: number, addToSelection?: boolean) => void;
  deselectAll: () => void;
  setHoveredSegment: (index: number | null) => void;

  // Actions — Editing
  setIsEditing: (editing: boolean) => void;

  // Actions — Undo / Redo
  pushModification: (mod: ToolpathModification) => void;
  undo: () => void;
  redo: () => void;
  clearHistory: () => void;
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useToolpathEditorStore = create<ToolpathEditorState>()(
  immer((set, get) => ({
    // ── Initial State ─────────────────────────────────────────────────────

    selectedSegments: new Set<number>(),
    hoveredSegment: null,
    isEditing: false,
    modificationStack: [],
    undoIndex: -1,

    // ── Computed ───────────────────────────────────────────────────────────

    get canUndo(): boolean {
      return get().undoIndex >= 0;
    },

    get canRedo(): boolean {
      const { undoIndex, modificationStack } = get();
      return undoIndex < modificationStack.length - 1;
    },

    // ── Actions — Selection ───────────────────────────────────────────────

    selectSegment: (index: number, addToSelection?: boolean) =>
      set((state) => {
        if (addToSelection) {
          state.selectedSegments.add(index);
        } else {
          state.selectedSegments = new Set<number>([index]);
        }
      }),

    deselectAll: () =>
      set((state) => {
        state.selectedSegments = new Set<number>();
      }),

    setHoveredSegment: (index: number | null) =>
      set((state) => {
        state.hoveredSegment = index;
      }),

    // ── Actions — Editing ─────────────────────────────────────────────────

    setIsEditing: (editing: boolean) =>
      set((state) => {
        state.isEditing = editing;
      }),

    // ── Actions — Undo / Redo ─────────────────────────────────────────────

    pushModification: (mod: ToolpathModification) =>
      set((state) => {
        // Discard any redo entries beyond the current position
        state.modificationStack = state.modificationStack.slice(
          0,
          state.undoIndex + 1,
        );

        // Push the new modification
        state.modificationStack.push(mod);

        // Enforce max stack size — drop oldest entries
        if (state.modificationStack.length > MAX_MODIFICATION_STACK) {
          const overflow =
            state.modificationStack.length - MAX_MODIFICATION_STACK;
          state.modificationStack = state.modificationStack.slice(overflow);
        }

        // undoIndex points at the newest entry
        state.undoIndex = state.modificationStack.length - 1;
      }),

    undo: () =>
      set((state) => {
        if (state.undoIndex >= 0) {
          state.undoIndex -= 1;
        }
      }),

    redo: () =>
      set((state) => {
        if (state.undoIndex < state.modificationStack.length - 1) {
          state.undoIndex += 1;
        }
      }),

    clearHistory: () =>
      set((state) => {
        state.modificationStack = [];
        state.undoIndex = -1;
      }),
  })),
);
