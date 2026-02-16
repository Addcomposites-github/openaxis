/**
 * SetupPanel — Robot cell configuration (extracted from RobotSetup.tsx).
 * Reads/writes to workspaceStore.cellSetup.
 */
import { useState, useEffect } from 'react';
import { useWorkspaceStore, type CellSetup } from '../../stores/workspaceStore';
import { useRobotStore } from '../../stores/robotStore';
import { getRobotConfig } from '../../api/robot';
import { checkHealth } from '../../api/client';
import ProcessSetupSection from './ProcessSetupSection';
import TCPSetupPanel from './TCPSetupPanel';
import WorkFramePanel from './WorkFramePanel';

type ExternalAxisType = CellSetup['externalAxis']['type'];

export default function SetupPanel() {
  const cellSetup = useWorkspaceStore((s) => s.cellSetup);
  const setCellSetup = useWorkspaceStore((s) => s.setCellSetup);
  const setMode = useWorkspaceStore((s) => s.setMode);

  const [activeTab, setActiveTab] = useState<'robot' | 'process' | 'endeffector' | 'external' | 'worktable'>('robot');
  const [backendConnected, setBackendConnected] = useState(false);
  const [robotSpecs, setRobotSpecs] = useState<{ reach: number; payload: number; dof: number }>({
    reach: 2600, payload: 200, dof: 6,
  });

  useEffect(() => {
    const init = async () => {
      const health = await checkHealth();
      setBackendConnected(health.ok);
      if (health.ok) {
        try {
          const config = await getRobotConfig(cellSetup.robot.model);
          setRobotSpecs({
            reach: config.maxReach || 2600,
            payload: config.maxPayload || 200,
            dof: config.dof || 6,
          });
        } catch (e) {
          console.warn('Failed to fetch robot config:', e);
        }
      }
    };
    init();
  }, [cellSetup.robot.model]);

  const updateRobotPosition = (axis: 'x' | 'y' | 'z', value: number) => {
    const pos = [...cellSetup.robot.basePosition] as [number, number, number];
    const idx = axis === 'x' ? 0 : axis === 'y' ? 1 : 2;
    pos[idx] = value;
    setCellSetup({ ...cellSetup, robot: { ...cellSetup.robot, basePosition: pos } });
  };

  const updateRobotRotation = (axis: number, value: number) => {
    const rot = [...cellSetup.robot.baseRotation] as [number, number, number];
    rot[axis] = value;
    setCellSetup({ ...cellSetup, robot: { ...cellSetup.robot, baseRotation: rot } });
  };

  const updateExternalAxis = (type: ExternalAxisType) => {
    const presets: Record<ExternalAxisType, { enabled: boolean; position: [number, number, number]; rotation: [number, number, number] }> = {
      turntable: { enabled: true, position: [2, 0, 0], rotation: [0, 0, 0] },
      positioner_2axis: { enabled: true, position: [1.5, 0, 0.5], rotation: [0, 0, 0] },
      linear_track: { enabled: true, position: [0, 0, 2], rotation: [0, 0, 0] },
      none: { enabled: false, position: [0, 0, 0], rotation: [0, 0, 0] },
    };
    setCellSetup({ ...cellSetup, externalAxis: { type, ...presets[type] } });
  };

  const saveCellSetup = () => {
    // Persist to robotStore for backward compat
    const robotStore = useRobotStore.getState();
    robotStore.setBaseRotation(cellSetup.robot.baseRotation);
    robotStore.setConfiguration({
      id: cellSetup.robot.model,
      name: `Robot Cell - ${cellSetup.robot.model}`,
      manufacturer: cellSetup.robot.model.startsWith('abb') ? 'ABB' : 'Unknown',
      model: cellSetup.robot.model,
      type: 'industrial',
      dof: robotSpecs.dof,
      payload: robotSpecs.payload,
      reach: robotSpecs.reach,
      urdfPath: `/config/urdf/${cellSetup.robot.model}.urdf`,
      jointLimits: [],
      workEnvelope: { xMin: -3, xMax: 3, yMin: -3, yMax: 3, zMin: 0, zMax: 3 },
    });

    // Proceed to geometry mode
    setMode('geometry');
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Robot Cell Setup</h3>
        <p className="text-sm text-gray-600 mt-1">Configure your manufacturing environment</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex">
          {[
            { id: 'robot', label: 'Robot' },
            { id: 'process', label: 'Process' },
            { id: 'endeffector', label: 'TCP / Tool' },
            { id: 'external', label: 'External Axes' },
            { id: 'worktable', label: 'Work Frames' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex-1 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-auto p-4 space-y-6">
        {activeTab === 'robot' && (
          <>
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-3">Robot Model</h4>
              <select
                value={cellSetup.robot.model}
                onChange={(e) =>
                  setCellSetup({ ...cellSetup, robot: { ...cellSetup.robot, model: e.target.value } })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="abb_irb6700">ABB IRB 6700-200/2.60</option>
                <option value="abb_irb4600" disabled>ABB IRB 4600 (Coming Soon)</option>
                <option value="kuka_kr120" disabled>KUKA KR 120 (Coming Soon)</option>
              </select>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-3">Robot Base Position</h4>
              <div className="space-y-3">
                {(['x', 'z'] as const).map((axis) => {
                  const idx = axis === 'x' ? 0 : 2;
                  return (
                    <div key={axis}>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        {axis.toUpperCase()} Position (m)
                      </label>
                      <input
                        type="range" min="-5" max="5" step="0.1"
                        value={cellSetup.robot.basePosition[idx]}
                        onChange={(e) => updateRobotPosition(axis, parseFloat(e.target.value))}
                        className="w-full"
                      />
                      <div className="text-xs text-gray-600 mt-1">
                        {cellSetup.robot.basePosition[idx].toFixed(2)} m
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-3">Robot Base Rotation</h4>
              <div className="space-y-3">
                {[
                  { label: 'Yaw / Z-axis (degrees)', idx: 2, min: -180, max: 180 },
                  { label: 'Pitch / Y-axis (degrees)', idx: 1, min: -45, max: 45 },
                  { label: 'Roll / X-axis (degrees)', idx: 0, min: -45, max: 45 },
                ].map((item) => (
                  <div key={item.idx}>
                    <label className="block text-xs font-medium text-gray-700 mb-1">{item.label}</label>
                    <input
                      type="range" min={item.min} max={item.max} step="1"
                      value={cellSetup.robot.baseRotation[item.idx]}
                      onChange={(e) => updateRobotRotation(item.idx, parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <div className="text-xs text-gray-600 mt-1">
                      {cellSetup.robot.baseRotation[item.idx].toFixed(0)}°
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-gray-50 p-3 rounded-lg">
              <h5 className="text-xs font-semibold text-gray-700 mb-2">
                Robot Specifications
                {backendConnected && <span className="text-green-600 ml-1">(live)</span>}
              </h5>
              <div className="space-y-1 text-xs text-gray-600">
                <div className="flex justify-between">
                  <span>Reach:</span>
                  <span className="font-medium">{robotSpecs.reach} mm</span>
                </div>
                <div className="flex justify-between">
                  <span>Payload:</span>
                  <span className="font-medium">{robotSpecs.payload} kg</span>
                </div>
                <div className="flex justify-between">
                  <span>Axes:</span>
                  <span className="font-medium">{robotSpecs.dof}</span>
                </div>
              </div>
            </div>
          </>
        )}

        {activeTab === 'process' && (
          <ProcessSetupSection />
        )}

        {activeTab === 'endeffector' && (
          <TCPSetupPanel />
        )}

        {activeTab === 'external' && (
          <>
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-3">External Axis Type</h4>
              <div className="space-y-2">
                {[
                  { value: 'none', label: 'None', desc: 'No external axes' },
                  { value: 'turntable', label: 'Turntable (1-axis)', desc: 'Rotating table for round parts' },
                  { value: 'positioner_2axis', label: 'Positioner (2-axis)', desc: 'Tilt & rotate workpiece' },
                  { value: 'linear_track', label: 'Linear Track', desc: 'Extend robot reach' },
                ].map((option) => (
                  <button
                    key={option.value}
                    onClick={() => updateExternalAxis(option.value as ExternalAxisType)}
                    className={`w-full text-left px-4 py-3 border-2 rounded-lg transition-colors ${
                      cellSetup.externalAxis.type === option.value
                        ? 'border-blue-600 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="font-medium text-sm">{option.label}</div>
                    <div className="text-xs text-gray-600 mt-1">{option.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {cellSetup.externalAxis.enabled && (
              <div className="bg-yellow-50 border border-yellow-200 p-3 rounded-lg">
                <p className="text-xs text-yellow-800">
                  <strong>Note:</strong> External axes coordination will be available in a future phase.
                  For now, this is visual placement only.
                </p>
              </div>
            )}
          </>
        )}

        {activeTab === 'worktable' && (
          <WorkFramePanel />
        )}
      </div>

      {/* Actions */}
      <div className="border-t border-gray-200 p-4 space-y-2">
        <button
          onClick={saveCellSetup}
          className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          Save Cell Setup & Continue
        </button>
        <button className="w-full px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm">
          Load Preset Configuration
        </button>
      </div>
    </div>
  );
}
