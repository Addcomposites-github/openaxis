/**
 * WorkFramePanel — Work frame (coordinate system) management.
 *
 * Manages multiple work frames with position, rotation, size,
 * and alignment methods. Parts can be assigned to frames.
 * Replaces the simple work table position/size controls.
 */

import { useState } from 'react';
import { useWorkFrameStore, type WorkFrame, type AlignmentMethod } from '../../stores/workFrameStore';

const ALIGNMENT_METHODS: { value: AlignmentMethod; label: string; desc: string }[] = [
  { value: 'manual', label: 'Manual', desc: 'Enter position and rotation directly' },
  { value: 'z_plus_x', label: 'Z+X Axis', desc: 'Define Z and X axes from reference points' },
  { value: 'z_plus_y', label: 'Z+Y Axis', desc: 'Define Z and Y axes from reference points' },
  { value: 'x_plus_y', label: 'X+Y Axis', desc: 'Define X and Y axes from reference points' },
  { value: '3planes', label: 'Three Planes', desc: 'Define from three intersecting planes' },
  { value: 'offset', label: 'Offset', desc: 'Offset from an existing work frame' },
  { value: 'project', label: 'Project to Plane', desc: 'Project to a plane defined by points' },
];

export default function WorkFramePanel() {
  const {
    frames,
    activeFrameId,
    addFrame,
    removeFrame,
    updateFrame,
    setActiveFrame,
  } = useWorkFrameStore();

  const [expandedFrameId, setExpandedFrameId] = useState<string | null>(activeFrameId);

  const activeFrame = frames.find((f) => f.id === activeFrameId) || frames[0];

  const handleAddFrame = () => {
    const id = addFrame();
    setExpandedFrameId(id);
    setActiveFrame(id);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-gray-900">Work Frames</h4>
          <p className="text-xs text-gray-500 mt-0.5">
            Coordinate systems for part placement and robot programming.
          </p>
        </div>
        <button
          onClick={handleAddFrame}
          className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          + Add Frame
        </button>
      </div>

      {/* Frame List */}
      <div className="space-y-2">
        {frames.map((frame) => (
          <WorkFrameCard
            key={frame.id}
            frame={frame}
            isActive={frame.id === activeFrameId}
            isExpanded={frame.id === expandedFrameId}
            onSelect={() => setActiveFrame(frame.id)}
            onToggleExpand={() =>
              setExpandedFrameId(expandedFrameId === frame.id ? null : frame.id)
            }
            onUpdate={(updates) => updateFrame(frame.id, updates)}
            onRemove={() => removeFrame(frame.id)}
          />
        ))}
      </div>

      {/* Info Card */}
      <div className="bg-blue-50 border border-blue-200 p-3 rounded-lg">
        <p className="text-xs text-blue-800">
          <strong>Active Frame:</strong> {activeFrame?.name || 'None'}.
          Parts placed on the active frame use its coordinate system for toolpath generation and post-processor output.
        </p>
      </div>
    </div>
  );
}

// ─── WorkFrameCard ───────────────────────────────────────────────────────────

interface WorkFrameCardProps {
  frame: WorkFrame;
  isActive: boolean;
  isExpanded: boolean;
  onSelect: () => void;
  onToggleExpand: () => void;
  onUpdate: (updates: Partial<WorkFrame>) => void;
  onRemove: () => void;
}

function WorkFrameCard({
  frame,
  isActive,
  isExpanded,
  onSelect,
  onToggleExpand,
  onUpdate,
  onRemove,
}: WorkFrameCardProps) {
  return (
    <div
      className={`border-2 rounded-lg transition-colors ${
        isActive
          ? 'border-blue-500 bg-blue-50/50'
          : 'border-gray-200 bg-white'
      }`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 cursor-pointer"
        onClick={onToggleExpand}
      >
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full flex-shrink-0"
            style={{ backgroundColor: frame.color }}
          />
          <span className="text-sm font-medium text-gray-900">
            {frame.name}
          </span>
          {frame.isDefault && (
            <span className="px-1.5 py-0.5 text-xs bg-gray-200 text-gray-600 rounded">
              Default
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {!isActive && (
            <button
              onClick={(e) => { e.stopPropagation(); onSelect(); }}
              className="px-2 py-1 text-xs text-blue-600 hover:bg-blue-100 rounded transition-colors"
            >
              Set Active
            </button>
          )}
          {isActive && (
            <span className="px-2 py-1 text-xs text-blue-700 bg-blue-100 rounded font-medium">
              Active
            </span>
          )}
          <span className="text-gray-400 text-sm">{isExpanded ? '▼' : '▶'}</span>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-3 pb-3 space-y-3 border-t border-gray-100 pt-3">
          {/* Name */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
            <input
              type="text"
              value={frame.name}
              onChange={(e) => onUpdate({ name: e.target.value })}
              className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Position (mm) */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Position (mm)
            </label>
            <div className="grid grid-cols-3 gap-2">
              {['X', 'Y', 'Z'].map((axis, i) => (
                <div key={axis}>
                  <label className="block text-xs text-gray-400 text-center">{axis}</label>
                  <input
                    type="number"
                    step="10"
                    value={frame.position[i]}
                    onChange={(e) => {
                      const pos = [...frame.position] as [number, number, number];
                      pos[i] = parseFloat(e.target.value) || 0;
                      onUpdate({ position: pos });
                    }}
                    className="w-full px-2 py-1 text-xs text-center border border-gray-300 rounded font-mono"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Rotation (degrees) */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Rotation (degrees)
            </label>
            <div className="grid grid-cols-3 gap-2">
              {['RX', 'RY', 'RZ'].map((axis, i) => (
                <div key={axis}>
                  <label className="block text-xs text-gray-400 text-center">{axis}</label>
                  <input
                    type="number"
                    step="1"
                    value={frame.rotation[i]}
                    onChange={(e) => {
                      const rot = [...frame.rotation] as [number, number, number];
                      rot[i] = parseFloat(e.target.value) || 0;
                      onUpdate({ rotation: rot });
                    }}
                    className="w-full px-2 py-1 text-xs text-center border border-gray-300 rounded font-mono"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Size (m — scene units) */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Platform Size (m)
            </label>
            <div className="grid grid-cols-3 gap-2">
              {['Width', 'Height', 'Depth'].map((label, i) => (
                <div key={label}>
                  <label className="block text-xs text-gray-400 text-center">{label}</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="10"
                    value={frame.size[i]}
                    onChange={(e) => {
                      const size = [...frame.size] as [number, number, number];
                      size[i] = parseFloat(e.target.value) || 0.1;
                      onUpdate({ size: size });
                    }}
                    className="w-full px-2 py-1 text-xs text-center border border-gray-300 rounded font-mono"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Alignment Method */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Alignment Method
            </label>
            <select
              value={frame.alignmentMethod}
              onChange={(e) => onUpdate({ alignmentMethod: e.target.value as AlignmentMethod })}
              className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {ALIGNMENT_METHODS.map((am) => (
                <option key={am.value} value={am.value}>{am.label}</option>
              ))}
            </select>
            <p className="text-xs text-gray-400 mt-1">
              {ALIGNMENT_METHODS.find((am) => am.value === frame.alignmentMethod)?.desc}
            </p>
          </div>

          {/* Visibility */}
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-gray-600">Visible</label>
            <button
              onClick={() => onUpdate({ visible: !frame.visible })}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                frame.visible ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                  frame.visible ? 'translate-x-4' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Parts assigned */}
          {frame.childPartIds.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Assigned Parts ({frame.childPartIds.length})
              </label>
              <div className="text-xs text-gray-500">
                {frame.childPartIds.join(', ')}
              </div>
            </div>
          )}

          {/* Delete button (non-default only) */}
          {!frame.isDefault && (
            <button
              onClick={onRemove}
              className="w-full px-3 py-1.5 text-xs text-red-600 border border-red-200 rounded-md hover:bg-red-50 transition-colors"
            >
              Remove Frame
            </button>
          )}
        </div>
      )}
    </div>
  );
}
