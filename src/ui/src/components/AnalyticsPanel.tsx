/**
 * AnalyticsPanel — Toolpath analytics with inline SVG charts.
 *
 * Provides:
 * - Speed over path (line chart)
 * - Deposition rate over path
 * - Layer point distribution (bar chart)
 * - Quality per layer (stacked bar)
 *
 * Uses lightweight inline SVG — no external charting library required.
 */

import { useMemo, useState } from 'react';
import { useWorkspaceStore } from '../stores/workspaceStore';

// ─── Mini Line Chart ─────────────────────────────────────────────────────────

function MiniLineChart({
  data,
  width = 280,
  height = 80,
  color = '#3b82f6',
  label,
  unit,
}: {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  label: string;
  unit?: string;
}) {
  if (data.length === 0) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pad = 4;
  const chartW = width - pad * 2;
  const chartH = height - pad * 2 - 14; // leave room for label

  const points = data.map((v, i) => {
    const x = pad + (i / Math.max(data.length - 1, 1)) * chartW;
    const y = pad + 14 + chartH - ((v - min) / range) * chartH;
    return `${x},${y}`;
  });

  const avg = data.reduce((a, b) => a + b, 0) / data.length;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-2">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-700">{label}</span>
        <span className="text-xs text-gray-500">
          avg: {avg.toFixed(1)}{unit ? ` ${unit}` : ''}
        </span>
      </div>
      <svg width={width} height={height} className="w-full">
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((f) => {
          const y = pad + 14 + chartH * (1 - f);
          return (
            <line
              key={f}
              x1={pad}
              y1={y}
              x2={width - pad}
              y2={y}
              stroke="#e5e7eb"
              strokeWidth={0.5}
            />
          );
        })}
        {/* Data line */}
        <polyline
          points={points.join(' ')}
          fill="none"
          stroke={color}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Min/Max labels */}
        <text x={width - pad} y={pad + 14} textAnchor="end" fontSize={8} fill="#9ca3af">
          {max.toFixed(0)}
        </text>
        <text x={width - pad} y={pad + 14 + chartH} textAnchor="end" fontSize={8} fill="#9ca3af">
          {min.toFixed(0)}
        </text>
      </svg>
    </div>
  );
}

// ─── Mini Bar Chart ──────────────────────────────────────────────────────────

function MiniBarChart({
  data,
  width = 280,
  height = 80,
  color = '#10b981',
  label,
}: {
  data: { label: string; value: number }[];
  width?: number;
  height?: number;
  color?: string;
  label: string;
}) {
  if (data.length === 0) return null;

  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const pad = 4;
  const chartH = height - pad * 2 - 14;
  const barW = Math.max(2, (width - pad * 2) / data.length - 1);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-2">
      <span className="text-xs font-medium text-gray-700">{label}</span>
      <svg width={width} height={height} className="w-full mt-1">
        {data.map((d, i) => {
          const x = pad + i * (barW + 1);
          const barH = (d.value / maxVal) * chartH;
          const y = pad + 14 + chartH - barH;
          return (
            <rect
              key={i}
              x={x}
              y={y}
              width={barW}
              height={barH}
              fill={color}
              opacity={0.7}
              rx={1}
            >
              <title>{`Layer ${d.label}: ${d.value} points`}</title>
            </rect>
          );
        })}
      </svg>
    </div>
  );
}

// ─── AnalyticsPanel ──────────────────────────────────────────────────────────

interface AnalyticsPanelProps {
  compact?: boolean;
}

export default function AnalyticsPanel({ compact = false }: AnalyticsPanelProps) {
  const toolpathData = useWorkspaceStore((s) => s.toolpathData);
  const [activeTab, setActiveTab] = useState<'speed' | 'deposition' | 'layers' | 'quality'>('speed');

  // Compute analytics data
  const analytics = useMemo(() => {
    if (!toolpathData?.segments) return null;

    const segments = toolpathData.segments;

    // Speed data (per segment, excluding travel)
    const speeds: number[] = [];
    const depositions: number[] = [];
    const layerPointCounts: Map<number, number> = new Map();
    const layerSegmentTypes: Map<number, { perimeter: number; infill: number; travel: number }> = new Map();

    for (const seg of segments) {
      const layer = seg.layer;

      // Accumulate points per layer
      const pts = seg.points?.length || 0;
      layerPointCounts.set(layer, (layerPointCounts.get(layer) || 0) + pts);

      // Count segment types per layer
      const types = layerSegmentTypes.get(layer) || { perimeter: 0, infill: 0, travel: 0 };
      const segType = (seg.type || '').toLowerCase();
      if (segType.includes('perim') || segType.includes('wall')) types.perimeter++;
      else if (segType.includes('infill') || segType.includes('fill')) types.infill++;
      else if (segType.includes('travel') || segType.includes('move')) types.travel++;
      layerSegmentTypes.set(layer, types);

      // Skip travel for speed/deposition charts
      if (segType.includes('travel') || segType.includes('move') || segType.includes('rapid')) continue;

      speeds.push(seg.speed || 0);
      depositions.push(seg.extrusionRate ?? 1.0);
    }

    // Layer bar chart data
    const layerBars = Array.from(layerPointCounts.entries())
      .sort((a, b) => a[0] - b[0])
      .slice(0, 100) // limit to 100 bars
      .map(([layer, count]) => ({ label: String(layer), value: count }));

    // Quality per layer (simple: ratio of perimeter+infill to total)
    const qualityBars = Array.from(layerSegmentTypes.entries())
      .sort((a, b) => a[0] - b[0])
      .slice(0, 100)
      .map(([layer, types]) => {
        const total = types.perimeter + types.infill + types.travel;
        const quality = total > 0 ? ((types.perimeter + types.infill) / total) * 100 : 100;
        return { label: String(layer), value: Math.round(quality) };
      });

    return { speeds, depositions, layerBars, qualityBars };
  }, [toolpathData]);

  if (!analytics || !toolpathData) {
    return (
      <div className="p-3 text-xs text-gray-500 text-center">
        No toolpath data available for analytics.
      </div>
    );
  }

  const tabs = [
    { key: 'speed' as const, label: 'Speed' },
    { key: 'deposition' as const, label: 'Deposition' },
    { key: 'layers' as const, label: 'Layers' },
    { key: 'quality' as const, label: 'Quality' },
  ];

  return (
    <div className="space-y-2">
      {!compact && (
        <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
          Analytics
        </h3>
      )}

      {/* Tab selector */}
      <div className="flex gap-1">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-2 py-1 text-xs rounded-md transition-colors ${
              activeTab === tab.key
                ? 'bg-blue-100 text-blue-700 font-medium'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Chart content */}
      {activeTab === 'speed' && (
        <MiniLineChart
          data={analytics.speeds}
          color="#3b82f6"
          label="Speed (per segment)"
          unit="mm/min"
        />
      )}

      {activeTab === 'deposition' && (
        <MiniLineChart
          data={analytics.depositions}
          color="#f59e0b"
          label="Deposition Rate (per segment)"
        />
      )}

      {activeTab === 'layers' && (
        <MiniBarChart
          data={analytics.layerBars}
          color="#10b981"
          label="Points per Layer"
        />
      )}

      {activeTab === 'quality' && (
        <MiniBarChart
          data={analytics.qualityBars}
          color="#8b5cf6"
          label="Print Segment % per Layer"
        />
      )}

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-gray-50 rounded p-1.5">
          <div className="text-xs font-semibold text-gray-900">
            {analytics.speeds.length > 0
              ? (analytics.speeds.reduce((a, b) => a + b, 0) / analytics.speeds.length).toFixed(0)
              : '—'}
          </div>
          <div className="text-xs text-gray-500">Avg Speed</div>
        </div>
        <div className="bg-gray-50 rounded p-1.5">
          <div className="text-xs font-semibold text-gray-900">
            {analytics.layerBars.length}
          </div>
          <div className="text-xs text-gray-500">Layers</div>
        </div>
        <div className="bg-gray-50 rounded p-1.5">
          <div className="text-xs font-semibold text-gray-900">
            {toolpathData.statistics.totalSegments}
          </div>
          <div className="text-xs text-gray-500">Segments</div>
        </div>
      </div>
    </div>
  );
}
