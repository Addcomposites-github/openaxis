/**
 * ToolpathPanel — Layer controls, statistics, export (extracted from ToolpathEditor.tsx).
 * Reads/writes to workspaceStore toolpath state.
 */
import { useState } from 'react';
import {
  ArrowLeftIcon,
  DocumentArrowDownIcon,
  PlayIcon,
} from '@heroicons/react/24/outline';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import LayerControls from '../LayerControls';
import ToolpathStatistics from '../ToolpathStatistics';
import { apiClient } from '../../api/client';

export default function ToolpathPanel() {
  const toolpathData = useWorkspaceStore((s) => s.toolpathData);
  const currentLayer = useWorkspaceStore((s) => s.currentLayer);
  const showAllLayers = useWorkspaceStore((s) => s.showAllLayers);
  const setCurrentLayer = useWorkspaceStore((s) => s.setCurrentLayer);
  const setShowAllLayers = useWorkspaceStore((s) => s.setShowAllLayers);
  const setMode = useWorkspaceStore((s) => s.setMode);

  const [notification, setNotification] = useState<string | null>(null);

  const handleBack = () => {
    setMode('geometry');
  };

  const handleSimulate = () => {
    setMode('simulation');
  };

  const handleExportGCode = async () => {
    if (!toolpathData) {
      setNotification('No toolpath to export');
      setTimeout(() => setNotification(null), 2000);
      return;
    }

    try {
      setNotification('Exporting G-code...');

      let gcode: string;

      try {
        const response = await apiClient.post('/api/toolpath/export-gcode', {
          toolpathId: toolpathData.id,
        });
        if (response.data?.status === 'success' && response.data?.data?.gcodeContent) {
          gcode = response.data.data.gcodeContent;
          setNotification('G-code exported via backend!');
        } else {
          throw new Error('Backend returned no G-code');
        }
      } catch {
        // Fallback to client-side generation
        gcode = generateSimpleGCode(toolpathData);
        setNotification('G-code exported (offline mode)');
      }

      const blob = new Blob([gcode], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `toolpath_${toolpathData.id}.gcode`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setTimeout(() => setNotification(null), 3000);
    } catch (error: any) {
      console.error('Error exporting G-code:', error);
      setNotification(`Error: ${error.message}`);
      setTimeout(() => setNotification(null), 3000);
    }
  };

  const generateSimpleGCode = (data: typeof toolpathData): string => {
    if (!data) return '';
    let gcode = '; OpenAxis Generated G-code\n';
    gcode += `; Date: ${new Date().toISOString()}\n`;
    gcode += `; Process: ${data.processType}\n`;
    gcode += `; Layers: ${data.totalLayers}\n`;
    gcode += `; Layer Height: ${data.layerHeight}mm\n`;
    gcode += '\n; Start G-code\n';
    gcode += 'G21 ; Set units to millimeters\n';
    gcode += 'G90 ; Absolute positioning\n';
    gcode += 'G28 ; Home all axes\n\n';

    let currentZ = 0;
    data.segments.forEach((segment) => {
      const layerZ = segment.layer * data.layerHeight;
      if (layerZ !== currentZ) {
        gcode += `\n; Layer ${segment.layer}\n`;
        gcode += `G0 Z${layerZ.toFixed(3)}\n`;
        currentZ = layerZ;
      }
      segment.points.forEach((point, pIdx) => {
        if (pIdx === 0) {
          gcode += `G0 X${point[0].toFixed(3)} Y${point[1].toFixed(3)} ; ${segment.type}\n`;
        } else {
          const feedrate = segment.speed || 1000;
          gcode += `G1 X${point[0].toFixed(3)} Y${point[1].toFixed(3)} F${feedrate.toFixed(0)}\n`;
        }
      });
    });

    gcode += '\n; End G-code\nG28 ; Home\nM84 ; Disable motors\n';
    return gcode;
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
          </div>
          <div className="mt-2 pt-2 border-t border-gray-200">
            <div className="flex items-center space-x-2 text-xs">
              <div className="w-3 h-3 bg-blue-500 rounded"></div>
              <span>Perimeter</span>
              <div className="w-3 h-3 bg-orange-500 rounded ml-2"></div>
              <span>Infill</span>
              <div className="w-3 h-3 bg-gray-400 rounded ml-2"></div>
              <span>Travel</span>
            </div>
          </div>
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
        <button
          onClick={handleExportGCode}
          className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <DocumentArrowDownIcon className="w-5 h-5" />
          <span className="text-sm font-medium">Export G-code File</span>
        </button>
      </div>
    </div>
  );
}
