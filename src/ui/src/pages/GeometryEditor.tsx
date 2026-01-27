import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Canvas, useLoader } from '@react-three/fiber';
import { OrbitControls, GizmoHelper, GizmoViewcube, TransformControls } from '@react-three/drei';
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
} from '@heroicons/react/24/outline';
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { useProjectStore } from '../stores/projectStore';
import BuildPlate from '../components/BuildPlate';
import SlicingParametersPanel, { SlicingParameters } from '../components/SlicingParametersPanel';
import { centerOnPlate, checkBuildVolume, getDimensions, formatDimensions } from '../utils/geometryUtils';
import { generateToolpath, checkHealth } from '../api/toolpath';

interface GeometryPart {
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
  onPlate?: boolean;  // Is part properly on build plate?
  boundsValid?: boolean;  // Is part within build volume?
  geometry?: THREE.BufferGeometry;  // Store loaded geometry for calculations
}

function GeometryMesh({ part }: { part: GeometryPart }) {
  let geometry: THREE.BufferGeometry | undefined;

  // Get transform properties
  const position = part.position || { x: 0, y: 0, z: 0 };
  const rotation = part.rotation || { x: 0, y: 0, z: 0 };
  const scale = part.scale || { x: 1, y: 1, z: 1 };

  // Try to load geometry from file if URL is provided
  if (part.fileUrl && part.fileType === 'stl') {
    try {
      geometry = useLoader(STLLoader, part.fileUrl);
    } catch (error) {
      console.error('Error loading STL:', error);
    }
  } else if (part.fileUrl && part.fileType === 'obj') {
    try {
      const obj = useLoader(OBJLoader, part.fileUrl);
      // Get first mesh from OBJ
      obj.traverse((child: any) => {
        if (child instanceof THREE.Mesh && !geometry) {
          geometry = child.geometry;
        }
      });
    } catch (error) {
      console.error('Error loading OBJ:', error);
    }
  }

  // Fallback to box if no geometry loaded
  if (!geometry) {
    const dims = part.dimensions || { x: 1, y: 1, z: 1 };
    return (
      <mesh
        visible={part.visible}
        position={[position.x, position.y, position.z]}
        rotation={[rotation.x, rotation.y, rotation.z]}
        scale={[scale.x, scale.y, scale.z]}
      >
        <boxGeometry args={[dims.x, dims.y, dims.z]} />
        <meshStandardMaterial color={part.color} />
      </mesh>
    );
  }

  return (
    <>
      <mesh
        visible={part.visible}
        geometry={geometry}
        position={[position.x, position.y, position.z]}
        rotation={[rotation.x, rotation.y, rotation.z]}
        scale={[scale.x, scale.y, scale.z]}
        castShadow
        receiveShadow
      >
        <meshStandardMaterial
          color={part.boundsValid === false ? '#ef4444' : part.color}
          emissive={part.boundsValid === false ? '#ef4444' : '#000000'}
          emissiveIntensity={part.boundsValid === false ? 0.3 : 0}
        />
      </mesh>

      {/* Show warning box if out of bounds */}
      {part.boundsValid === false && geometry && (
        <lineSegments
          position={[position.x, position.y, position.z]}
          rotation={[rotation.x, rotation.y, rotation.z]}
          scale={[scale.x, scale.y, scale.z]}
        >
          <edgesGeometry args={[geometry]} />
          <lineBasicMaterial color="#ef4444" linewidth={2} />
        </lineSegments>
      )}
    </>
  );
}

interface SceneProps {
  parts: GeometryPart[];
  selectedPartId: string | null;
  transformMode: 'translate' | 'rotate' | 'scale';
  onPartTransform: (partId: string, transform: {
    position?: { x: number; y: number; z: number };
    rotation?: { x: number; y: number; z: number };
    scale?: { x: number; y: number; z: number };
  }) => void;
  onPartSelect: (partId: string) => void;
}

function Scene({ parts, selectedPartId, transformMode, onPartTransform, onPartSelect }: SceneProps) {
  const [targetMesh, setTargetMesh] = useState<THREE.Object3D | null>(null);
  const orbitControlsRef = useRef<any>(null);

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
      <directionalLight position={[-10, -10, -5]} intensity={0.3} />

      {/* Build Plate - 1m x 1m manufacturing surface */}
      <BuildPlate size={{ x: 1000, y: 1000 }} maxHeight={1000} visible={true} />

      {/* Geometry Parts */}
      {parts.map((part) => (
        <group
          key={part.id}
          onClick={(e) => {
            e.stopPropagation();
            onPartSelect(part.id);
          }}
          onPointerOver={(e) => {
            e.stopPropagation();
            document.body.style.cursor = 'pointer';
          }}
          onPointerOut={(e) => {
            e.stopPropagation();
            document.body.style.cursor = 'default';
          }}
        >
          <mesh
            ref={(ref) => {
              if (part.id === selectedPartId && ref) {
                setTargetMesh(ref);
              }
            }}
            position={[
              part.position?.x || 0,
              part.position?.y || 0,
              part.position?.z || 0
            ]}
            rotation={[
              part.rotation?.x || 0,
              part.rotation?.y || 0,
              part.rotation?.z || 0
            ]}
            scale={[
              part.scale?.x || 1,
              part.scale?.y || 1,
              part.scale?.z || 1
            ]}
          >
            <GeometryMesh part={{ ...part, position: { x: 0, y: 0, z: 0 } }} />
          </mesh>
        </group>
      ))}

      {/* Transform Controls */}
      {selectedPartId && targetMesh && (
        <TransformControls
          object={targetMesh}
          mode={transformMode}
          onMouseDown={() => {
            if (orbitControlsRef.current) {
              orbitControlsRef.current.enabled = false;
            }
          }}
          onMouseUp={() => {
            if (orbitControlsRef.current) {
              orbitControlsRef.current.enabled = true;
            }
            // Update part transform
            if (targetMesh) {
              onPartTransform(selectedPartId, {
                position: {
                  x: targetMesh.position.x,
                  y: targetMesh.position.y,
                  z: targetMesh.position.z
                },
                rotation: {
                  x: targetMesh.rotation.x,
                  y: targetMesh.rotation.y,
                  z: targetMesh.rotation.z
                },
                scale: {
                  x: targetMesh.scale.x,
                  y: targetMesh.scale.y,
                  z: targetMesh.scale.z
                }
              });
            }
          }}
        />
      )}

      {/* Orbit Controls */}
      <OrbitControls ref={orbitControlsRef} makeDefault />

      {/* Gizmo */}
      <GizmoHelper alignment="bottom-right" margin={[80, 80]}>
        <GizmoViewcube />
      </GizmoHelper>
    </>
  );
}

export default function GeometryEditor() {
  const navigate = useNavigate();
  const { currentProject } = useProjectStore();
  const [parts, setParts] = useState<GeometryPart[]>([]);

  const [selectedPart, setSelectedPart] = useState<string | null>(null);
  const [transformMode, setTransformMode] = useState<'translate' | 'rotate' | 'scale'>('translate');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [notification, setNotification] = useState<string | null>(null);
  const [slicingParams, setSlicingParams] = useState<SlicingParameters>({
    layerHeight: 2.0,
    extrusionWidth: 2.5,
    wallCount: 2,
    infillDensity: 0.2,
    infillPattern: 'lines',
    processType: 'waam'
  });
  const [isGenerating, setIsGenerating] = useState(false);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (e.key.toLowerCase()) {
        case 'g':
          setTransformMode('translate');
          break;
        case 'r':
          setTransformMode('rotate');
          break;
        case 's':
          setTransformMode('scale');
          break;
        case 'delete':
        case 'backspace':
          if (selectedPart) {
            setParts(prev => prev.filter(p => p.id !== selectedPart));
            setSelectedPart(null);
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedPart]);

  const handleImport = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      const fileName = file.name;
      const fileExtension = fileName.split('.').pop()?.toLowerCase();

      setNotification(`Loading ${fileName}...`);

      // Check if it's a STEP file that needs backend conversion
      if (fileExtension === 'step' || fileExtension === 'stp') {
        setNotification(`Converting STEP file to STL...`);

        try {
          // For STEP files, we'll show a note about backend processing
          // In a full implementation, this would send to backend API
          setNotification(`STEP files require backend processing. Using placeholder for now.`);

          // Create placeholder for STEP (will be enhanced with real backend call)
          const newPart: GeometryPart = {
            id: Date.now().toString(),
            name: fileName.replace(/\.[^/.]+$/, "") + " (STEP - needs conversion)",
            visible: true,
            color: '#' + Math.floor(Math.random()*16777215).toString(16),
            fileType: 'box',
            dimensions: { x: 50, y: 50, z: 50 }
          };

          setParts(prev => [...prev, newPart]);
          setTimeout(() => setNotification(null), 3000);

        } catch (error) {
          console.error('Error processing STEP file:', error);
          setNotification('Error: STEP conversion requires backend service');
          setTimeout(() => setNotification(null), 3000);
        }
        return;
      }

      // For STL/OBJ - load directly with auto-placement
      const fileUrl = URL.createObjectURL(file);

      // Determine file type
      let fileType: 'stl' | 'obj' | 'box' = 'box';
      if (fileExtension === 'stl') {
        fileType = 'stl';
      } else if (fileExtension === 'obj') {
        fileType = 'obj';
      }

      // Load geometry to calculate auto-placement
      const loader = fileType === 'stl' ? new STLLoader() : new OBJLoader();

      loader.load(fileUrl, (result) => {
        let geometry: THREE.BufferGeometry | undefined;

        if (result instanceof THREE.BufferGeometry) {
          geometry = result;
        } else {
          // OBJ returns a group, get first mesh
          (result as any).traverse((child: any) => {
            if (child instanceof THREE.Mesh && !geometry) {
              geometry = child.geometry;
            }
          });
        }

        if (geometry) {
          // Calculate auto-placement on build plate
          const plateSize = { x: 1000, y: 1000 };
          const autoPosition = centerOnPlate(geometry, plateSize);

          // Check if it fits in build volume
          const posVec = new THREE.Vector3(autoPosition.x, autoPosition.y, autoPosition.z);
          const volumeCheck = checkBuildVolume(geometry, posVec, plateSize, 1000);

          // Get dimensions for display
          const dimensions = getDimensions(geometry);

          // Create part with auto-placement
          const newPart: GeometryPart = {
            id: Date.now().toString(),
            name: fileName.replace(/\.[^/.]+$/, ""),
            visible: true,
            color: volumeCheck.valid ? '#3b82f6' : '#ef4444',
            fileUrl: fileUrl,
            fileType: fileType,
            position: autoPosition,
            onPlate: Math.abs(autoPosition.z) < 1.0,
            boundsValid: volumeCheck.valid,
            geometry: geometry,
            dimensions: {
              x: dimensions.x,
              y: dimensions.y,
              z: dimensions.z
            }
          };

          setParts(prev => [...prev, newPart]);
          setSelectedPart(newPart.id);

          // Show appropriate notification
          if (volumeCheck.valid) {
            setNotification(`${fileName} loaded and placed on build plate! ${formatDimensions(dimensions)}`);
          } else {
            setNotification(`Warning: ${volumeCheck.errors[0]}`);
          }
        } else {
          setNotification(`Error: Could not load geometry from ${fileName}`);
        }

        setTimeout(() => setNotification(null), 4000);
      }, undefined, (error) => {
        console.error('Error loading file:', error);
        setNotification(`Error loading ${fileName}`);
        setTimeout(() => setNotification(null), 3000);
      });
    }
  };

  const handlePartTransform = (partId: string, transform: {
    position?: { x: number; y: number; z: number };
    rotation?: { x: number; y: number; z: number };
    scale?: { x: number; y: number; z: number };
  }) => {
    setParts((prev) =>
      prev.map((part) => {
        if (part.id === partId) {
          const updated = { ...part, ...transform };

          // Revalidate bounds after transform
          if (updated.geometry && transform.position) {
            const plateSize = { x: 1000, y: 1000 };
            const posVec = new THREE.Vector3(
              transform.position.x,
              transform.position.y,
              transform.position.z
            );
            const volumeCheck = checkBuildVolume(updated.geometry, posVec, plateSize, 1000);
            updated.boundsValid = volumeCheck.valid;
            updated.onPlate = Math.abs(transform.position.z) < 1.0;
            updated.color = volumeCheck.valid ? '#3b82f6' : '#ef4444';
          }

          return updated;
        }
        return part;
      })
    );
  };

  const handleCenterOnPlate = () => {
    const part = parts.find(p => p.id === selectedPart);
    if (!part || !part.geometry) {
      setNotification('No part selected or geometry not loaded');
      setTimeout(() => setNotification(null), 2000);
      return;
    }

    const plateSize = { x: 1000, y: 1000 };
    const centered = centerOnPlate(part.geometry, plateSize);

    handlePartTransform(part.id, { position: centered });

    setNotification('Part centered on build plate');
    setTimeout(() => setNotification(null), 2000);
  };

  const handleGenerateToolpath = async () => {
    // Validate we have a selected part
    const part = parts.find(p => p.id === selectedPart);
    if (!part) {
      setNotification('No part selected. Please select a geometry part.');
      setTimeout(() => setNotification(null), 3000);
      return;
    }

    // Check if part has geometry or file URL
    if (!part.fileUrl && !part.geometry) {
      setNotification('Selected part has no geometry. Please import an STL or OBJ file.');
      setTimeout(() => setNotification(null), 3000);
      return;
    }

    // Check bounds
    if (part.boundsValid === false) {
      setNotification('Cannot slice: Part exceeds build volume');
      setTimeout(() => setNotification(null), 3000);
      return;
    }

    setIsGenerating(true);
    setNotification('Checking backend connection...');

    try {
      // Check if backend is running
      const isHealthy = await checkHealth();
      if (!isHealthy) {
        setNotification('Backend not running. Start: python src/backend/server.py');
        setTimeout(() => setNotification(null), 5000);
        setIsGenerating(false);
        return;
      }

      setNotification('Generating toolpath...');

      // Convert blob URL to file path (for now, we'll use a placeholder)
      // In a real implementation, we'd need to upload the file or pass the path
      const geometryPath = part.fileUrl || 'placeholder.stl';

      // Call backend API
      const toolpathData = await generateToolpath(geometryPath, slicingParams);

      // Note: Toolpath data structure from backend API may differ from Project ToolpathData
      // For now, we just pass it directly to the toolpath editor

      setNotification(`Toolpath generated! ${toolpathData.totalLayers} layers, ${toolpathData.statistics.totalSegments} segments`);

      setTimeout(() => {
        setNotification('Opening toolpath editor...');
        setTimeout(() => {
          setNotification(null);
          navigate('/toolpath', { state: { toolpathData } });
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

  const togglePartVisibility = (partId: string) => {
    setParts((prev) =>
      prev.map((part) =>
        part.id === partId ? { ...part, visible: !part.visible } : part
      )
    );
  };

  const handleDeletePart = (partId: string) => {
    setParts((prev) => prev.filter(p => p.id !== partId));
    if (selectedPart === partId) {
      setSelectedPart(null);
    }
    setNotification('Part deleted');
    setTimeout(() => setNotification(null), 2000);
  };

  const handlePartColorChange = (partId: string, color: string) => {
    setParts((prev) =>
      prev.map((part) => (part.id === partId ? { ...part, color } : part))
    );
  };

  const handlePositionChange = (partId: string, axis: 'x' | 'y' | 'z', value: number) => {
    setParts((prev) =>
      prev.map((part) =>
        part.id === partId
          ? {
              ...part,
              position: {
                ...(part.position || { x: 0, y: 0, z: 0 }),
                [axis]: value,
              },
            }
          : part
      )
    );
  };

  const handleRotationChange = (partId: string, axis: 'x' | 'y' | 'z', value: number) => {
    setParts((prev) =>
      prev.map((part) =>
        part.id === partId
          ? {
              ...part,
              rotation: {
                ...(part.rotation || { x: 0, y: 0, z: 0 }),
                [axis]: (value * Math.PI) / 180, // Convert degrees to radians
              },
            }
          : part
      )
    );
  };

  return (
    <div className="flex h-full">
      {/* 3D Viewport */}
      <div className="flex-1 bg-gray-900 relative">
        <Canvas camera={{ position: [800, 600, 800], fov: 50 }} shadows>
          <Scene
            parts={parts}
            selectedPartId={selectedPart}
            transformMode={transformMode}
            onPartTransform={handlePartTransform}
            onPartSelect={setSelectedPart}
          />
        </Canvas>

        {/* Viewport Controls */}
        <div className="absolute top-4 left-4 space-y-2">
          {/* Import Button */}
          <button
            onClick={handleImport}
            className="flex items-center space-x-2 px-4 py-2 bg-white rounded-lg shadow-md hover:bg-gray-50 transition-colors"
          >
            <ArrowUpTrayIcon className="w-5 h-5 text-gray-700" />
            <span className="text-sm font-medium text-gray-700">Import</span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".stl,.obj,.step,.stp"
            onChange={handleFileChange}
            className="hidden"
          />

          {/* Transform Mode Controls */}
          <div className="bg-white rounded-lg shadow-md p-2">
            <div className="flex flex-col space-y-1">
              <button
                onClick={() => setTransformMode('translate')}
                className={`p-2 rounded transition-colors ${
                  transformMode === 'translate'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                title="Move (G)"
              >
                <ArrowsPointingOutIcon className="w-5 h-5" />
              </button>
              <button
                onClick={() => setTransformMode('rotate')}
                className={`p-2 rounded transition-colors ${
                  transformMode === 'rotate'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                title="Rotate (R)"
              >
                <ArrowPathIcon className="w-5 h-5" />
              </button>
              <button
                onClick={() => setTransformMode('scale')}
                className={`p-2 rounded transition-colors ${
                  transformMode === 'scale'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                title="Scale (S)"
              >
                <MagnifyingGlassIcon className="w-5 h-5" />
              </button>
              <div className="border-t border-gray-300 my-1"></div>
              <button
                onClick={handleCenterOnPlate}
                className="p-2 rounded bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
                title="Center on Plate"
                disabled={!selectedPart}
              >
                <HomeIcon className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Notification */}
        {notification && (
          <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-6 py-3 rounded-lg shadow-lg z-50">
            {notification}
          </div>
        )}
{/* Project Info */}        {currentProject && (          <div className="absolute top-4 right-4 bg-white/95 rounded-lg shadow-md p-3 max-w-sm">            <h3 className="text-sm font-semibold text-gray-900">{currentProject.name}</h3>            <div className="flex items-center space-x-2 mt-1 text-xs text-gray-600">              <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded">                {currentProject.process.toUpperCase().replace("_", " ")}              </span>              <span>•</span>              <span>{new Date(currentProject.modifiedAt).toLocaleDateString()}</span>            </div>          </div>        )}        {!currentProject && (          <div className="absolute top-4 right-4 bg-yellow-50/95 border border-yellow-300 rounded-lg shadow-md p-3 max-w-sm">            <p className="text-xs text-yellow-800">              ⚠️ No project selected. Changes will not be saved.            </p>          </div>        )}

        {/* Instructions */}
        <div className="absolute bottom-4 left-4 bg-white/90 rounded-lg shadow-md p-4 max-w-sm">
          <h3 className="text-sm font-semibold text-gray-900 mb-2">Quick Start</h3>
          <ul className="text-xs text-gray-700 space-y-1">
            <li>1. <strong>Import</strong> an STL/OBJ file</li>
            <li>2. <strong>Place on Build Plate</strong> to center it</li>
            <li>3. <strong>Adjust</strong> position/rotation as needed</li>
            <li>4. <strong>Generate Toolpath</strong> to slice</li>
          </ul>
          <div className="mt-3 pt-2 border-t border-gray-200">
            <p className="text-xs text-gray-600"><strong>Keyboard:</strong></p>
            <ul className="text-xs text-gray-700 space-y-1">
              <li>• <strong>G/R/S:</strong> Move/Rotate/Scale</li>
              <li>• <strong>Delete:</strong> Remove part</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Right Panel */}
      <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
        {/* Parts List */}
        <div className="flex-1 overflow-auto">
          <div className="p-4 border-b border-gray-200">
            <h3 className="text-sm font-semibold text-gray-900">Geometry Parts</h3>
          </div>

          <div className="divide-y divide-gray-200">
            {parts.map((part) => (
              <div
                key={part.id}
                className={`p-4 hover:bg-gray-50 transition-colors cursor-pointer ${
                  selectedPart === part.id ? 'bg-blue-50' : ''
                }`}
                onClick={() => setSelectedPart(part.id)}
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
                        togglePartVisibility(part.id);
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
                        handleDeletePart(part.id);
                      }}
                      className="p-1 hover:bg-red-100 rounded transition-colors"
                      title="Delete part"
                    >
                      <TrashIcon className="w-4 h-4 text-red-600" />
                    </button>
                  </div>
                </div>

                {selectedPart === part.id && (
                  <div className="mt-3 space-y-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Color
                      </label>
                      <input
                        type="color"
                        value={part.color}
                        onChange={(e) => handlePartColorChange(part.id, e.target.value)}
                        className="w-full h-8 rounded border border-gray-300"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Position (mm)
                      </label>
                      <div className="grid grid-cols-3 gap-2">
                        <div>
                          <label className="text-xs text-gray-500">X</label>
                          <input
                            type="number"
                            step="0.1"
                            value={part.position?.x || 0}
                            onChange={(e) =>
                              handlePositionChange(part.id, 'x', parseFloat(e.target.value) || 0)
                            }
                            className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-gray-500">Y</label>
                          <input
                            type="number"
                            step="0.1"
                            value={part.position?.y || 0}
                            onChange={(e) =>
                              handlePositionChange(part.id, 'y', parseFloat(e.target.value) || 0)
                            }
                            className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-gray-500">Z</label>
                          <input
                            type="number"
                            step="0.1"
                            value={part.position?.z || 0}
                            onChange={(e) =>
                              handlePositionChange(part.id, 'z', parseFloat(e.target.value) || 0)
                            }
                            className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                          />
                        </div>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Rotation (degrees)
                      </label>
                      <div className="grid grid-cols-3 gap-2">
                        <div>
                          <label className="text-xs text-gray-500">X</label>
                          <input
                            type="number"
                            step="1"
                            value={
                              part.rotation
                                ? Math.round((part.rotation.x * 180) / Math.PI)
                                : 0
                            }
                            onChange={(e) =>
                              handleRotationChange(part.id, 'x', parseFloat(e.target.value) || 0)
                            }
                            className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-gray-500">Y</label>
                          <input
                            type="number"
                            step="1"
                            value={
                              part.rotation
                                ? Math.round((part.rotation.y * 180) / Math.PI)
                                : 0
                            }
                            onChange={(e) =>
                              handleRotationChange(part.id, 'y', parseFloat(e.target.value) || 0)
                            }
                            className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-gray-500">Z</label>
                          <input
                            type="number"
                            step="1"
                            value={
                              part.rotation
                                ? Math.round((part.rotation.z * 180) / Math.PI)
                                : 0
                            }
                            onChange={(e) =>
                              handleRotationChange(part.id, 'z', parseFloat(e.target.value) || 0)
                            }
                            className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
                      <button
                        onClick={() => handleCenterOnPlate()}
                        disabled={!part.geometry}
                        className={`w-full flex items-center justify-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                          !part.geometry
                            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                            : 'bg-green-600 text-white hover:bg-green-700'
                        }`}
                      >
                        <HomeIcon className="w-4 h-4" />
                        <span>Place on Build Plate</span>
                      </button>

                      <button
                        onClick={() => handleDeletePart(part.id)}
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
              <p className="text-xs text-gray-500 mb-4">
                Import an STL or OBJ file to get started
              </p>
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

        {/* Slicing Parameters & Generate */}
        <div className="border-t border-gray-200">
          <div className="p-4 max-h-96 overflow-y-auto">
            <SlicingParametersPanel
              parameters={slicingParams}
              onChange={setSlicingParams}
            />
          </div>

          <div className="border-t border-gray-200 p-4 bg-gray-50">
            <button
              onClick={handleGenerateToolpath}
              disabled={isGenerating || !selectedPart}
              className={`w-full flex items-center justify-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                isGenerating || !selectedPart
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              <AdjustmentsHorizontalIcon className="w-5 h-5" />
              <span className="text-sm font-medium">
                {isGenerating ? 'Generating...' : 'Generate Toolpath'}
              </span>
            </button>
            <p className="text-xs text-gray-500 text-center mt-2">
              {selectedPart
                ? 'Slice geometry into manufacturing path'
                : 'Select a part to generate toolpath'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
