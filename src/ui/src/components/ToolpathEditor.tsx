/**
 * ToolpathEditor — Interactive toolpath segment editing panel.
 *
 * Provides:
 * - Segment selection info (type, layer, speed, points count)
 * - Speed override for selected segments
 * - Deposition rate override
 * - Reverse selected segments
 * - Delete selected segments
 * - Add delay to segment
 * - Undo/Redo stack
 */

import { useState, useCallback } from 'react';
import {
  ArrowPathIcon,
  TrashIcon,
  ArrowUturnLeftIcon,
  ArrowUturnRightIcon,
  BoltIcon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline';
import { useWorkspaceStore } from '../stores/workspaceStore';

// ─── Types ───────────────────────────────────────────────────────────────────

interface ToolpathModification {
  type: string;
  segmentIndices: number[];
  previousValues: any;
  newValues: any;
  timestamp: number;
}

// ─── ToolpathEditor Component ────────────────────────────────────────────────

interface ToolpathEditorProps {
  selectedSegments: Set<number>;
  onSelectSegment: (index: number, add?: boolean) => void;
  onDeselectAll: () => void;
}

export default function ToolpathEditor({
  selectedSegments,
  onSelectSegment: _onSelectSegment,
  onDeselectAll,
}: ToolpathEditorProps) {
  const toolpathData = useWorkspaceStore((s) => s.toolpathData);
  const setToolpathData = useWorkspaceStore((s) => s.setToolpathData);

  const [modificationStack, setModificationStack] = useState<ToolpathModification[]>([]);
  const [undoIndex, setUndoIndex] = useState(-1);
  const [speedOverride, setSpeedOverride] = useState<string>('');
  const [depositionOverride, setDepositionOverride] = useState<string>('');
  const [_delayValue, _setDelayValue] = useState<string>('0.5');

  const canUndo = undoIndex >= 0;
  const canRedo = undoIndex < modificationStack.length - 1;

  const selectedCount = selectedSegments.size;
  const segments = toolpathData?.segments || [];

  // Get info about selected segments
  const selectedInfo = Array.from(selectedSegments).map((idx) => segments[idx]).filter(Boolean);
  const selectedTypes = [...new Set(selectedInfo.map((s) => s.type))];
  const selectedLayers = [...new Set(selectedInfo.map((s) => s.layer))];
  const totalPoints = selectedInfo.reduce((sum, s) => sum + (s.points?.length || 0), 0);
  const avgSpeed = selectedInfo.length > 0
    ? selectedInfo.reduce((sum, s) => sum + (s.speed || 0), 0) / selectedInfo.length
    : 0;

  // Push a modification to the stack (truncates any redo history)
  const pushMod = useCallback((mod: ToolpathModification) => {
    setModificationStack((prev) => {
      const truncated = prev.slice(0, undoIndex + 1);
      const updated = [...truncated, mod].slice(-50); // Max 50 entries
      setUndoIndex(updated.length - 1);
      return updated;
    });
  }, [undoIndex]);

  // Apply speed override
  const handleSpeedOverride = () => {
    if (!toolpathData || selectedCount === 0) return;
    const newSpeed = parseFloat(speedOverride);
    if (isNaN(newSpeed) || newSpeed <= 0) return;

    const indices = Array.from(selectedSegments);
    const prevValues = indices.map((i) => segments[i]?.speed);

    const newSegments = [...segments];
    for (const idx of indices) {
      if (newSegments[idx]) {
        newSegments[idx] = { ...newSegments[idx], speed: newSpeed };
      }
    }

    setToolpathData({ ...toolpathData, segments: newSegments });
    pushMod({
      type: 'speed_override',
      segmentIndices: indices,
      previousValues: prevValues,
      newValues: newSpeed,
      timestamp: Date.now(),
    });
    setSpeedOverride('');
  };

  // Apply deposition override
  const handleDepositionOverride = () => {
    if (!toolpathData || selectedCount === 0) return;
    const newRate = parseFloat(depositionOverride);
    if (isNaN(newRate) || newRate < 0) return;

    const indices = Array.from(selectedSegments);
    const prevValues = indices.map((i) => segments[i]?.extrusionRate);

    const newSegments = [...segments];
    for (const idx of indices) {
      if (newSegments[idx]) {
        newSegments[idx] = { ...newSegments[idx], extrusionRate: newRate };
      }
    }

    setToolpathData({ ...toolpathData, segments: newSegments });
    pushMod({
      type: 'deposition_override',
      segmentIndices: indices,
      previousValues: prevValues,
      newValues: newRate,
      timestamp: Date.now(),
    });
    setDepositionOverride('');
  };

  // Reverse selected segments
  const handleReverse = () => {
    if (!toolpathData || selectedCount === 0) return;

    const indices = Array.from(selectedSegments);
    const newSegments = [...segments];

    for (const idx of indices) {
      if (newSegments[idx]?.points) {
        newSegments[idx] = {
          ...newSegments[idx],
          points: [...newSegments[idx].points].reverse(),
        };
      }
    }

    setToolpathData({ ...toolpathData, segments: newSegments });
    pushMod({
      type: 'reverse',
      segmentIndices: indices,
      previousValues: null,
      newValues: null,
      timestamp: Date.now(),
    });
  };

  // Delete selected segments
  const handleDelete = () => {
    if (!toolpathData || selectedCount === 0) return;

    const indices = new Set(selectedSegments);
    const deletedSegments = Array.from(indices).map((i) => ({ index: i, segment: segments[i] }));
    const newSegments = segments.filter((_: any, i: number) => !indices.has(i));

    const newStats = {
      ...toolpathData.statistics,
      totalSegments: newSegments.length,
      totalPoints: newSegments.reduce((sum: number, s: any) => sum + (s.points?.length || 0), 0),
    };

    setToolpathData({
      ...toolpathData,
      segments: newSegments,
      statistics: newStats,
    });
    onDeselectAll();
    pushMod({
      type: 'delete',
      segmentIndices: Array.from(indices),
      previousValues: deletedSegments,
      newValues: null,
      timestamp: Date.now(),
    });
  };

  // Undo
  const handleUndo = () => {
    if (!canUndo || !toolpathData) return;

    const mod = modificationStack[undoIndex];
    const newSegments = [...segments];

    switch (mod.type) {
      case 'speed_override':
        mod.segmentIndices.forEach((idx: number, i: number) => {
          if (newSegments[idx]) {
            newSegments[idx] = { ...newSegments[idx], speed: mod.previousValues[i] };
          }
        });
        setToolpathData({ ...toolpathData, segments: newSegments });
        break;
      case 'deposition_override':
        mod.segmentIndices.forEach((idx: number, i: number) => {
          if (newSegments[idx]) {
            newSegments[idx] = { ...newSegments[idx], extrusionRate: mod.previousValues[i] };
          }
        });
        setToolpathData({ ...toolpathData, segments: newSegments });
        break;
      case 'reverse':
        // Reverse again to undo
        mod.segmentIndices.forEach((idx: number) => {
          if (newSegments[idx]?.points) {
            newSegments[idx] = {
              ...newSegments[idx],
              points: [...newSegments[idx].points].reverse(),
            };
          }
        });
        setToolpathData({ ...toolpathData, segments: newSegments });
        break;
      case 'delete':
        // Re-insert deleted segments
        const restored = [...segments];
        for (const item of mod.previousValues) {
          restored.splice(item.index, 0, item.segment);
        }
        setToolpathData({
          ...toolpathData,
          segments: restored,
          statistics: {
            ...toolpathData.statistics,
            totalSegments: restored.length,
            totalPoints: restored.reduce((sum: number, s: any) => sum + (s.points?.length || 0), 0),
          },
        });
        break;
    }

    setUndoIndex((prev) => prev - 1);
  };

  // Redo
  const handleRedo = () => {
    if (!canRedo || !toolpathData) return;

    const mod = modificationStack[undoIndex + 1];
    const newSegments = [...segments];

    switch (mod.type) {
      case 'speed_override':
        mod.segmentIndices.forEach((idx: number) => {
          if (newSegments[idx]) {
            newSegments[idx] = { ...newSegments[idx], speed: mod.newValues };
          }
        });
        setToolpathData({ ...toolpathData, segments: newSegments });
        break;
      case 'deposition_override':
        mod.segmentIndices.forEach((idx: number) => {
          if (newSegments[idx]) {
            newSegments[idx] = { ...newSegments[idx], extrusionRate: mod.newValues };
          }
        });
        setToolpathData({ ...toolpathData, segments: newSegments });
        break;
      case 'reverse':
        mod.segmentIndices.forEach((idx: number) => {
          if (newSegments[idx]?.points) {
            newSegments[idx] = {
              ...newSegments[idx],
              points: [...newSegments[idx].points].reverse(),
            };
          }
        });
        setToolpathData({ ...toolpathData, segments: newSegments });
        break;
      case 'delete':
        const indices = new Set(mod.segmentIndices);
        const filtered = segments.filter((_: any, i: number) => !indices.has(i));
        setToolpathData({
          ...toolpathData,
          segments: filtered,
          statistics: {
            ...toolpathData.statistics,
            totalSegments: filtered.length,
            totalPoints: filtered.reduce((sum: number, s: any) => sum + (s.points?.length || 0), 0),
          },
        });
        break;
    }

    setUndoIndex((prev) => prev + 1);
  };

  if (!toolpathData) {
    return (
      <div className="p-4 text-center text-sm text-gray-500">
        No toolpath loaded. Generate a toolpath first.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Undo/Redo toolbar */}
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
          Toolpath Editor
        </h3>
        <div className="flex items-center gap-1">
          <button
            onClick={handleUndo}
            disabled={!canUndo}
            className={`p-1 rounded ${canUndo ? 'hover:bg-gray-200 text-gray-600' : 'text-gray-300'}`}
            title="Undo (Ctrl+Z)"
          >
            <ArrowUturnLeftIcon className="w-4 h-4" />
          </button>
          <button
            onClick={handleRedo}
            disabled={!canRedo}
            className={`p-1 rounded ${canRedo ? 'hover:bg-gray-200 text-gray-600' : 'text-gray-300'}`}
            title="Redo (Ctrl+Shift+Z)"
          >
            <ArrowUturnRightIcon className="w-4 h-4" />
          </button>
          <span className="text-xs text-gray-400 ml-1">
            {modificationStack.length > 0 ? `${undoIndex + 1}/${modificationStack.length}` : ''}
          </span>
        </div>
      </div>

      {/* Selection info */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
        {selectedCount > 0 ? (
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-900">
                {selectedCount} segment{selectedCount !== 1 ? 's' : ''} selected
              </span>
              <button
                onClick={onDeselectAll}
                className="text-xs text-blue-600 hover:text-blue-800"
              >
                Clear
              </button>
            </div>
            <div className="grid grid-cols-2 gap-x-4 text-xs text-gray-500">
              <span>Types: {selectedTypes.join(', ')}</span>
              <span>Layers: {selectedLayers.length === 1 ? selectedLayers[0] : `${selectedLayers.length} layers`}</span>
              <span>Points: {totalPoints}</span>
              <span>Avg Speed: {avgSpeed.toFixed(0)} mm/min</span>
            </div>
          </div>
        ) : (
          <p className="text-xs text-gray-500 text-center">
            Click segments in the 3D view to select them, or use the layer slider.
          </p>
        )}
      </div>

      {/* Speed Override */}
      <div className="space-y-1">
        <label className="flex items-center gap-1 text-xs font-medium text-gray-700">
          <BoltIcon className="w-3.5 h-3.5" />
          Speed Override
        </label>
        <div className="flex gap-1">
          <input
            type="number"
            placeholder={avgSpeed > 0 ? `Current: ${avgSpeed.toFixed(0)}` : 'mm/min'}
            value={speedOverride}
            onChange={(e) => setSpeedOverride(e.target.value)}
            className="flex-1 px-2 py-1.5 text-xs border border-gray-300 rounded-md font-mono"
            disabled={selectedCount === 0}
          />
          <button
            onClick={handleSpeedOverride}
            disabled={selectedCount === 0 || !speedOverride}
            className={`px-3 py-1.5 text-xs font-medium rounded-md ${
              selectedCount > 0 && speedOverride
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-200 text-gray-400'
            }`}
          >
            Apply
          </button>
        </div>
      </div>

      {/* Deposition Override */}
      <div className="space-y-1">
        <label className="flex items-center gap-1 text-xs font-medium text-gray-700">
          <AdjustmentsHorizontalIcon className="w-3.5 h-3.5" />
          Deposition Rate
        </label>
        <div className="flex gap-1">
          <input
            type="number"
            step="0.1"
            min="0"
            max="2"
            placeholder="0.0 - 2.0"
            value={depositionOverride}
            onChange={(e) => setDepositionOverride(e.target.value)}
            className="flex-1 px-2 py-1.5 text-xs border border-gray-300 rounded-md font-mono"
            disabled={selectedCount === 0}
          />
          <button
            onClick={handleDepositionOverride}
            disabled={selectedCount === 0 || !depositionOverride}
            className={`px-3 py-1.5 text-xs font-medium rounded-md ${
              selectedCount > 0 && depositionOverride
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-200 text-gray-400'
            }`}
          >
            Apply
          </button>
        </div>
      </div>

      {/* Action buttons */}
      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={handleReverse}
          disabled={selectedCount === 0}
          className={`flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border transition-colors ${
            selectedCount > 0
              ? 'border-orange-300 text-orange-700 bg-orange-50 hover:bg-orange-100'
              : 'border-gray-200 text-gray-400 bg-gray-50'
          }`}
        >
          <ArrowPathIcon className="w-3.5 h-3.5" />
          Reverse
        </button>
        <button
          onClick={handleDelete}
          disabled={selectedCount === 0}
          className={`flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border transition-colors ${
            selectedCount > 0
              ? 'border-red-300 text-red-700 bg-red-50 hover:bg-red-100'
              : 'border-gray-200 text-gray-400 bg-gray-50'
          }`}
        >
          <TrashIcon className="w-3.5 h-3.5" />
          Delete
        </button>
      </div>

      {/* Statistics */}
      <div className="border-t border-gray-200 pt-2">
        <div className="grid grid-cols-2 gap-1 text-xs text-gray-500">
          <span>Total segments: {segments.length}</span>
          <span>Modifications: {modificationStack.length}</span>
        </div>
      </div>
    </div>
  );
}
