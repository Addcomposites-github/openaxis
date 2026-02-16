/**
 * GeometryPanel — Geometry import, part list, slicing (extracted from GeometryEditor.tsx).
 * Reads/writes to workspaceStore geometry state.
 */
import { useState, useRef, useEffect } from 'react';
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import {
  ArrowUpTrayIcon,
  EyeIcon,
  EyeSlashIcon,
  CubeIcon,
  AdjustmentsHorizontalIcon,
  ArrowsPointingOutIcon,
  ArrowPathIcon,
  MagnifyingGlassIcon,
  HomeIcon,
  TrashIcon,
  ChevronDoubleRightIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/react/24/outline';
import { useWorkspaceStore, storeGeometryFile, getGeometryFile, type GeometryPartData } from '../../stores/workspaceStore';
import { useProjectStore } from '../../stores/projectStore';
import SlicingParametersPanel, { type SlicingParameters } from '../SlicingParametersPanel';
import AdvancedSlicingPanel, { type SlicingParams, defaultSlicingParams } from '../AdvancedSlicingPanel';
import SlicingStrategySelector, { type SlicingStrategy } from '../SlicingStrategySelector';
import MeshOperationsPanel from '../MeshOperationsPanel';
import { centerOnPlate, checkBuildVolume, getDimensions, formatDimensions, computePlateOffsetAfterRotation } from '../../utils/geometryUtils';
import { generateToolpath, uploadGeometryFile, checkHealth } from '../../api/toolpath';

export default function GeometryPanel() {
  const parts = useWorkspaceStore((s) => s.geometryParts);
  const selectedPart = useWorkspaceStore((s) => s.selectedPartId);
  const transformMode = useWorkspaceStore((s) => s.transformMode);
  const addGeometryPart = useWorkspaceStore((s) => s.addGeometryPart);
  const removeGeometryPart = useWorkspaceStore((s) => s.removeGeometryPart);
  const updateGeometryPart = useWorkspaceStore((s) => s.updateGeometryPart);
  const setSelectedPartId = useWorkspaceStore((s) => s.setSelectedPartId);
  const setTransformMode = useWorkspaceStore((s) => s.setTransformMode);
  const setToolpathData = useWorkspaceStore((s) => s.setToolpathData);
  const toolpathStale = useWorkspaceStore((s) => s.toolpathStale);
  const setMode = useWorkspaceStore((s) => s.setMode);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [notification, setNotification] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [useAdvancedSlicing, setUseAdvancedSlicing] = useState(false);
  const [slicingParams, setSlicingParams] = useState<SlicingParameters>({
    layerHeight: 2.0,
    extrusionWidth: 2.5,
    wallCount: 2,
    infillDensity: 0.2,
    infillPattern: 'grid',
    processType: 'waam',
  });
  const [advancedParams, setAdvancedParams] = useState<SlicingParams>(defaultSlicingParams);
  const [slicingStrategy, setSlicingStrategy] = useState<SlicingStrategy>('planar');
  const [sliceAngle, setSliceAngle] = useState(30);
  const [supportEnabled, setSupportEnabled] = useState(false);
  const [supportThreshold, setSupportThreshold] = useState(45);
  const [meshOpsExpanded, setMeshOpsExpanded] = useState(false);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      switch (e.key.toLowerCase()) {
        case 'g': setTransformMode('translate'); break;
        case 'r': setTransformMode('rotate'); break;
        case 's': setTransformMode('scale'); break;
        case 'delete':
        case 'backspace':
          if (selectedPart) {
            removeGeometryPart(selectedPart);
          }
          break;
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedPart, setTransformMode, removeGeometryPart]);

  const handleImport = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    const fileName = file.name;
    const fileExtension = fileName.split('.').pop()?.toLowerCase();

    setNotification(`Loading ${fileName}...`);

    if (fileExtension === 'step' || fileExtension === 'stp') {
      setNotification('STEP files require backend processing. Using placeholder for now.');
      const newPart: GeometryPartData = {
        id: Date.now().toString(),
        name: fileName.replace(/\.[^/.]+$/, '') + ' (STEP)',
        visible: true,
        color: '#' + Math.floor(Math.random() * 16777215).toString(16),
        fileType: 'box',
        dimensions: { x: 50, y: 50, z: 50 },
      };
      addGeometryPart(newPart);
      setTimeout(() => setNotification(null), 3000);
      return;
    }

    const fileUrl = URL.createObjectURL(file);
    const fileType: 'stl' | 'obj' | 'box' =
      fileExtension === 'stl' ? 'stl' : fileExtension === 'obj' ? 'obj' : 'box';

    const loader = fileType === 'stl' ? new STLLoader() : new OBJLoader();

    loader.load(
      fileUrl,
      (result) => {
        let geometry: THREE.BufferGeometry | undefined;

        if (result instanceof THREE.BufferGeometry) {
          geometry = result;
        } else {
          (result as any).traverse((child: any) => {
            if (child instanceof THREE.Mesh && !geometry) {
              geometry = child.geometry;
            }
          });
        }

        if (geometry) {
          const plateSize = { x: 1000, y: 1000 };
          const autoPosition = centerOnPlate(geometry, plateSize);
          const posVec = new THREE.Vector3(autoPosition.x, autoPosition.y, autoPosition.z);
          const volumeCheck = checkBuildVolume(geometry, posVec, plateSize, 1000);
          const dimensions = getDimensions(geometry);

          const partId = Date.now().toString();
          const newPart: GeometryPartData = {
            id: partId,
            name: fileName.replace(/\.[^/.]+$/, ''),
            visible: true,
            color: volumeCheck.valid ? '#3b82f6' : '#ef4444',
            fileUrl,
            fileType,
            position: autoPosition,
            onPlate: Math.abs(autoPosition.y) < 1.0,
            boundsValid: volumeCheck.valid,
            dimensions: { x: dimensions.x, y: dimensions.y, z: dimensions.z },
          };

          addGeometryPart(newPart);
          storeGeometryFile(partId, file);
          setSelectedPartId(partId);

          if (volumeCheck.valid) {
            setNotification(`${fileName} loaded! ${formatDimensions(dimensions)}`);
          } else {
            setNotification(`Warning: ${volumeCheck.errors[0]}`);
          }
        } else {
          setNotification(`Error: Could not load geometry from ${fileName}`);
        }
        setTimeout(() => setNotification(null), 4000);
      },
      undefined,
      (error) => {
        console.error('Error loading file:', error);
        setNotification(`Error loading ${fileName}`);
        setTimeout(() => setNotification(null), 3000);
      }
    );

    // Reset file input
    if (event.target) event.target.value = '';
  };

  const handleCenterOnPlate = () => {
    if (!selectedPart) return;
    const part = parts.find((p) => p.id === selectedPart);
    if (!part) return;

    // Geometry vertices were centered and bottom-aligned at import time
    // (by centerOnPlate() in geometryUtils). When position is [0,0,0] and
    // rotation is [0,0,0], the part bottom is exactly at Y=0 (plate surface).
    //
    // If the part has been rotated, its bounding box changes and we need to
    // recompute the Y offset to place the bottom on the plate.
    const rot = part.rotation || { x: 0, y: 0, z: 0 };
    const hasRotation = rot.x !== 0 || rot.y !== 0 || rot.z !== 0;

    if (hasRotation && part.dimensions) {
      // Compute exact Y offset using rotated bounding box corners
      const yOffset = computePlateOffsetAfterRotation(part.dimensions, rot);
      updateGeometryPart(selectedPart, {
        position: { x: 0, y: yOffset, z: 0 },
      });
      setNotification('Part placed on build plate');
    } else {
      // No rotation: reset to origin restores import-time alignment
      updateGeometryPart(selectedPart, {
        position: { x: 0, y: 0, z: 0 },
        rotation: { x: 0, y: 0, z: 0 },
      });
      setNotification('Part centered on build plate');
    }
    setTimeout(() => setNotification(null), 2000);
  };

  const handleGenerateToolpath = async () => {
    const part = parts.find((p) => p.id === selectedPart);
    if (!part) {
      setNotification('No part selected. Please select a geometry part.');
      setTimeout(() => setNotification(null), 3000);
      return;
    }

    if (!part.fileUrl) {
      setNotification('Selected part has no geometry. Please import an STL or OBJ file.');
      setTimeout(() => setNotification(null), 3000);
      return;
    }

    setIsGenerating(true);
    setNotification('Checking backend connection...');

    try {
      const isHealthy = await checkHealth();
      if (!isHealthy) {
        setNotification('Backend not running. Start: python src/backend/server.py');
        setTimeout(() => setNotification(null), 5000);
        setIsGenerating(false);
        return;
      }

      // Get the raw file from our module-level store
      const rawFile = getGeometryFile(part.id);
      if (!rawFile) {
        setNotification('No geometry file available for upload. Please re-import.');
        setTimeout(() => setNotification(null), 3000);
        setIsGenerating(false);
        return;
      }

      setNotification('Uploading geometry to backend...');
      const geometryPath = await uploadGeometryFile(rawFile);

      // Ground check — position.y is height (Y-up convention in store).
      // If the part has been dragged below the plate surface, refuse to slice.
      const pos = part.position || { x: 0, y: 0, z: 0 };
      if (pos.y < -1) { // small tolerance
        setNotification('Cannot slice: part is below the build plate. Move it above the plate first.');
        setTimeout(() => setNotification(null), 5000);
        setIsGenerating(false);
        return;
      }

      setNotification('Generating toolpath...');
      // Convert store position (Y-up mm) to slicer position (Z-up mm).
      // Scene/store: X=left/right, Y=height, Z=depth
      // Slicer:      X=left/right, Y=depth,  Z=height
      // Mapping: slicer_x = store_x, slicer_y = store_z, slicer_z = store_y
      const slicerPos = { x: pos.x, y: pos.z, z: pos.y };

      console.log('[TOOLPATH-DEBUG] Store position (Y-up mm):', JSON.stringify(pos));
      console.log('[TOOLPATH-DEBUG] Slicer position (Z-up mm):', JSON.stringify(slicerPos));
      console.log('[TOOLPATH-DEBUG] Part dimensions:', JSON.stringify(part.dimensions));

      // Build API params — merge advanced params if in advanced mode
      const apiParams = useAdvancedSlicing
        ? {
            layerHeight: advancedParams.layerHeight,
            extrusionWidth: advancedParams.lineWidth,
            wallCount: advancedParams.wallCount,
            infillDensity: advancedParams.infillDensity / 100, // UI uses 0-100%, API uses 0-1
            infillPattern: advancedParams.infillPattern,
            processType: slicingParams.processType,
            // Advanced params
            wallWidth: advancedParams.wallWidth,
            printSpeed: advancedParams.printSpeed,
            seamMode: advancedParams.seamMode,
            seamShape: advancedParams.seamShape,
            seamAngle: advancedParams.seamAngle,
            travelSpeed: advancedParams.travelSpeed,
            zHop: advancedParams.zHop,
            retractDistance: advancedParams.retractDistance,
            retractSpeed: advancedParams.retractSpeed,
            leadInDistance: advancedParams.leadInDistance,
            leadInAngle: advancedParams.leadInAngle,
            leadOutDistance: advancedParams.leadOutDistance,
            leadOutAngle: advancedParams.leadOutAngle,
          }
        : slicingParams;

      // Attach strategy info + support config
      const finalParams = {
        ...apiParams,
        strategy: slicingStrategy,
        ...(slicingStrategy === 'angled' ? { sliceAngle } : {}),
        supportEnabled,
        supportThreshold,
      };

      const toolpathData = await generateToolpath(geometryPath, finalParams, slicerPos);

      // Store in workspace & project store
      setToolpathData(toolpathData);
      useProjectStore.getState().setWorkspaceToolpath(toolpathData);

      setNotification(
        `Toolpath generated! ${toolpathData.totalLayers} layers, ${toolpathData.statistics.totalSegments} segments`
      );

      setTimeout(() => {
        setNotification('Opening toolpath editor...');
        setTimeout(() => {
          setNotification(null);
          setMode('toolpath');
        }, 1000);
      }, 2000);
    } catch (error: any) {
      console.error('Error generating toolpath:', error);
      setNotification(`Error: ${error.message || 'Failed to generate toolpath'}`);
      setTimeout(() => setNotification(null), 5000);
    } finally {
      setIsGenerating(false);
    }
  };

  const handlePositionChange = (partId: string, axis: 'x' | 'y' | 'z', value: number) => {
    const part = parts.find((p) => p.id === partId);
    if (!part) return;
    updateGeometryPart(partId, {
      position: { ...(part.position || { x: 0, y: 0, z: 0 }), [axis]: value },
    });
  };

  const handleRotationChange = (partId: string, axis: 'x' | 'y' | 'z', valueDeg: number) => {
    const part = parts.find((p) => p.id === partId);
    if (!part) return;
    updateGeometryPart(partId, {
      rotation: { ...(part.rotation || { x: 0, y: 0, z: 0 }), [axis]: (valueDeg * Math.PI) / 180 },
    });
  };

  return (
    <div className="flex flex-col h-full">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".stl,.obj,.step,.stp"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Notification */}
      {notification && (
        <div className="mx-4 mt-3 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg">
          {notification}
        </div>
      )}

      {/* Viewport Toolbar (floating) */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-900">Geometry Parts</h3>
          <button
            onClick={handleImport}
            className="flex items-center space-x-1 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            <ArrowUpTrayIcon className="w-4 h-4" />
            <span>Import</span>
          </button>
        </div>

        {/* Transform Mode Controls */}
        <div className="flex items-center space-x-1">
          {[
            { mode: 'translate' as const, icon: ArrowsPointingOutIcon, label: 'Move (G)' },
            { mode: 'rotate' as const, icon: ArrowPathIcon, label: 'Rotate (R)' },
            { mode: 'scale' as const, icon: MagnifyingGlassIcon, label: 'Scale (S)' },
          ].map((item) => (
            <button
              key={item.mode}
              onClick={() => setTransformMode(item.mode)}
              className={`p-2 rounded transition-colors ${
                transformMode === item.mode
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
              title={item.label}
            >
              <item.icon className="w-4 h-4" />
            </button>
          ))}
          <div className="w-px h-6 bg-gray-300 mx-1" />
          <button
            onClick={handleCenterOnPlate}
            className="p-2 rounded bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
            title="Center on Plate"
            disabled={!selectedPart}
          >
            <HomeIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Parts List */}
      <div className="flex-1 overflow-auto">
        <div className="divide-y divide-gray-200">
          {parts.map((part) => (
            <div
              key={part.id}
              className={`p-4 hover:bg-gray-50 transition-colors cursor-pointer ${
                selectedPart === part.id ? 'bg-blue-50' : ''
              }`}
              onClick={() => setSelectedPartId(part.id)}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-3">
                  <CubeIcon className="w-5 h-5 text-gray-400" />
                  <span className="text-sm font-medium text-gray-900">{part.name}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      updateGeometryPart(part.id, { visible: !part.visible });
                    }}
                    className="p-1 hover:bg-gray-200 rounded transition-colors"
                    title="Toggle visibility"
                  >
                    {part.visible ? (
                      <EyeIcon className="w-4 h-4 text-gray-600" />
                    ) : (
                      <EyeSlashIcon className="w-4 h-4 text-gray-400" />
                    )}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeGeometryPart(part.id);
                    }}
                    className="p-1 hover:bg-red-100 rounded transition-colors"
                    title="Delete part"
                  >
                    <TrashIcon className="w-4 h-4 text-red-600" />
                  </button>
                </div>
              </div>

              {/* Expanded detail for selected part */}
              {selectedPart === part.id && (
                <div className="mt-3 space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Color</label>
                    <input
                      type="color"
                      value={part.color}
                      onChange={(e) => updateGeometryPart(part.id, { color: e.target.value })}
                      className="w-full h-8 rounded border border-gray-300"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Position (mm)</label>
                    <div className="grid grid-cols-3 gap-2">
                      {(['x', 'y', 'z'] as const).map((axis) => (
                        <div key={axis}>
                          <label className="text-xs text-gray-500">{axis.toUpperCase()}</label>
                          <input
                            type="number" step="0.1"
                            value={part.position?.[axis] || 0}
                            onChange={(e) => handlePositionChange(part.id, axis, parseFloat(e.target.value) || 0)}
                            className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Rotation (degrees)</label>
                    <div className="grid grid-cols-3 gap-2">
                      {(['x', 'y', 'z'] as const).map((axis) => (
                        <div key={axis}>
                          <label className="text-xs text-gray-500">{axis.toUpperCase()}</label>
                          <input
                            type="number" step="1"
                            value={part.rotation ? Math.round((part.rotation[axis] * 180) / Math.PI) : 0}
                            onChange={(e) => handleRotationChange(part.id, axis, parseFloat(e.target.value) || 0)}
                            className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
                    <button
                      onClick={handleCenterOnPlate}
                      className="w-full flex items-center justify-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium bg-green-600 text-white hover:bg-green-700 transition-colors"
                    >
                      <HomeIcon className="w-4 h-4" />
                      <span>Place on Build Plate</span>
                    </button>
                    <button
                      onClick={() => removeGeometryPart(part.id)}
                      className="w-full flex items-center justify-center space-x-2 px-3 py-2 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg text-sm font-medium transition-colors"
                    >
                      <TrashIcon className="w-4 h-4" />
                      <span>Delete Part</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Empty State */}
        {parts.length === 0 && (
          <div className="p-8 text-center">
            <CubeIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <h4 className="text-sm font-medium text-gray-900 mb-1">No Geometry Parts</h4>
            <p className="text-xs text-gray-500 mb-4">Import an STL or OBJ file to get started</p>
            <button
              onClick={handleImport}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
            >
              <ArrowUpTrayIcon className="w-4 h-4" />
              <span>Import Geometry</span>
            </button>
          </div>
        )}
      </div>

      {/* Mesh Operations (collapsible) */}
      <div className="border-t border-gray-200">
        <button
          onClick={() => setMeshOpsExpanded(!meshOpsExpanded)}
          className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center gap-1.5">
            <WrenchScrewdriverIcon className="w-4 h-4 text-gray-500" />
            <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Mesh Operations</h3>
          </div>
          {meshOpsExpanded ? (
            <ChevronDownIcon className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRightIcon className="w-4 h-4 text-gray-500" />
          )}
        </button>
        {meshOpsExpanded && (
          <div className="px-4 pb-3">
            <MeshOperationsPanel />
          </div>
        )}
      </div>

      {/* Slicing Parameters & Generate */}
      <div className="border-t border-gray-200">
        {/* Basic / Advanced toggle */}
        <div className="flex items-center justify-between px-4 pt-3 pb-1">
          <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Slicing</h3>
          <button
            onClick={() => setUseAdvancedSlicing(!useAdvancedSlicing)}
            className={`flex items-center gap-1 px-2 py-0.5 text-xs rounded-md border transition-colors ${
              useAdvancedSlicing
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-300 text-gray-600 hover:border-gray-400'
            }`}
          >
            <ChevronDoubleRightIcon className="w-3 h-3" />
            <span>{useAdvancedSlicing ? 'Advanced' : 'Basic'}</span>
          </button>
        </div>
        <div className="p-4 max-h-96 overflow-y-auto space-y-3">
          {/* Slicing Strategy Selector */}
          <SlicingStrategySelector
            strategy={slicingStrategy}
            onChange={setSlicingStrategy}
            angleParam={sliceAngle}
            onAngleChange={setSliceAngle}
          />

          {/* Support Generation Toggle */}
          <div className="bg-gray-50 rounded-lg p-3 space-y-2">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={supportEnabled}
                onChange={(e) => setSupportEnabled(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="text-xs font-medium text-gray-700">Enable Support Structures</span>
            </label>
            {supportEnabled && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs text-gray-600">Overhang Threshold</label>
                  <span className="text-xs text-gray-500">{supportThreshold}°</span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="80"
                  step="5"
                  value={supportThreshold}
                  onChange={(e) => setSupportThreshold(parseInt(e.target.value))}
                  className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-0.5">
                  <span>20°</span>
                  <span>80°</span>
                </div>
              </div>
            )}
          </div>

          {/* Parameter panels */}
          {useAdvancedSlicing ? (
            <AdvancedSlicingPanel params={advancedParams} onChange={setAdvancedParams} />
          ) : (
            <SlicingParametersPanel parameters={slicingParams} onChange={setSlicingParams} />
          )}
        </div>
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <button
            onClick={handleGenerateToolpath}
            disabled={isGenerating || !selectedPart}
            className={`w-full flex items-center justify-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
              isGenerating || !selectedPart
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : toolpathStale
                  ? 'bg-amber-500 text-white hover:bg-amber-600'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            <AdjustmentsHorizontalIcon className="w-5 h-5" />
            <span className="text-sm font-medium">
              {isGenerating ? 'Generating...' : toolpathStale ? 'Regenerate Toolpath' : 'Generate Toolpath'}
            </span>
          </button>
          <p className="text-xs text-center mt-2">
            {toolpathStale ? (
              <span className="text-amber-600 font-medium">Part moved — toolpath needs regeneration</span>
            ) : selectedPart ? (
              <span className="text-gray-500">Slice geometry into manufacturing path</span>
            ) : (
              <span className="text-gray-500">Select a part to generate toolpath</span>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
