/**
 * TCPSetupPanel — Full 6DOF Tool Center Point definition.
 *
 * Replaces the basic XYZ offset sliders with:
 * - XYZ position (mm) + RX/RY/RZ rotation (degrees)
 * - Tool convention dropdown (Z+, Z-, X+, X-, Y+, Y-)
 * - Tool mass input
 * - End effector type selection (preserved from original)
 */

import { useState, useEffect } from 'react';
import { useWorkspaceStore, type CellSetup } from '../../stores/workspaceStore';
import { getTools, type ToolInfo } from '../../api/robot';

type EndEffectorType = CellSetup['endEffector']['type'];

// Tool conventions: which axis of the tool frame points toward the workpiece
const TOOL_CONVENTIONS = [
  { value: 'Z+', label: 'Z+ (Forward)', desc: 'Z-axis points toward workpiece (most common)' },
  { value: 'Z-', label: 'Z- (Backward)', desc: 'Z-axis points away from workpiece' },
  { value: 'X+', label: 'X+ (Forward)', desc: 'X-axis points toward workpiece' },
  { value: 'X-', label: 'X- (Backward)', desc: 'X-axis points away from workpiece' },
  { value: 'Y+', label: 'Y+ (Forward)', desc: 'Y-axis points toward workpiece' },
  { value: 'Y-', label: 'Y- (Backward)', desc: 'Y-axis points away from workpiece' },
] as const;

export default function TCPSetupPanel() {
  const cellSetup = useWorkspaceStore((s) => s.cellSetup);
  const setCellSetup = useWorkspaceStore((s) => s.setCellSetup);
  const [backendTools, setBackendTools] = useState<ToolInfo[]>([]);

  const ee = cellSetup.endEffector;

  // Fetch tools from backend config/tools/*.yaml
  useEffect(() => {
    getTools().then((tools) => {
      if (tools.length > 0) setBackendTools(tools);
    });
  }, []);

  // Apply a backend tool's TCP offset and mass
  const applyBackendTool = (tool: ToolInfo) => {
    const offset: [number, number, number, number, number, number] = [
      tool.tcpOffset[0] ?? 0, tool.tcpOffset[1] ?? 0, tool.tcpOffset[2] ?? 0,
      tool.tcpOffset[3] ?? 0, tool.tcpOffset[4] ?? 0, tool.tcpOffset[5] ?? 0,
    ];
    const typeMap: Record<string, EndEffectorType> = {
      extruder: 'waam_torch',
      milling: 'spindle',
      remover: 'spindle',
    };
    const eeType = typeMap[tool.type] || 'waam_torch';
    setCellSetup({ ...cellSetup, endEffector: { ...ee, type: eeType, offset, mass: tool.mass, convention: 'Z+' } });
  };

  // End effector presets
  const updateEndEffector = (type: EndEffectorType) => {
    const presets: Record<EndEffectorType, { offset: [number, number, number, number, number, number]; mass: number; convention: CellSetup['endEffector']['convention'] }> = {
      waam_torch: { offset: [0, 0, 0.15, 0, 0, 0], mass: 5.0, convention: 'Z+' },
      pellet_extruder: { offset: [0, 0, 0.25, 0, 0, 0], mass: 8.0, convention: 'Z+' },
      spindle: { offset: [0, 0, 0.2, 0, 0, 0], mass: 12.0, convention: 'Z+' },
      none: { offset: [0, 0, 0, 0, 0, 0], mass: 0, convention: 'Z+' },
    };
    setCellSetup({ ...cellSetup, endEffector: { type, ...presets[type] } });
  };

  const updateConvention = (convention: CellSetup['endEffector']['convention']) => {
    setCellSetup({ ...cellSetup, endEffector: { ...ee, convention } });
  };

  const updateOffset = (index: number, value: number) => {
    const offset = [...ee.offset] as [number, number, number, number, number, number];
    offset[index] = value;
    setCellSetup({ ...cellSetup, endEffector: { ...ee, offset } });
  };

  const updateMass = (mass: number) => {
    setCellSetup({ ...cellSetup, endEffector: { ...ee, mass } });
  };

  return (
    <div className="space-y-5">
      {/* End Effector Type */}
      <div>
        <h4 className="text-sm font-semibold text-gray-900 mb-3">End Effector Type</h4>
        <div className="grid grid-cols-2 gap-2">
          {[
            { value: 'waam_torch', label: 'WAAM Torch', icon: '⚡' },
            { value: 'pellet_extruder', label: 'Pellet Extruder', icon: '🔥' },
            { value: 'spindle', label: 'Milling Spindle', icon: '⚙️' },
            { value: 'none', label: 'None', icon: '⬜' },
          ].map((option) => (
            <button
              key={option.value}
              onClick={() => updateEndEffector(option.value as EndEffectorType)}
              className={`flex items-center gap-2 px-3 py-2.5 border-2 rounded-lg transition-colors text-left ${
                ee.type === option.value
                  ? 'border-blue-600 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <span className="text-lg">{option.icon}</span>
              <span className="text-xs font-medium">{option.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Backend Tool Presets (from config/tools/*.yaml) */}
      {backendTools.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-900 mb-1">Tool Library</h4>
          <p className="text-xs text-gray-400 mb-2 font-mono">config/tools/*.yaml</p>
          <div className="space-y-1">
            {backendTools.map((tool) => (
              <button
                key={tool.id}
                onClick={() => applyBackendTool(tool)}
                className="w-full text-left px-3 py-2 border border-gray-200 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-800">{tool.name}</span>
                  <span className="text-xs text-gray-400">{tool.type}</span>
                </div>
                <div className="text-xs text-gray-500 mt-0.5">{tool.description}</div>
                <div className="text-xs text-gray-400 font-mono mt-0.5">
                  TCP: [{tool.tcpOffset.slice(0, 3).map((v: number) => v.toFixed(3)).join(', ')}] | {tool.mass} kg
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {ee.type !== 'none' && (
        <>
          {/* TCP Position (6DOF) */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-1">
              TCP Position <span className="text-gray-400 font-normal text-xs">(Flange Frame, m)</span>
            </h4>
            <p className="text-xs text-gray-500 mb-3">
              Tool Center Point offset from robot flange in the flange coordinate frame.
            </p>
            <div className="grid grid-cols-3 gap-2">
              {['X', 'Y', 'Z'].map((axis, i) => (
                <div key={axis}>
                  <label className="block text-xs font-medium text-gray-600 mb-1 text-center">
                    {axis}
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    value={ee.offset[i]}
                    onChange={(e) => updateOffset(i, parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1.5 text-sm text-center border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
                  />
                  <div className="text-xs text-gray-400 text-center mt-0.5">
                    {(ee.offset[i] * 1000).toFixed(0)} mm
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* TCP Orientation */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-1">
              TCP Orientation <span className="text-gray-400 font-normal text-xs">(Flange Frame, deg)</span>
            </h4>
            <p className="text-xs text-gray-500 mb-3">
              Tool frame rotation relative to flange frame in Euler angles.
            </p>
            <div className="grid grid-cols-3 gap-2">
              {['RX', 'RY', 'RZ'].map((axis, i) => (
                <div key={axis}>
                  <label className="block text-xs font-medium text-gray-600 mb-1 text-center">
                    {axis}
                  </label>
                  <input
                    type="number"
                    step="1"
                    value={ee.offset[i + 3]}
                    onChange={(e) => updateOffset(i + 3, parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1.5 text-sm text-center border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
                  />
                  <div className="text-xs text-gray-400 text-center mt-0.5">deg</div>
                </div>
              ))}
            </div>
          </div>

          {/* Tool Convention */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-1">
              Tool Convention
            </h4>
            <p className="text-xs text-gray-500 mb-2">
              Which axis of the tool frame points toward the workpiece.
            </p>
            <select
              value={ee.convention || 'Z+'}
              onChange={(e) => updateConvention(e.target.value as CellSetup['endEffector']['convention'])}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {TOOL_CONVENTIONS.map((tc) => (
                <option key={tc.value} value={tc.value}>{tc.label}</option>
              ))}
            </select>
          </div>

          {/* Tool Mass */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-1">
              Tool Mass
            </h4>
            <div className="flex items-center gap-2">
              <input
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={ee.mass}
                onChange={(e) => updateMass(parseFloat(e.target.value) || 0)}
                className="w-24 px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
              />
              <span className="text-xs text-gray-500">kg</span>
            </div>
          </div>

          {/* Summary Card */}
          <div className="bg-gray-50 p-3 rounded-lg">
            <h5 className="text-xs font-semibold text-gray-700 mb-2">TCP Summary</h5>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-600">Position:</span>
                <span className="font-medium font-mono">
                  [{ee.offset.slice(0, 3).map((v) => `${(v * 1000).toFixed(0)}`).join(', ')}] mm
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Orientation:</span>
                <span className="font-medium font-mono">
                  [{ee.offset.slice(3).map((v) => `${v.toFixed(0)}`).join(', ')}] deg
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Mass:</span>
                <span className="font-medium">{ee.mass} kg</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Convention:</span>
                <span className="font-medium">
                  {TOOL_CONVENTIONS.find((tc) => tc.value === (ee.convention || 'Z+'))?.label || 'Z+ (Forward)'}
                </span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
