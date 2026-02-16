/**
 * ToolpathPanel — Layer controls, statistics, color overlay, quality, export.
 * Reads/writes to workspaceStore toolpath state.
 */
import { useState, useCallback } from 'react';
import {
  ArrowLeftIcon,
  PlayIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  PencilSquareIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import LayerControls from '../LayerControls';
import ToolpathStatistics from '../ToolpathStatistics';
import ToolpathColorOverlay from '../ToolpathColorOverlay';
import QualityPanel from '../QualityPanel';
import PostProcessorPanel from '../PostProcessorPanel';
import ToolpathEditor from '../ToolpathEditor';
import AnalyticsPanel from '../AnalyticsPanel';

/** Strategy description lookup — explains what each slicing strategy does. */
const STRATEGY_DESCRIPTIONS: Record<string, string> = {
  planar: 'Horizontal layer-by-layer slicing perpendicular to Z axis',
  angled: 'Slice planes tilted at a custom angle for overhangs',
  radial: 'Concentric cylindrical paths radiating from center',
  curve: 'Non-planar layers following a guide curve surface',
  revolved: 'Helical paths for bodies of revolution',
};

export default function ToolpathPanel() {
  const toolpathData = useWorkspaceStore((s) => s.toolpathData);
  const toolpathStale = useWorkspaceStore((s) => s.toolpathStale);
  const rawCurrentLayer = useWorkspaceStore((s) => s.currentLayer);
  const showAllLayers = useWorkspaceStore((s) => s.showAllLayers);
  // Clamp to valid range (prevents stale persisted values from showing wrong layer)
  const currentLayer = toolpathData
    ? Math.max(0, Math.min(rawCurrentLayer, toolpathData.totalLayers - 1))
    : rawCurrentLayer;
  const setCurrentLayer = useWorkspaceStore((s) => s.setCurrentLayer);
  const setShowAllLayers = useWorkspaceStore((s) => s.setShowAllLayers);
  const setMode = useWorkspaceStore((s) => s.setMode);

  const [notification, _setNotification] = useState<string | null>(null);
  const [qualityExpanded, setQualityExpanded] = useState(false);
  const [exportExpanded, setExportExpanded] = useState(false);
  const [editorExpanded, setEditorExpanded] = useState(false);
  const [analyticsExpanded, setAnalyticsExpanded] = useState(false);
  const [selectedSegments, setSelectedSegments] = useState<Set<number>>(new Set());

  const handleSelectSegment = useCallback((index: number, add?: boolean) => {
    setSelectedSegments((prev) => {
      const next = new Set(add ? prev : []);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  const handleDeselectAll = useCallback(() => {
    setSelectedSegments(new Set());
  }, []);

  const handleBack = () => {
    setMode('geometry');
  };

  const handleSimulate = () => {
    setMode('simulation');
  };

  // No toolpath data — show empty state
  if (!toolpathData) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8">
        <h2 className="text-lg font-bold text-gray-900 mb-4">No Toolpath Data</h2>
        <p className="text-gray-600 mb-6 text-center text-sm">
          Generate a toolpath from the Geometry mode first.
        </p>
        <button
          onClick={handleBack}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Back to Geometry
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Toolpath Preview</h2>
            <p className="text-xs text-gray-500 mt-1">
              {toolpathData.statistics.totalSegments} segments,{' '}
              {toolpathData.statistics.totalPoints} points
            </p>
          </div>
          <button
            onClick={handleBack}
            className="flex items-center space-x-1 px-3 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm"
          >
            <ArrowLeftIcon className="w-4 h-4 text-gray-700" />
            <span className="text-gray-700">Back</span>
          </button>
        </div>
      </div>

      {/* Notification */}
      {notification && (
        <div className="mx-4 mt-3 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg">
          {notification}
        </div>
      )}

      {/* Stale Toolpath Warning */}
      {toolpathStale && (
        <div className="mx-4 mt-3 px-4 py-2 bg-amber-50 border border-amber-300 text-amber-800 text-sm rounded-lg flex items-center gap-2">
          <ExclamationTriangleIcon className="w-5 h-5 flex-shrink-0" />
          <div>
            <span className="font-medium">Toolpath outdated.</span>{' '}
            Part geometry has moved. Go back and regenerate.
          </div>
          <button
            onClick={handleBack}
            className="ml-auto px-2 py-1 text-xs font-medium bg-amber-200 hover:bg-amber-300 rounded transition-colors"
          >
            Regenerate
          </button>
        </div>
      )}

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Layer Controls */}
        <LayerControls
          totalLayers={toolpathData.totalLayers}
          currentLayer={currentLayer}
          onLayerChange={setCurrentLayer}
          showAllLayers={showAllLayers}
          onShowAllLayersChange={setShowAllLayers}
        />

        {/* Statistics */}
        <ToolpathStatistics
          statistics={toolpathData.statistics}
          layerHeight={toolpathData.layerHeight}
          processType={toolpathData.processType}
        />

        {/* Color Overlay Controls */}
        <ToolpathColorOverlay />

        {/* Toolpath Editor (collapsible) */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <button
            onClick={() => setEditorExpanded(!editorExpanded)}
            className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <PencilSquareIcon className="w-4 h-4 text-gray-500" />
              <h3 className="text-xs font-semibold text-gray-900">Edit Toolpath</h3>
            </div>
            {editorExpanded ? (
              <ChevronDownIcon className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRightIcon className="w-4 h-4 text-gray-500" />
            )}
          </button>
          {editorExpanded && (
            <div className="px-4 pb-4">
              <ToolpathEditor
                selectedSegments={selectedSegments}
                onSelectSegment={handleSelectSegment}
                onDeselectAll={handleDeselectAll}
              />
            </div>
          )}
        </div>

        {/* Toolpath Info */}
        <div className="bg-white rounded-lg shadow-md p-4">
          <h3 className="text-xs font-semibold text-gray-900 mb-2">Toolpath Info</h3>
          <div className="text-xs text-gray-700 space-y-1">
            <div className="flex justify-between">
              <span>Current Layer:</span>
              <span className="font-medium">
                {currentLayer + 1} / {toolpathData.totalLayers}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Layer Height:</span>
              <span className="font-medium">{toolpathData.layerHeight}mm</span>
            </div>
            <div className="flex justify-between">
              <span>Process:</span>
              <span className="font-medium uppercase">{toolpathData.processType}</span>
            </div>
            {toolpathData.params?.strategy && (
              <>
                <div className="flex justify-between">
                  <span>Strategy:</span>
                  <span className="font-medium capitalize">{toolpathData.params.strategy}</span>
                </div>
                {toolpathData.params.strategy === 'angled' && toolpathData.params.sliceAngle !== undefined && (
                  <div className="flex justify-between">
                    <span>Slice Angle:</span>
                    <span className="font-medium">{toolpathData.params.sliceAngle}°</span>
                  </div>
                )}
                <div className="mt-1 pt-1 border-t border-gray-100">
                  <p className="text-xs text-gray-500 italic">
                    {STRATEGY_DESCRIPTIONS[toolpathData.params.strategy] || 'Custom slicing strategy'}
                  </p>
                </div>
              </>
            )}
            {toolpathData.params?.infillDensity !== undefined && (
              <div className="flex justify-between">
                <span>Infill Density:</span>
                <span className="font-medium">{Math.round(toolpathData.params.infillDensity * 100)}%</span>
              </div>
            )}
            {toolpathData.params?.infillPattern && (
              <div className="flex justify-between">
                <span>Infill Pattern:</span>
                <span className="font-medium capitalize">{toolpathData.params.infillPattern}</span>
              </div>
            )}
          </div>
        </div>

        {/* Quality Report (collapsible) */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <button
            onClick={() => setQualityExpanded(!qualityExpanded)}
            className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
          >
            <h3 className="text-xs font-semibold text-gray-900">Quality Report</h3>
            {qualityExpanded ? (
              <ChevronDownIcon className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRightIcon className="w-4 h-4 text-gray-500" />
            )}
          </button>
          {qualityExpanded && (
            <div className="px-4 pb-4">
              <QualityPanel compact={false} />
            </div>
          )}
        </div>

        {/* Analytics (collapsible) */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <button
            onClick={() => setAnalyticsExpanded(!analyticsExpanded)}
            className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
          >
            <h3 className="text-xs font-semibold text-gray-900">Analytics</h3>
            {analyticsExpanded ? (
              <ChevronDownIcon className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRightIcon className="w-4 h-4 text-gray-500" />
            )}
          </button>
          {analyticsExpanded && (
            <div className="px-4 pb-4">
              <AnalyticsPanel />
            </div>
          )}
        </div>

        {/* Parameters Used */}
        {toolpathData.params && (
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Slicing Parameters</h3>
            <div className="space-y-2 text-xs">
              {Object.entries(toolpathData.params).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-gray-600 capitalize">{key.replace(/([A-Z])/g, ' $1').trim()}:</span>
                  <span className="font-medium text-gray-900">
                    {typeof value === 'number' ? (value as number).toFixed(2) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Export / Post Processor (collapsible) */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <button
            onClick={() => setExportExpanded(!exportExpanded)}
            className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
          >
            <h3 className="text-xs font-semibold text-gray-900">Export / Post Processor</h3>
            {exportExpanded ? (
              <ChevronDownIcon className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRightIcon className="w-4 h-4 text-gray-500" />
            )}
          </button>
          {exportExpanded && (
            <div className="px-4 pb-4">
              <PostProcessorPanel />
            </div>
          )}
        </div>
      </div>

      {/* Footer Actions */}
      <div className="border-t border-gray-200 p-4 bg-gray-50 space-y-2">
        <button
          onClick={handleSimulate}
          className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          <PlayIcon className="w-5 h-5" />
          <span className="text-sm font-medium">Simulate Toolpath</span>
        </button>
      </div>
    </div>
  );
}
