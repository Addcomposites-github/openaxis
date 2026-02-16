/**
 * ToolpathColorOverlay — Color mode selector + gradient legend for toolpath.
 *
 * Renders a dropdown to select the color overlay mode, a gradient legend bar,
 * and optional min/max range override inputs.
 */

import { useMemo } from 'react';
import { useWorkspaceStore } from '../stores/workspaceStore';
import {
  type ToolpathColorMode,
  COLOR_MODE_LABELS,
  COLOR_MODE_UNITS,
  getGradientStops,
  TYPE_COLORS,
} from '../utils/toolpathColorMaps';

const COLOR_MODES: ToolpathColorMode[] = [
  'type', 'speed', 'layer_time', 'deposition', 'reachability', 'layer', 'z_height',
];

export default function ToolpathColorOverlay() {
  const colorMode = useWorkspaceStore((s) => s.toolpathColorMode);
  const colorRange = useWorkspaceStore((s) => s.toolpathColorRange);
  const setToolpathColorMode = useWorkspaceStore((s) => s.setToolpathColorMode);
  const setToolpathColorRange = useWorkspaceStore((s) => s.setToolpathColorRange);

  const isContinuous = colorMode !== 'type' && colorMode !== 'reachability';

  const gradientStops = useMemo(() => {
    if (!isContinuous) return [];
    return getGradientStops(colorMode, colorRange);
  }, [colorMode, colorRange, isContinuous]);

  const gradientCSS = useMemo(() => {
    if (gradientStops.length === 0) return '';
    return `linear-gradient(to right, ${gradientStops.map((s) => s.color).join(', ')})`;
  }, [gradientStops]);

  return (
    <div className="bg-white rounded-lg shadow-md p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-gray-900">Color Overlay</h3>
      </div>

      {/* Mode Selector */}
      <select
        value={colorMode}
        onChange={(e) => setToolpathColorMode(e.target.value as ToolpathColorMode)}
        className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      >
        {COLOR_MODES.map((mode) => (
          <option key={mode} value={mode}>
            {COLOR_MODE_LABELS[mode]}
          </option>
        ))}
      </select>

      {/* Categorical Legend (type mode) */}
      {colorMode === 'type' && (
        <div className="grid grid-cols-2 gap-1">
          {Object.entries(TYPE_COLORS)
            .filter(([key]) => key !== 'default')
            .map(([key, [r, g, b]]) => (
              <div key={key} className="flex items-center gap-1.5">
                <div
                  className="w-3 h-3 rounded-sm flex-shrink-0"
                  style={{ backgroundColor: `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})` }}
                />
                <span className="text-xs text-gray-600 capitalize">{key}</span>
              </div>
            ))}
        </div>
      )}

      {/* Reachability Legend */}
      {colorMode === 'reachability' && (
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-sm bg-green-500" />
            <span className="text-xs text-gray-600">Reachable</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-sm bg-red-500" />
            <span className="text-xs text-gray-600">Unreachable</span>
          </div>
        </div>
      )}

      {/* Gradient Legend (continuous modes) */}
      {isContinuous && (
        <>
          <div
            className="h-4 rounded-sm"
            style={{ background: gradientCSS }}
          />
          <div className="flex justify-between text-xs text-gray-500">
            <span>{colorRange.min.toFixed(1)} {COLOR_MODE_UNITS[colorMode]}</span>
            <span>{COLOR_MODE_LABELS[colorMode]}</span>
            <span>{colorRange.max.toFixed(1)} {COLOR_MODE_UNITS[colorMode]}</span>
          </div>

          {/* Range Override */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-500 mb-0.5">Min</label>
              <input
                type="number"
                step="any"
                value={colorRange.min}
                onChange={(e) =>
                  setToolpathColorRange({ ...colorRange, min: parseFloat(e.target.value) || 0 })
                }
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-0.5">Max</label>
              <input
                type="number"
                step="any"
                value={colorRange.max}
                onChange={(e) =>
                  setToolpathColorRange({ ...colorRange, max: parseFloat(e.target.value) || 0 })
                }
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
