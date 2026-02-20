/**
 * WorkspaceView — the single persistent workspace page.
 *
 * Holds ONE Canvas (never unmounts), mode tabs, and a context panel that
 * switches content based on the active mode.
 */
import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Canvas } from '@react-three/fiber';
import {
  WrenchScrewdriverIcon,
  CubeIcon,
  PencilIcon,
  PlayIcon,
} from '@heroicons/react/24/outline';

import SceneManager from '../components/SceneManager';
import ErrorBoundary from '../components/ErrorBoundary';
import SetupPanel from '../components/panels/SetupPanel';
import GeometryPanel from '../components/panels/GeometryPanel';
import ToolpathPanel from '../components/panels/ToolpathPanel';
import SimulationPanel from '../components/panels/SimulationPanel';
import { useWorkspaceStore, type WorkspaceMode } from '../stores/workspaceStore';

const MODE_TABS: { mode: WorkspaceMode; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { mode: 'setup', label: 'Setup', icon: WrenchScrewdriverIcon },
  { mode: 'geometry', label: 'Geometry', icon: CubeIcon },
  { mode: 'toolpath', label: 'Toolpath', icon: PencilIcon },
  { mode: 'simulation', label: 'Trajectory Preview', icon: PlayIcon },
];

export default function WorkspaceView() {
  const mode = useWorkspaceStore((s) => s.mode);
  const setMode = useWorkspaceStore((s) => s.setMode);

  // Read ?mode= query param for redirect support
  const [searchParams] = useSearchParams();
  useEffect(() => {
    const modeParam = searchParams.get('mode') as WorkspaceMode | null;
    if (modeParam && ['setup', 'geometry', 'toolpath', 'simulation'].includes(modeParam)) {
      setMode(modeParam);
    }
  }, [searchParams, setMode]);

  // Single camera position for all modes (everything is in meters now)
  // 4m out, 3m up — frames robot cell nicely at meter scale
  const cameraPosition: [number, number, number] = [4, 3, 4];

  return (
    <div className="flex flex-col h-full">
      {/* Mode Tabs — top bar within workspace */}
      <div className="bg-white border-b border-gray-200 px-4">
        <div className="flex items-center space-x-1">
          {MODE_TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = mode === tab.mode;
            return (
              <button
                key={tab.mode}
                onClick={() => setMode(tab.mode)}
                className={`flex items-center space-x-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  isActive
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main workspace area: Canvas + Context Panel */}
      <div className="flex-1 flex overflow-hidden">
        {/* 3D Canvas — NEVER unmounts */}
        <div className="flex-1 bg-gray-900 relative">
          <Canvas camera={{ position: cameraPosition, fov: 50 }} shadows>
            <SceneManager />
          </Canvas>

          {/* Collision Warning (simulation mode) */}
          {mode === 'simulation' && useWorkspaceStore.getState().simState.collisionDetected && (
            <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-red-600 text-white px-6 py-3 rounded-lg shadow-lg flex items-center space-x-2 z-50">
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

          {/* Mode info badge */}
          <div className="absolute top-4 left-4 bg-white/90 rounded-lg shadow-md px-3 py-2 text-xs text-gray-700">
            {mode === 'setup' && 'Configure your robot cell: model, position, end effector, external axes'}
            {mode === 'geometry' && 'Import and position parts on the build plate'}
            {mode === 'toolpath' && 'Review and export the generated toolpath'}
            {mode === 'simulation' && 'Trajectory preview — kinematic replay of the robot path (not physics simulation)'}
          </div>
        </div>

        {/* Context Panel — right side, switches by mode */}
        <div className="w-96 bg-white border-l border-gray-200 flex flex-col overflow-hidden">
          <ErrorBoundary>
            {mode === 'setup' && <SetupPanel />}
            {mode === 'geometry' && <GeometryPanel />}
            {mode === 'toolpath' && <ToolpathPanel />}
            {mode === 'simulation' && <SimulationPanel />}
          </ErrorBoundary>
        </div>
      </div>
    </div>
  );
}
