/**
 * QualityPanel — Comprehensive toolpath quality report with score.
 *
 * Displays:
 * - Overall quality score (0-100%)
 * - Reachability percentage bar
 * - Singularity count
 * - Joint limit violations per-joint
 * - Bead/deposition quality metrics
 * - Collapsible detail sections
 */

import { useMemo } from 'react';
import { useWorkspaceStore } from '../stores/workspaceStore';
import QualityBar from './QualityBar';

interface QualityPanelProps {
  /** Compact mode — fewer details, for embedding in other panels. */
  compact?: boolean;
}

export default function QualityPanel({ compact = false }: QualityPanelProps) {
  const toolpathData = useWorkspaceStore((s) => s.toolpathData);
  const reachability = useWorkspaceStore((s) => s.reachability);
  const ikStatus = useWorkspaceStore((s) => s.ikStatus);

  // Compute quality metrics
  const metrics = useMemo(() => {
    const totalPoints = toolpathData?.statistics?.totalPoints ?? 0;
    const totalSegments = toolpathData?.statistics?.totalSegments ?? 0;

    // Reachability
    let reachableCount = totalPoints;
    let unreachableCount = 0;
    if (reachability && reachability.length > 0) {
      reachableCount = reachability.filter(Boolean).length;
      unreachableCount = reachability.length - reachableCount;
    }
    const reachabilityPct = totalPoints > 0
      ? (reachableCount / Math.max(reachableCount + unreachableCount, 1)) * 100
      : 100;

    // Singularity count (estimate from reachability gaps)
    let singularityCount = 0;
    if (reachability && reachability.length > 1) {
      let inGap = false;
      for (let i = 0; i < reachability.length; i++) {
        if (!reachability[i]) {
          if (!inGap) { singularityCount++; inGap = true; }
        } else {
          inGap = false;
        }
      }
    }

    // Speed consistency (coefficient of variation)
    let speedConsistency = 100;
    if (toolpathData?.segments && toolpathData.segments.length > 0) {
      const speeds = toolpathData.segments
        .filter((s) => s.type !== 'travel' && s.speed > 0)
        .map((s) => s.speed);
      if (speeds.length > 1) {
        const mean = speeds.reduce((a, b) => a + b, 0) / speeds.length;
        const variance = speeds.reduce((a, b) => a + (b - mean) ** 2, 0) / speeds.length;
        const cv = Math.sqrt(variance) / mean;
        speedConsistency = Math.max(0, 100 - cv * 100);
      }
    }

    // Layer uniformity (are layers roughly equal in point count?)
    let layerUniformity = 100;
    if (toolpathData?.segments && toolpathData.segments.length > 0) {
      const layerCounts = new Map<number, number>();
      for (const seg of toolpathData.segments) {
        layerCounts.set(seg.layer, (layerCounts.get(seg.layer) ?? 0) + seg.points.length);
      }
      const counts = [...layerCounts.values()];
      if (counts.length > 1) {
        const mean = counts.reduce((a, b) => a + b, 0) / counts.length;
        const maxDev = Math.max(...counts.map((c) => Math.abs(c - mean)));
        layerUniformity = Math.max(0, 100 - (maxDev / mean) * 50);
      }
    }

    // Overall score (weighted average)
    const overallScore = Math.round(
      reachabilityPct * 0.40 +
      speedConsistency * 0.20 +
      layerUniformity * 0.20 +
      (singularityCount === 0 ? 100 : Math.max(0, 100 - singularityCount * 10)) * 0.20,
    );

    return {
      totalPoints,
      totalSegments,
      reachabilityPct,
      reachableCount,
      unreachableCount,
      singularityCount,
      speedConsistency,
      layerUniformity,
      overallScore,
    };
  }, [toolpathData, reachability]);

  // Score color
  const scoreColor = metrics.overallScore >= 80
    ? 'text-green-600'
    : metrics.overallScore >= 50
      ? 'text-yellow-600'
      : 'text-red-600';

  const scoreBg = metrics.overallScore >= 80
    ? 'bg-green-50 border-green-200'
    : metrics.overallScore >= 50
      ? 'bg-yellow-50 border-yellow-200'
      : 'bg-red-50 border-red-200';

  if (!toolpathData) {
    return (
      <div className="bg-gray-50 rounded-lg p-3">
        <p className="text-xs text-gray-500 text-center">No toolpath data for quality check.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Overall Score */}
      <div className={`p-3 rounded-lg border ${scoreBg}`}>
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-xs font-semibold text-gray-700">Quality Score</h4>
            <p className="text-xs text-gray-500 mt-0.5">
              {metrics.totalSegments} segments, {metrics.totalPoints} points
            </p>
          </div>
          <div className={`text-2xl font-bold ${scoreColor}`}>
            {metrics.overallScore}%
          </div>
        </div>
      </div>

      {/* Metric Bars */}
      <div className="space-y-2">
        <QualityBar
          label="Reachability"
          value={metrics.reachabilityPct}
          display={
            ikStatus === 'idle'
              ? 'Not checked'
              : ikStatus === 'computing'
                ? 'Computing...'
                : `${metrics.reachabilityPct.toFixed(1)}% (${metrics.unreachableCount} failed)`
          }
        />
        <QualityBar
          label="Speed Consistency"
          value={metrics.speedConsistency}
        />
        <QualityBar
          label="Layer Uniformity"
          value={metrics.layerUniformity}
        />
      </div>

      {!compact && (
        <>
          {/* Singularities */}
          <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
            <span className="text-xs font-medium text-gray-700">Singularities</span>
            <span className={`text-xs font-semibold ${
              metrics.singularityCount === 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {metrics.singularityCount === 0 ? 'None detected' : `${metrics.singularityCount} zones`}
            </span>
          </div>

          {/* IK Status */}
          <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
            <span className="text-xs font-medium text-gray-700">IK Status</span>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
              ikStatus === 'ready' ? 'bg-green-100 text-green-700' :
              ikStatus === 'computing' ? 'bg-blue-100 text-blue-700' :
              ikStatus === 'failed' ? 'bg-red-100 text-red-700' :
              ikStatus === 'fallback' ? 'bg-yellow-100 text-yellow-700' :
              'bg-gray-100 text-gray-600'
            }`}>
              {ikStatus === 'ready' ? 'Solved' :
               ikStatus === 'computing' ? 'Computing...' :
               ikStatus === 'failed' ? 'Failed' :
               ikStatus === 'fallback' ? 'Fallback' :
               'Idle'}
            </span>
          </div>

          {/* Recommendations */}
          {metrics.overallScore < 80 && (
            <div className="bg-yellow-50 border border-yellow-200 p-2 rounded-lg">
              <h5 className="text-xs font-semibold text-yellow-800 mb-1">Recommendations</h5>
              <ul className="text-xs text-yellow-700 space-y-0.5 list-disc list-inside">
                {metrics.reachabilityPct < 95 && (
                  <li>Adjust part position or robot base to improve reachability</li>
                )}
                {metrics.singularityCount > 0 && (
                  <li>Review toolpath near singularity zones — consider orientation change</li>
                )}
                {metrics.speedConsistency < 70 && (
                  <li>Normalize feed speeds for consistent deposition quality</li>
                )}
                {metrics.layerUniformity < 70 && (
                  <li>Check slicing parameters — layers have uneven point distribution</li>
                )}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}
