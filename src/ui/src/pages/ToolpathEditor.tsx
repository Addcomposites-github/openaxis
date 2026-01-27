import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, GizmoHelper, GizmoViewcube } from '@react-three/drei';
import {
  ArrowLeftIcon,
  DocumentArrowDownIcon,
} from '@heroicons/react/24/outline';
import BuildPlate from '../components/BuildPlate';
import ToolpathRenderer, { ToolpathSegment } from '../components/ToolpathRenderer';
import LayerControls from '../components/LayerControls';
import ToolpathStatistics from '../components/ToolpathStatistics';

interface ToolpathData {
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

function Scene({
  segments,
  currentLayer,
  showAllLayers
}: {
  segments: ToolpathSegment[];
  currentLayer: number;
  showAllLayers: boolean;
}) {
  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.6} />
      <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
      <directionalLight position={[-10, -10, -5]} intensity={0.3} />

      {/* Build Plate */}
      <BuildPlate size={{ x: 1000, y: 1000 }} maxHeight={1000} visible={true} />

      {/* Toolpath Visualization */}
      <ToolpathRenderer
        segments={segments}
        currentLayer={currentLayer}
        showAllLayers={showAllLayers}
        colorByType={true}
      />

      {/* Controls */}
      <OrbitControls makeDefault />

      {/* Gizmo */}
      <GizmoHelper alignment="bottom-right" margin={[80, 80]}>
        <GizmoViewcube />
      </GizmoHelper>
    </>
  );
}

export default function ToolpathEditor() {
  const navigate = useNavigate();
  const location = useLocation();

  // Get toolpath data from navigation state
  const [toolpathData, setToolpathData] = useState<ToolpathData | null>(
    location.state?.toolpathData || null
  );

  const [currentLayer, setCurrentLayer] = useState(0);
  const [showAllLayers, setShowAllLayers] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  // If no toolpath data, show message
  useEffect(() => {
    if (!toolpathData) {
      setNotification('No toolpath data loaded. Generate a toolpath first.');
    }
  }, [toolpathData]);

  const handleBack = () => {
    navigate('/geometry');
  };

  const handleExportGCode = async () => {
    if (!toolpathData) {
      setNotification('No toolpath to export');
      setTimeout(() => setNotification(null), 2000);
      return;
    }

    try {
      setNotification('Exporting G-code...');

      // TODO: Call backend API to export G-code
      // For now, create a simple G-code download

      const gcode = generateSimpleGCode(toolpathData);

      // Create blob and download
      const blob = new Blob([gcode], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `toolpath_${toolpathData.id}.gcode`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setNotification('G-code exported successfully!');
      setTimeout(() => setNotification(null), 3000);

    } catch (error: any) {
      console.error('Error exporting G-code:', error);
      setNotification(`Error: ${error.message}`);
      setTimeout(() => setNotification(null), 3000);
    }
  };

  const generateSimpleGCode = (data: ToolpathData): string => {
    let gcode = '; OpenAxis Generated G-code\n';
    gcode += `; Date: ${new Date().toISOString()}\n`;
    gcode += `; Process: ${data.processType}\n`;
    gcode += `; Layers: ${data.totalLayers}\n`;
    gcode += `; Layer Height: ${data.layerHeight}mm\n`;
    gcode += '\n; Start G-code\n';
    gcode += 'G21 ; Set units to millimeters\n';
    gcode += 'G90 ; Absolute positioning\n';
    gcode += 'G28 ; Home all axes\n';
    gcode += '\n';

    let currentZ = 0;
    data.segments.forEach((segment, idx) => {
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

    gcode += '\n; End G-code\n';
    gcode += 'G28 ; Home\n';
    gcode += 'M84 ; Disable motors\n';

    return gcode;
  };

  if (!toolpathData) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-100">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            No Toolpath Data
          </h2>
          <p className="text-gray-600 mb-6">
            Generate a toolpath from the Geometry Editor first.
          </p>
          <button
            onClick={handleBack}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Back to Geometry Editor
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* 3D Viewport */}
      <div className="flex-1 bg-gray-900 relative">
        <Canvas camera={{ position: [800, 600, 800], fov: 50 }} shadows>
          <Scene
            segments={toolpathData.segments}
            currentLayer={currentLayer}
            showAllLayers={showAllLayers}
          />
        </Canvas>

        {/* Top Bar */}
        <div className="absolute top-4 left-4 right-4 flex items-center justify-between">
          <button
            onClick={handleBack}
            className="flex items-center space-x-2 px-4 py-2 bg-white rounded-lg shadow-md hover:bg-gray-50 transition-colors"
          >
            <ArrowLeftIcon className="w-5 h-5 text-gray-700" />
            <span className="text-sm font-medium text-gray-700">Back</span>
          </button>

          <button
            onClick={handleExportGCode}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg shadow-md hover:bg-blue-700 transition-colors"
          >
            <DocumentArrowDownIcon className="w-5 h-5" />
            <span className="text-sm font-medium">Export G-code</span>
          </button>
        </div>

        {/* Notification */}
        {notification && (
          <div className="absolute top-20 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-6 py-3 rounded-lg shadow-lg z-50">
            {notification}
          </div>
        )}

        {/* Info Display */}
        <div className="absolute bottom-4 left-4 bg-white/90 rounded-lg shadow-md p-3 max-w-xs">
          <h3 className="text-xs font-semibold text-gray-900 mb-2">Toolpath Info</h3>
          <div className="text-xs text-gray-700 space-y-1">
            <div className="flex justify-between">
              <span>Current Layer:</span>
              <span className="font-medium">{currentLayer + 1} / {toolpathData.totalLayers}</span>
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
      </div>

      {/* Right Panel */}
      <div className="w-96 bg-white border-l border-gray-200 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Toolpath Preview</h2>
          <p className="text-xs text-gray-500 mt-1">
            {toolpathData.statistics.totalSegments} segments,{' '}
            {toolpathData.statistics.totalPoints} points
          </p>
        </div>

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

          {/* Parameters Used */}
          {toolpathData.params && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">
                Slicing Parameters
              </h3>
              <div className="space-y-2 text-xs">
                {Object.entries(toolpathData.params).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-gray-600 capitalize">
                      {key.replace(/([A-Z])/g, ' $1').trim()}:
                    </span>
                    <span className="font-medium text-gray-900">
                      {typeof value === 'number' ? value.toFixed(2) : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <button
            onClick={handleExportGCode}
            className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <DocumentArrowDownIcon className="w-5 h-5" />
            <span className="text-sm font-medium">Export G-code File</span>
          </button>
          <p className="text-xs text-gray-500 text-center mt-2">
            Download ready-to-use G-code
          </p>
        </div>
      </div>
    </div>
  );
}
