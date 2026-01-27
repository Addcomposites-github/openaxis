import { useState, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid, useGLTF } from '@react-three/drei';
import {
  PlayIcon,
  PauseIcon,
  ForwardIcon,
  BackwardIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import * as THREE from 'three';

interface SimulationState {
  isRunning: boolean;
  currentTime: number;
  totalTime: number;
  speed: number;
  collisionDetected: boolean;
}

function RobotModel({ position }: { position: THREE.Vector3 }) {
  return (
    <group position={position}>
      {/* Simple robot visualization - replace with actual URDF/GLTF loading */}
      <mesh position={[0, 0.5, 0]}>
        <cylinderGeometry args={[0.1, 0.1, 1]} />
        <meshStandardMaterial color="#64748b" />
      </mesh>
      <mesh position={[0, 1.2, 0]}>
        <boxGeometry args={[0.3, 0.4, 0.2]} />
        <meshStandardMaterial color="#475569" />
      </mesh>
      <mesh position={[0, 1.6, 0.15]}>
        <cylinderGeometry args={[0.05, 0.05, 0.3]} />
        <meshStandardMaterial color="#94a3b8" />
      </mesh>
    </group>
  );
}

function Scene() {
  const [robotPosition] = useState(new THREE.Vector3(0, 0, 0));

  return (
    <>
      <ambientLight intensity={0.6} />
      <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
      <spotLight position={[0, 10, 0]} angle={0.3} penumbra={1} intensity={0.5} castShadow />

      <Grid
        args={[100, 100]}
        cellSize={1}
        cellThickness={0.5}
        cellColor="#6b7280"
        sectionSize={10}
        sectionThickness={1}
        sectionColor="#374151"
        fadeDistance={50}
        fadeStrength={1}
        followCamera={false}
        infiniteGrid
      />

      {/* Work Table */}
      <mesh position={[0, -0.05, 0]} receiveShadow>
        <boxGeometry args={[3, 0.1, 3]} />
        <meshStandardMaterial color="#9ca3af" />
      </mesh>

      {/* Robot */}
      <RobotModel position={robotPosition} />

      {/* Part being manufactured */}
      <mesh position={[0, 0.5, 0]} castShadow>
        <boxGeometry args={[0.5, 0.5, 0.5]} />
        <meshStandardMaterial color="#3b82f6" />
      </mesh>

      <OrbitControls makeDefault />
    </>
  );
}

export default function Simulation() {
  const [simState, setSimState] = useState<SimulationState>({
    isRunning: false,
    currentTime: 0,
    totalTime: 300,
    speed: 1.0,
    collisionDetected: false,
  });

  useEffect(() => {
    if (simState.isRunning && simState.currentTime < simState.totalTime) {
      const interval = setInterval(() => {
        setSimState((prev) => ({
          ...prev,
          currentTime: Math.min(prev.currentTime + prev.speed, prev.totalTime),
        }));
      }, 100);

      return () => clearInterval(interval);
    } else if (simState.currentTime >= simState.totalTime) {
      setSimState((prev) => ({ ...prev, isRunning: false }));
    }
  }, [simState.isRunning, simState.currentTime, simState.totalTime, simState.speed]);

  const handlePlayPause = () => {
    setSimState((prev) => ({ ...prev, isRunning: !prev.isRunning }));
  };

  const handleReset = () => {
    setSimState((prev) => ({ ...prev, isRunning: false, currentTime: 0 }));
  };

  const handleSpeedChange = (speed: number) => {
    setSimState((prev) => ({ ...prev, speed }));
  };

  const handleTimeChange = (time: number) => {
    setSimState((prev) => ({ ...prev, currentTime: time }));
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex h-full">
      {/* 3D Viewport */}
      <div className="flex-1 bg-gray-900 relative">
        <Canvas camera={{ position: [5, 5, 5], fov: 50 }} shadows>
          <Scene />
        </Canvas>

        {/* Simulation Controls */}
        <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 bg-white rounded-lg shadow-lg p-4">
          <div className="flex items-center space-x-4 mb-4">
            <button
              onClick={() => handleTimeChange(Math.max(0, simState.currentTime - 10))}
              className="p-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <BackwardIcon className="w-5 h-5" />
            </button>

            <button
              onClick={handlePlayPause}
              className="p-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              {simState.isRunning ? (
                <PauseIcon className="w-6 h-6" />
              ) : (
                <PlayIcon className="w-6 h-6" />
              )}
            </button>

            <button
              onClick={() =>
                handleTimeChange(Math.min(simState.totalTime, simState.currentTime + 10))
              }
              className="p-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ForwardIcon className="w-5 h-5" />
            </button>

            <button
              onClick={handleReset}
              className="p-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowPathIcon className="w-5 h-5" />
            </button>

            <div className="border-l border-gray-300 h-8 mx-2"></div>

            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-700">Speed:</span>
              <select
                value={simState.speed}
                onChange={(e) => handleSpeedChange(Number(e.target.value))}
                className="px-3 py-1 border border-gray-300 rounded text-sm"
              >
                <option value="0.25">0.25x</option>
                <option value="0.5">0.5x</option>
                <option value="1">1x</option>
                <option value="2">2x</option>
                <option value="5">5x</option>
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <input
              type="range"
              min="0"
              max={simState.totalTime}
              value={simState.currentTime}
              onChange={(e) => handleTimeChange(Number(e.target.value))}
              className="w-96"
            />
            <div className="flex justify-between text-sm text-gray-600">
              <span>{formatTime(simState.currentTime)}</span>
              <span>{formatTime(simState.totalTime)}</span>
            </div>
          </div>
        </div>

        {/* Collision Warning */}
        {simState.collisionDetected && (
          <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-red-600 text-white px-6 py-3 rounded-lg shadow-lg flex items-center space-x-2">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            <span className="font-medium">Collision Detected!</span>
          </div>
        )}
      </div>

      {/* Right Panel - Simulation Info */}
      <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-900">Simulation Status</h3>
        </div>

        <div className="flex-1 overflow-auto p-4 space-y-6">
          {/* Status Cards */}
          <div className="space-y-3">
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-green-800">Collision Check</span>
                <span className="px-2 py-1 bg-green-600 text-white text-xs font-semibold rounded">
                  PASS
                </span>
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-blue-800">Joint Limits</span>
                <span className="px-2 py-1 bg-blue-600 text-white text-xs font-semibold rounded">
                  OK
                </span>
              </div>
            </div>

            <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-purple-800">Singularities</span>
                <span className="px-2 py-1 bg-purple-600 text-white text-xs font-semibold rounded">
                  NONE
                </span>
              </div>
            </div>
          </div>

          {/* Robot State */}
          <div>
            <h4 className="text-xs font-semibold text-gray-700 mb-3">Robot State</h4>
            <div className="space-y-2">
              {[
                { name: 'Joint 1', value: 45.2, unit: '°' },
                { name: 'Joint 2', value: -30.5, unit: '°' },
                { name: 'Joint 3', value: 90.0, unit: '°' },
                { name: 'Joint 4', value: 0.0, unit: '°' },
                { name: 'Joint 5', value: 45.0, unit: '°' },
                { name: 'Joint 6', value: 0.0, unit: '°' },
              ].map((joint) => (
                <div key={joint.name} className="flex justify-between items-center text-sm">
                  <span className="text-gray-600">{joint.name}</span>
                  <span className="font-medium text-gray-900">
                    {joint.value.toFixed(1)}{joint.unit}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* TCP Position */}
          <div>
            <h4 className="text-xs font-semibold text-gray-700 mb-3">TCP Position</h4>
            <div className="space-y-2">
              {[
                { name: 'X', value: 125.5, unit: 'mm' },
                { name: 'Y', value: -45.2, unit: 'mm' },
                { name: 'Z', value: 320.8, unit: 'mm' },
                { name: 'RX', value: 180.0, unit: '°' },
                { name: 'RY', value: 0.0, unit: '°' },
                { name: 'RZ', value: 45.0, unit: '°' },
              ].map((coord) => (
                <div key={coord.name} className="flex justify-between items-center text-sm">
                  <span className="text-gray-600">{coord.name}</span>
                  <span className="font-medium text-gray-900">
                    {coord.value.toFixed(1)} {coord.unit}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Process Parameters */}
          <div>
            <h4 className="text-xs font-semibold text-gray-700 mb-3">Process Status</h4>
            <div className="space-y-2">
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-600">Temperature</span>
                <span className="font-medium text-gray-900">220°C</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-600">Flow Rate</span>
                <span className="font-medium text-gray-900">10 mm³/s</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-600">Layer</span>
                <span className="font-medium text-gray-900">25/50</span>
              </div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="border-t border-gray-200 p-4 space-y-2">
          <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            Export Simulation Data
          </button>
          <button className="w-full px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
            Adjust Collision Margins
          </button>
        </div>
      </div>
    </div>
  );
}
