/**
 * PostProcessorPanel — Export format selector, event code editor, zone controls.
 *
 * Replaces the basic "Export G-code" button with a full post processor UI:
 * - Format selector (G-code, ABB RAPID, KUKA KRL, Fanuc LS)
 * - Event hook editor (program start/end, layer start/end, process on/off)
 * - Motion parameter controls (speed, zone, blending)
 * - Template variable reference
 * - Export button with file download
 */

import { useState, useEffect } from 'react';
import {
  DocumentArrowDownIcon,
  ChevronDownIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import { usePostProcessorStore, type ExportFormat, type EventHooks } from '../stores/postProcessorStore';
import { useWorkspaceStore } from '../stores/workspaceStore';
import { apiClient } from '../api/client';

const FORMAT_ICONS: Record<ExportFormat, string> = {
  gcode: 'G',
  rapid: 'R',
  krl: 'K',
  fanuc: 'F',
};

const ZONE_OPTIONS = ['fine', 'z0', 'z1', 'z5', 'z10', 'z50', 'z100', 'z200'];

const HOOK_LABELS: { key: keyof EventHooks; label: string; desc: string }[] = [
  { key: 'programStart', label: 'Program Start', desc: 'Code after header initialization' },
  { key: 'programEnd', label: 'Program End', desc: 'Code before footer' },
  { key: 'layerStart', label: 'Layer Start', desc: 'Code at beginning of each layer' },
  { key: 'layerEnd', label: 'Layer End', desc: 'Code at end of each layer' },
  { key: 'processOn', label: 'Process On', desc: 'Code when deposition/welding starts' },
  { key: 'processOff', label: 'Process Off', desc: 'Code when deposition/welding stops' },
  { key: 'beforePoint', label: 'Before Point', desc: 'Code before each motion command' },
  { key: 'afterPoint', label: 'After Point', desc: 'Code after each motion command' },
];

const TEMPLATE_VARS = [
  '{x}, {y}, {z}', '{rx}, {ry}, {rz}', '{speed}',
  '{depositionFactor}', '{segmentType}', '{layerIndex}',
  '{time}', '{toolName}', '{pointIndex}',
];

export default function PostProcessorPanel() {
  const config = usePostProcessorStore((s) => s.config);
  const availableFormats = usePostProcessorStore((s) => s.availableFormats);
  const setFormat = usePostProcessorStore((s) => s.setFormat);
  const setConfig = usePostProcessorStore((s) => s.setConfig);
  const setHook = usePostProcessorStore((s) => s.setHook);
  const setLastExportResult = usePostProcessorStore((s) => s.setLastExportResult);
  const loadFormats = usePostProcessorStore((s) => s.loadFormatsFromBackend);

  const toolpathData = useWorkspaceStore((s) => s.toolpathData);

  // Fetch available formats from backend on mount
  useEffect(() => {
    loadFormats();
  }, [loadFormats]);

  const [hooksExpanded, setHooksExpanded] = useState(false);
  const [varsExpanded, setVarsExpanded] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  const selectedFormat = availableFormats.find((f) => f.id === config.format);

  // ── Export handler ─────────────────────────────────────────────────

  const handleExport = async () => {
    if (!toolpathData) {
      setNotification('No toolpath to export');
      setTimeout(() => setNotification(null), 2000);
      return;
    }

    setExporting(true);
    setNotification(`Exporting ${selectedFormat?.name ?? config.format}...`);

    try {
      // Build config for backend
      const exportConfig = {
        format_name: config.format,
        default_speed: config.defaultSpeed,
        travel_speed: config.travelSpeed,
        zone_data: config.zoneData,
        blending: config.blending,
        tool_name: config.toolName,
        work_object: config.workObject,
        program_name: config.programName,
        hooks: {
          program_start: config.hooks.programStart,
          program_end: config.hooks.programEnd,
          layer_start: config.hooks.layerStart,
          layer_end: config.hooks.layerEnd,
          process_on: config.hooks.processOn,
          process_off: config.hooks.processOff,
          before_point: config.hooks.beforePoint,
          after_point: config.hooks.afterPoint,
        },
      };

      let content: string;
      let ext: string = selectedFormat?.extension ?? '.gcode';

      try {
        const response = await apiClient.post('/api/postprocessor/export', {
          toolpathId: toolpathData.id,
          format: config.format,
          config: exportConfig,
        });

        if (response.data?.status === 'success' && response.data?.data?.content) {
          content = response.data.data.content;
          ext = response.data.data.extension || ext;
          setLastExportResult({
            content,
            extension: ext,
            lines: response.data.data.lines || 0,
            size: response.data.data.size || content.length,
          });
          setNotification(`Exported ${response.data.data.lines} lines as ${response.data.data.formatName || config.format}`);
        } else {
          throw new Error('Backend returned no content');
        }
      } catch {
        // Fallback: use the basic G-code export
        content = generateFallbackGCode(toolpathData);
        ext = '.gcode';
        setNotification('Exported G-code (offline mode)');
      }

      // Download file
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${config.programName}${ext}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setTimeout(() => setNotification(null), 3000);
    } catch (error: any) {
      setNotification(`Error: ${error.message}`);
      setTimeout(() => setNotification(null), 3000);
    } finally {
      setExporting(false);
    }
  };

  const generateFallbackGCode = (data: typeof toolpathData): string => {
    if (!data) return '';
    let gcode = '; OpenAxis Generated G-code (offline)\n';
    gcode += `; Process: ${data.processType}\n`;
    gcode += `; Layers: ${data.totalLayers}\n`;
    gcode += 'G21\nG90\nG28\n\n';
    data.segments.forEach((seg) => {
      seg.points.forEach((pt, i) => {
        const cmd = i === 0 ? 'G0' : 'G1';
        const f = i > 0 ? ` F${seg.speed || 1000}` : '';
        gcode += `${cmd} X${pt[0].toFixed(3)} Y${pt[1].toFixed(3)}${f}\n`;
      });
    });
    gcode += '\nG28\nM84\n';
    return gcode;
  };

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      {/* Notification */}
      {notification && (
        <div className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg">
          {notification}
        </div>
      )}

      {/* Format Selector */}
      <div>
        <h4 className="text-xs font-semibold text-gray-900 mb-2">Export Format</h4>
        <div className="grid grid-cols-2 gap-2">
          {availableFormats.map((fmt) => (
            <button
              key={fmt.id}
              onClick={() => setFormat(fmt.id)}
              className={`flex items-center gap-2 px-3 py-2.5 border-2 rounded-lg transition-colors text-left ${
                config.format === fmt.id
                  ? 'border-blue-600 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <span className={`text-lg font-bold ${
                config.format === fmt.id ? 'text-blue-600' : 'text-gray-400'
              }`}>
                {FORMAT_ICONS[fmt.id]}
              </span>
              <div>
                <div className="text-xs font-medium">{fmt.name}</div>
                <div className="text-xs text-gray-400">{fmt.extension}</div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Program Name */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Program Name</label>
        <input
          type="text"
          value={config.programName}
          onChange={(e) => setConfig({ programName: e.target.value })}
          className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* Motion Parameters */}
      <div>
        <h4 className="text-xs font-semibold text-gray-900 mb-2">Motion Parameters</h4>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Default Speed</label>
            <input
              type="number"
              value={config.defaultSpeed}
              onChange={(e) => setConfig({ defaultSpeed: parseFloat(e.target.value) || 0 })}
              className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">Travel Speed</label>
            <input
              type="number"
              value={config.travelSpeed}
              onChange={(e) => setConfig({ travelSpeed: parseFloat(e.target.value) || 0 })}
              className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
            />
          </div>
        </div>
      </div>

      {/* Format-specific controls */}
      {config.format === 'rapid' && (
        <div>
          <h4 className="text-xs font-semibold text-gray-900 mb-2">RAPID Settings</h4>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-500 mb-0.5">Zone Data</label>
              <select
                value={config.zoneData}
                onChange={(e) => setConfig({ zoneData: e.target.value })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
              >
                {ZONE_OPTIONS.map((z) => (
                  <option key={z} value={z}>{z}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-0.5">Tool Name</label>
              <input
                type="text"
                value={config.toolName}
                onChange={(e) => setConfig({ toolName: e.target.value })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
            </div>
          </div>
        </div>
      )}

      {config.format === 'krl' && (
        <div>
          <h4 className="text-xs font-semibold text-gray-900 mb-2">KRL Settings</h4>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-500 mb-0.5">C_DIS (mm)</label>
              <input
                type="number"
                step="0.5"
                value={config.blending}
                onChange={(e) => setConfig({ blending: parseFloat(e.target.value) || 0 })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-0.5">Tool Data</label>
              <input
                type="text"
                value={config.toolName}
                onChange={(e) => setConfig({ toolName: e.target.value })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
            </div>
          </div>
        </div>
      )}

      {config.format === 'fanuc' && (
        <div>
          <h4 className="text-xs font-semibold text-gray-900 mb-2">Fanuc Settings</h4>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-500 mb-0.5">CNT (0-100)</label>
              <input
                type="number"
                min="0"
                max="100"
                value={config.blending}
                onChange={(e) => setConfig({ blending: parseFloat(e.target.value) || 0 })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-0.5">User Tool</label>
              <input
                type="text"
                value={config.toolName}
                onChange={(e) => setConfig({ toolName: e.target.value })}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded font-mono"
              />
            </div>
          </div>
        </div>
      )}

      {/* Event Hooks (collapsible) */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <button
          onClick={() => setHooksExpanded(!hooksExpanded)}
          className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-50 transition-colors"
        >
          <span className="text-xs font-semibold text-gray-900">Event Hooks</span>
          {hooksExpanded ? (
            <ChevronDownIcon className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRightIcon className="w-4 h-4 text-gray-500" />
          )}
        </button>

        {hooksExpanded && (
          <div className="px-3 pb-3 space-y-3 border-t border-gray-100 pt-3">
            {HOOK_LABELS.map(({ key, label, desc }) => (
              <div key={key}>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">
                  {label}
                </label>
                <p className="text-xs text-gray-400 mb-1">{desc}</p>
                <textarea
                  rows={2}
                  value={config.hooks[key]}
                  onChange={(e) => setHook(key, e.target.value)}
                  placeholder={`Custom ${label.toLowerCase()} code...`}
                  className="w-full px-2 py-1 text-xs font-mono border border-gray-300 rounded resize-y focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            ))}

            {/* Template Variables Reference */}
            <div className="border-t border-gray-100 pt-2">
              <button
                onClick={() => setVarsExpanded(!varsExpanded)}
                className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
              >
                {varsExpanded ? '▼' : '▶'} Template Variables
              </button>
              {varsExpanded && (
                <div className="mt-1 bg-gray-50 p-2 rounded text-xs font-mono text-gray-600 space-y-0.5">
                  {TEMPLATE_VARS.map((v) => (
                    <div key={v}>{v}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Export Button */}
      <button
        onClick={handleExport}
        disabled={!toolpathData || exporting}
        className={`w-full flex items-center justify-center space-x-2 px-4 py-3 rounded-lg transition-colors ${
          toolpathData && !exporting
            ? 'bg-blue-600 text-white hover:bg-blue-700'
            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
        }`}
      >
        <DocumentArrowDownIcon className="w-5 h-5" />
        <span className="text-sm font-medium">
          {exporting ? 'Exporting...' : `Export ${selectedFormat?.name ?? 'Program'}`}
        </span>
      </button>

      {/* Format Info */}
      {selectedFormat && (
        <div className="bg-gray-50 p-2 rounded-lg">
          <p className="text-xs text-gray-500">
            <strong>{selectedFormat.name}</strong> ({selectedFormat.vendor}) — {selectedFormat.description}
          </p>
          <p className="text-xs text-gray-400 mt-1 font-mono">
            Powered by openaxis.postprocessor
          </p>
        </div>
      )}
    </div>
  );
}
