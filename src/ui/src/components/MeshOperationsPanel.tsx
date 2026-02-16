/**
 * MeshOperationsPanel — Boolean ops, mesh repair, and offset controls.
 *
 * Requires 2 selected parts for boolean operations.
 * Repair and offset work on a single selected part.
 */
import { useState, useCallback } from 'react';
import {
  ArrowPathIcon,
  ArrowsPointingOutIcon,
  PlusIcon,
  MinusIcon,
  ScissorsIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/react/24/outline';
import { useWorkspaceStore } from '../stores/workspaceStore';
import { apiClient } from '../api/client';

interface MeshOperationsPanelProps {
  compact?: boolean;
}

export default function MeshOperationsPanel({ compact = false }: MeshOperationsPanelProps) {
  const parts = useWorkspaceStore((s) => s.geometryParts);
  const selectedPartId = useWorkspaceStore((s) => s.selectedPartId);
  const [secondPartId, setSecondPartId] = useState<string | null>(null);
  const [offsetDistance, setOffsetDistance] = useState(1.0);
  const [notification, setNotification] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);

  const notify = useCallback((msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3000);
  }, []);

  const selectedPart = parts.find((p) => p.id === selectedPartId);
  const otherParts = parts.filter((p) => p.id !== selectedPartId);

  // Boolean operations
  const handleBoolean = async (operation: 'union' | 'subtract' | 'intersect') => {
    if (!selectedPartId || !secondPartId) {
      notify('Select two parts for boolean operation');
      return;
    }
    setIsProcessing(true);
    try {
      const response = await apiClient.post('/api/geometry/boolean', {
        geometryIdA: selectedPartId,
        geometryIdB: secondPartId,
        operation,
      });
      if (response.data?.status === 'success') {
        notify(`Boolean ${operation} successful`);
      } else {
        throw new Error(response.data?.error || 'Boolean operation failed');
      }
    } catch (err: any) {
      notify(`Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Mesh repair
  const handleRepair = async () => {
    if (!selectedPartId) {
      notify('Select a part to repair');
      return;
    }
    setIsProcessing(true);
    try {
      const response = await apiClient.post('/api/geometry/repair', {
        geometryId: selectedPartId,
      });
      if (response.data?.status === 'success') {
        const report = response.data.data?.repairReport;
        const msg = report
          ? `Repaired: ${report.holes_filled} holes filled, ${report.degenerate_removed} degenerate faces removed`
          : 'Mesh repaired';
        notify(msg);
      } else {
        throw new Error(response.data?.error || 'Repair failed');
      }
    } catch (err: any) {
      notify(`Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Mesh offset
  const handleOffset = async () => {
    if (!selectedPartId) {
      notify('Select a part to offset');
      return;
    }
    setIsProcessing(true);
    try {
      const response = await apiClient.post('/api/geometry/offset', {
        geometryId: selectedPartId,
        distance: offsetDistance,
      });
      if (response.data?.status === 'success') {
        notify(`Offset by ${offsetDistance}mm applied`);
      } else {
        throw new Error(response.data?.error || 'Offset failed');
      }
    } catch (err: any) {
      notify(`Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Mesh analysis
  const handleAnalyze = async () => {
    if (!selectedPartId) {
      notify('Select a part to analyze');
      return;
    }
    setIsProcessing(true);
    try {
      const response = await apiClient.post('/api/geometry/analyze', {
        geometryId: selectedPartId,
      });
      if (response.data?.status === 'success') {
        setAnalysisResult(response.data.data);
        notify('Analysis complete');
      } else {
        throw new Error(response.data?.error || 'Analysis failed');
      }
    } catch (err: any) {
      notify(`Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Undo
  const handleUndo = async () => {
    if (!selectedPartId) return;
    try {
      const response = await apiClient.post('/api/geometry/undo', {
        geometryId: selectedPartId,
      });
      if (response.data?.status === 'success') {
        notify('Undo successful');
      }
    } catch (err: any) {
      notify(`Undo failed: ${err.message}`);
    }
  };

  if (!selectedPart && !compact) {
    return (
      <div className="p-3 text-xs text-gray-500 text-center">
        Select a part to access mesh operations.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Notification */}
      {notification && (
        <div className="px-3 py-2 bg-blue-600 text-white text-xs rounded-lg">
          {notification}
        </div>
      )}

      {/* Boolean Operations */}
      <div>
        <h4 className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-1">
          <ScissorsIcon className="w-3.5 h-3.5" />
          Boolean Operations
        </h4>
        <div className="space-y-2">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Second Part:</label>
            <select
              value={secondPartId || ''}
              onChange={(e) => setSecondPartId(e.target.value || null)}
              className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
              disabled={otherParts.length === 0}
            >
              <option value="">— Select —</option>
              {otherParts.map((p) => (
                <option key={p.id} value={p.id}>{p.name || p.id}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-3 gap-1">
            <button
              onClick={() => handleBoolean('union')}
              disabled={!secondPartId || isProcessing}
              className="px-2 py-1.5 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <PlusIcon className="w-3 h-3 inline mr-0.5" />
              Union
            </button>
            <button
              onClick={() => handleBoolean('subtract')}
              disabled={!secondPartId || isProcessing}
              className="px-2 py-1.5 text-xs bg-orange-50 text-orange-700 border border-orange-200 rounded hover:bg-orange-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <MinusIcon className="w-3 h-3 inline mr-0.5" />
              Subtract
            </button>
            <button
              onClick={() => handleBoolean('intersect')}
              disabled={!secondPartId || isProcessing}
              className="px-2 py-1.5 text-xs bg-purple-50 text-purple-700 border border-purple-200 rounded hover:bg-purple-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ScissorsIcon className="w-3 h-3 inline mr-0.5" />
              Intersect
            </button>
          </div>
        </div>
      </div>

      {/* Repair */}
      <div>
        <h4 className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-1">
          <WrenchScrewdriverIcon className="w-3.5 h-3.5" />
          Repair &amp; Analyze
        </h4>
        <div className="flex gap-1">
          <button
            onClick={handleRepair}
            disabled={!selectedPartId || isProcessing}
            className="flex-1 px-2 py-1.5 text-xs bg-green-50 text-green-700 border border-green-200 rounded hover:bg-green-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <WrenchScrewdriverIcon className="w-3 h-3 inline mr-0.5" />
            Repair Mesh
          </button>
          <button
            onClick={handleAnalyze}
            disabled={!selectedPartId || isProcessing}
            className="flex-1 px-2 py-1.5 text-xs bg-gray-50 text-gray-700 border border-gray-200 rounded hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Analyze
          </button>
        </div>
      </div>

      {/* Analysis Result */}
      {analysisResult && (
        <div className="bg-gray-50 rounded p-2 text-xs space-y-1">
          <div className="flex justify-between">
            <span className="text-gray-500">Vertices:</span>
            <span className="font-medium">{analysisResult.vertex_count?.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Faces:</span>
            <span className="font-medium">{analysisResult.face_count?.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Watertight:</span>
            <span className={`font-medium ${analysisResult.is_watertight ? 'text-green-600' : 'text-red-600'}`}>
              {analysisResult.is_watertight ? 'Yes' : 'No'}
            </span>
          </div>
          {analysisResult.volume != null && (
            <div className="flex justify-between">
              <span className="text-gray-500">Volume:</span>
              <span className="font-medium">{analysisResult.volume.toFixed(1)} mm³</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-gray-500">Surface Area:</span>
            <span className="font-medium">{analysisResult.surface_area?.toFixed(1)} mm²</span>
          </div>
        </div>
      )}

      {/* Offset */}
      <div>
        <h4 className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-1">
          <ArrowsPointingOutIcon className="w-3.5 h-3.5" />
          Mesh Offset
        </h4>
        <div className="flex items-center gap-2">
          <input
            type="number"
            step="0.5"
            value={offsetDistance}
            onChange={(e) => setOffsetDistance(parseFloat(e.target.value) || 0)}
            className="w-20 px-2 py-1 text-xs border border-gray-300 rounded text-center"
          />
          <span className="text-xs text-gray-500">mm</span>
          <button
            onClick={handleOffset}
            disabled={!selectedPartId || isProcessing}
            className="flex-1 px-2 py-1.5 text-xs bg-indigo-50 text-indigo-700 border border-indigo-200 rounded hover:bg-indigo-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Apply Offset
          </button>
        </div>
      </div>

      {/* Undo */}
      <button
        onClick={handleUndo}
        disabled={!selectedPartId || isProcessing}
        className="w-full px-2 py-1.5 text-xs bg-gray-50 text-gray-600 border border-gray-200 rounded hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-1"
      >
        <ArrowPathIcon className="w-3 h-3" />
        Undo Last Operation
      </button>

      {/* Processing indicator */}
      {isProcessing && (
        <div className="text-xs text-blue-600 text-center animate-pulse">
          Processing...
        </div>
      )}
    </div>
  );
}
