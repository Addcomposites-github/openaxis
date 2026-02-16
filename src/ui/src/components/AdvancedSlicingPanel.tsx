/**
 * AdvancedSlicingPanel — Comprehensive slicing parameter controls.
 *
 * Replaces the basic SlicingParametersPanel with organized sections:
 * - Basic Parameters (layer height, line width, speed)
 * - Shell Settings (wall count, wall width)
 * - Infill Settings (pattern selection with visual previews, density)
 * - Seam Control (mode, shape, angle)
 * - Movement Settings (travel speed, z-hop, retraction)
 * - Engage/Disengage (lead-in/out distance and angle)
 */

import { useState } from 'react';
import {
  ChevronDownIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import InfillPatternPreview from './InfillPatternPreview';

interface AdvancedSlicingPanelProps {
  params: SlicingParams;
  onChange: (params: SlicingParams) => void;
  materialPreset?: string;
}

export interface SlicingParams {
  // Basic
  layerHeight: number;
  lineWidth: number;
  printSpeed: number;

  // Shell
  wallCount: number;
  wallWidth: number;

  // Infill
  infillPattern: string;
  infillDensity: number;  // 0-100%

  // Seam
  seamMode: string;       // 'guided' | 'distributed' | 'random'
  seamShape: string;      // 'straight' | 'zigzag' | 'triangular' | 'sine'
  seamAngle: number;      // degrees (for guided mode)

  // Movement
  travelSpeed: number;
  zHop: number;
  retractDistance: number;
  retractSpeed: number;

  // Engage/Disengage
  leadInDistance: number;
  leadInAngle: number;
  leadOutDistance: number;
  leadOutAngle: number;
}

const INFILL_PATTERNS = [
  { value: 'grid', label: 'Grid', desc: 'Parallel lines at 0°/90°' },
  { value: 'triangles', label: 'Triangles', desc: '60° angle rotation per layer' },
  { value: 'triangle_grid', label: 'Triangle Grid', desc: 'Dense 0°/60°/120° grid' },
  { value: 'zigzag', label: 'Zigzag', desc: 'Connected parallel lines' },
  { value: 'radial', label: 'Radial', desc: 'Concentric rings from center' },
  { value: 'offset', label: 'Offset', desc: 'Inward contour offsets' },
  { value: 'hexgrid', label: 'Hexagonal', desc: 'Honeycomb pattern' },
  { value: 'medial', label: 'Medial', desc: 'Medial axis guided paths' },
];

const SEAM_MODES = [
  { value: 'guided', label: 'Guided', desc: 'All layers start at specified angle' },
  { value: 'distributed', label: 'Distributed', desc: 'Evenly spaced around perimeter' },
  { value: 'random', label: 'Random', desc: 'Random start point per layer' },
];

const SEAM_SHAPES = [
  { value: 'straight', label: 'Straight' },
  { value: 'zigzag', label: 'Zigzag' },
  { value: 'triangular', label: 'Triangular' },
  { value: 'sine', label: 'Sine Wave' },
];

export const defaultSlicingParams: SlicingParams = {
  layerHeight: 0.3,
  lineWidth: 0.6,
  printSpeed: 1000,
  wallCount: 2,
  wallWidth: 0.6,
  infillPattern: 'grid',
  infillDensity: 20,
  seamMode: 'guided',
  seamShape: 'straight',
  seamAngle: 0,
  travelSpeed: 5000,
  zHop: 0.5,
  retractDistance: 2.0,
  retractSpeed: 2400,
  leadInDistance: 0,
  leadInAngle: 45,
  leadOutDistance: 0,
  leadOutAngle: 45,
};

function Section({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <span className="text-xs font-semibold text-gray-800">{title}</span>
        {open ? (
          <ChevronDownIcon className="w-3.5 h-3.5 text-gray-500" />
        ) : (
          <ChevronRightIcon className="w-3.5 h-3.5 text-gray-500" />
        )}
      </button>
      {open && <div className="p-3 space-y-3">{children}</div>}
    </div>
  );
}

export default function AdvancedSlicingPanel({
  params,
  onChange,
  materialPreset,
}: AdvancedSlicingPanelProps) {
  const update = (updates: Partial<SlicingParams>) => {
    onChange({ ...params, ...updates });
  };

  return (
    <div className="space-y-2">
      {/* Material Badge */}
      {materialPreset && (
        <div className="flex items-center gap-2 px-2 py-1 bg-blue-50 border border-blue-200 rounded-lg">
          <span className="text-xs text-blue-700">Material preset:</span>
          <span className="text-xs font-medium text-blue-900">{materialPreset}</span>
        </div>
      )}

      {/* Basic Parameters */}
      <Section title="Basic Parameters" defaultOpen={true}>
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Layer Height</label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                step="0.05"
                min="0.05"
                max="5"
                value={params.layerHeight}
                onChange={(e) => update({ layerHeight: parseFloat(e.target.value) || 0.3 })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
              <span className="text-xs text-gray-400">mm</span>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Line Width</label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="5"
                value={params.lineWidth}
                onChange={(e) => update({ lineWidth: parseFloat(e.target.value) || 0.6 })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
              <span className="text-xs text-gray-400">mm</span>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Print Speed</label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                step="100"
                min="100"
                value={params.printSpeed}
                onChange={(e) => update({ printSpeed: parseFloat(e.target.value) || 1000 })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
              <span className="text-xs text-gray-400 whitespace-nowrap">mm/m</span>
            </div>
          </div>
        </div>
      </Section>

      {/* Shell Settings */}
      <Section title="Shell / Walls">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Wall Count</label>
            <input
              type="number"
              min="0"
              max="10"
              value={params.wallCount}
              onChange={(e) => update({ wallCount: parseInt(e.target.value) || 0 })}
              className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Wall Width (mm)</label>
            <input
              type="number"
              step="0.1"
              min="0.1"
              max="5"
              value={params.wallWidth}
              onChange={(e) => update({ wallWidth: parseFloat(e.target.value) || 0.6 })}
              className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
            />
          </div>
        </div>
      </Section>

      {/* Infill Settings */}
      <Section title="Infill">
        {/* Pattern Grid with Previews */}
        <div className="grid grid-cols-4 gap-1.5">
          {INFILL_PATTERNS.map((p) => (
            <button
              key={p.value}
              onClick={() => update({ infillPattern: p.value })}
              className={`flex flex-col items-center gap-1 p-1.5 rounded-lg border-2 transition-colors ${
                params.infillPattern === p.value
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <InfillPatternPreview
                pattern={p.value}
                size={40}
                lineColor={params.infillPattern === p.value ? '#3b82f6' : '#9ca3af'}
              />
              <span className="text-xs text-gray-700 leading-tight text-center">{p.label}</span>
            </button>
          ))}
        </div>

        {/* Infill Density */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs text-gray-500">Infill Density</label>
            <span className="text-xs font-mono text-gray-700">{params.infillDensity}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            step="5"
            value={params.infillDensity}
            onChange={(e) => update({ infillDensity: parseInt(e.target.value) })}
            className="w-full h-1.5"
          />
        </div>
      </Section>

      {/* Seam Control */}
      <Section title="Seam Control">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Placement Mode</label>
          <div className="grid grid-cols-3 gap-1.5">
            {SEAM_MODES.map((m) => (
              <button
                key={m.value}
                onClick={() => update({ seamMode: m.value })}
                className={`px-2 py-1.5 text-xs rounded-md border transition-colors ${
                  params.seamMode === m.value
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>

        {params.seamMode === 'guided' && (
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Seam Angle (°)</label>
            <input
              type="number"
              step="15"
              min="0"
              max="360"
              value={params.seamAngle}
              onChange={(e) => update({ seamAngle: parseFloat(e.target.value) || 0 })}
              className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
            />
          </div>
        )}

        <div>
          <label className="block text-xs text-gray-500 mb-1">Seam Shape</label>
          <div className="grid grid-cols-4 gap-1.5">
            {SEAM_SHAPES.map((s) => (
              <button
                key={s.value}
                onClick={() => update({ seamShape: s.value })}
                className={`px-2 py-1.5 text-xs rounded-md border transition-colors ${
                  params.seamShape === s.value
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </Section>

      {/* Movement Settings */}
      <Section title="Movement">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Travel Speed</label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                step="500"
                min="100"
                value={params.travelSpeed}
                onChange={(e) => update({ travelSpeed: parseFloat(e.target.value) || 5000 })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
              <span className="text-xs text-gray-400 whitespace-nowrap">mm/m</span>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Z-Hop</label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                step="0.1"
                min="0"
                value={params.zHop}
                onChange={(e) => update({ zHop: parseFloat(e.target.value) || 0 })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
              <span className="text-xs text-gray-400">mm</span>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Retract Dist.</label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                step="0.5"
                min="0"
                value={params.retractDistance}
                onChange={(e) => update({ retractDistance: parseFloat(e.target.value) || 0 })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
              <span className="text-xs text-gray-400">mm</span>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Retract Speed</label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                step="100"
                min="100"
                value={params.retractSpeed}
                onChange={(e) => update({ retractSpeed: parseFloat(e.target.value) || 2400 })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
              <span className="text-xs text-gray-400 whitespace-nowrap">mm/m</span>
            </div>
          </div>
        </div>
      </Section>

      {/* Engage/Disengage */}
      <Section title="Engage / Disengage">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Lead-In Dist.</label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                step="0.5"
                min="0"
                value={params.leadInDistance}
                onChange={(e) => update({ leadInDistance: parseFloat(e.target.value) || 0 })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
              <span className="text-xs text-gray-400">mm</span>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Lead-In Angle</label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                step="5"
                min="0"
                max="90"
                value={params.leadInAngle}
                onChange={(e) => update({ leadInAngle: parseFloat(e.target.value) || 45 })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
              <span className="text-xs text-gray-400">°</span>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Lead-Out Dist.</label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                step="0.5"
                min="0"
                value={params.leadOutDistance}
                onChange={(e) => update({ leadOutDistance: parseFloat(e.target.value) || 0 })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
              <span className="text-xs text-gray-400">mm</span>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Lead-Out Angle</label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                step="5"
                min="0"
                max="90"
                value={params.leadOutAngle}
                onChange={(e) => update({ leadOutAngle: parseFloat(e.target.value) || 45 })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
              <span className="text-xs text-gray-400">°</span>
            </div>
          </div>
        </div>
      </Section>
    </div>
  );
}
