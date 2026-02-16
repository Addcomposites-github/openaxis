import { useMemo } from 'react';
import { Line } from '@react-three/drei';
import { toolpathPointToScene } from '../utils/units';
import {
  type ToolpathColorMode,
  type ColorRange,
  type SegmentColorInfo,
  getColorForMode,
  TYPE_COLORS,
} from '../utils/toolpathColorMaps';

export interface ToolpathSegment {
  type: string;
  layer: number;
  points: [number, number, number][];
  speed: number;
  extrusionRate: number;
}

interface ToolpathRendererProps {
  segments: ToolpathSegment[];
  currentLayer?: number;
  showAllLayers?: boolean;
  colorByType?: boolean;
  reachability?: boolean[] | null;
  /** Color overlay mode (defaults to 'type' if colorByType is true). */
  colorMode?: ToolpathColorMode;
  /** Min/max range for continuous color modes. */
  colorRange?: ColorRange;
}

/* ── colour look-up by segment type (legacy fallback) ──────────── */

function colorForType(type: string): [number, number, number] {
  return TYPE_COLORS[type] || TYPE_COLORS.default;
}

/** A single chunk of line-segment pairs with vertex colors. */
interface LineChunk {
  points: [number, number, number][];
  vertexColors: [number, number, number][];
}

/**
 * Maximum number of VERTICES per <Line> chunk.
 *
 * drei's <Line> internally creates Float32Array buffers. Very large arrays
 * (200K+ vertices) can exceed WebGL buffer limits or cause silent failures
 * on some drivers (notably ANGLE/Direct3D11 on Intel GPUs).
 *
 * 20,000 vertices = 10,000 line segments per chunk — a safe limit that
 * renders reliably while keeping draw calls reasonable (~25 draws for a
 * 250K-segment toolpath).
 */
const MAX_VERTICES_PER_CHUNK = 20_000;

/**
 * ToolpathRenderer — renders all toolpath segments using drei's <Line>.
 *
 * Uses drei's Line component with segments={true} which internally creates
 * LineSegments2 + LineSegmentsGeometry + LineMaterial — rendered as
 * instanced screen-aligned quads (meshes). This is GPU-compatible and
 * supports line widths > 1 pixel on all GPUs (unlike native GL_LINES).
 *
 * Large toolpaths are split into chunks of ≤ MAX_VERTICES_PER_CHUNK vertices
 * to avoid WebGL buffer size issues. Each chunk is a separate <Line> component.
 *
 * Supports 7 color overlay modes via the colorMode prop:
 * - type: segment type categorical coloring
 * - speed: viridis gradient by feed rate
 * - layer_time: viridis gradient by layer time
 * - deposition: viridis gradient by extrusion rate
 * - reachability: binary green/red
 * - layer: rainbow gradient by layer number
 * - z_height: viridis gradient by Z coordinate
 */
export default function ToolpathRenderer({
  segments,
  currentLayer,
  showAllLayers = false,
  colorByType = true,
  reachability,
  colorMode,
  colorRange,
}: ToolpathRendererProps) {
  // Determine the effective color mode: explicit prop > legacy colorByType flag
  const effectiveMode: ToolpathColorMode = colorMode ?? (colorByType ? 'type' : 'type');

  // Auto-compute range from visible segments if not provided
  const effectiveRange = useMemo<ColorRange>(() => {
    if (colorRange && (colorRange.min !== 0 || colorRange.max !== 100)) {
      return colorRange;
    }

    // Auto-range based on mode
    if (!segments || segments.length === 0) return { min: 0, max: 100 };

    const visible = showAllLayers
      ? segments
      : segments.filter((s) => s.layer === (currentLayer ?? 1));

    switch (effectiveMode) {
      case 'speed': {
        let min = Infinity, max = -Infinity;
        for (const seg of visible) {
          if (seg.type === 'travel') continue;
          if (seg.speed > 0) {
            min = Math.min(min, seg.speed);
            max = Math.max(max, seg.speed);
          }
        }
        return min <= max ? { min, max } : { min: 0, max: 1000 };
      }
      case 'deposition': {
        let min = Infinity, max = -Infinity;
        for (const seg of visible) {
          if (seg.type === 'travel') continue;
          if (seg.extrusionRate > 0) {
            min = Math.min(min, seg.extrusionRate);
            max = Math.max(max, seg.extrusionRate);
          }
        }
        return min <= max ? { min, max } : { min: 0, max: 10 };
      }
      case 'layer': {
        let min = Infinity, max = -Infinity;
        for (const seg of visible) {
          min = Math.min(min, seg.layer);
          max = Math.max(max, seg.layer);
        }
        return min <= max ? { min, max } : { min: 0, max: 1 };
      }
      case 'z_height': {
        let min = Infinity, max = -Infinity;
        for (const seg of visible) {
          for (const pt of seg.points) {
            const z = pt[2] ?? 0;
            min = Math.min(min, z);
            max = Math.max(max, z);
          }
        }
        return min <= max ? { min, max } : { min: 0, max: 100 };
      }
      default:
        return colorRange ?? { min: 0, max: 100 };
    }
  }, [segments, currentLayer, showAllLayers, effectiveMode, colorRange]);

  const chunks = useMemo<LineChunk[]>(() => {
    if (!segments || segments.length === 0) return [];

    // Filter segments by layer visibility
    const visible = showAllLayers
      ? segments
      : segments.filter((s) => s.layer === (currentLayer ?? 1));

    // Count total vertex pairs for logging
    let totalPairs = 0;
    for (const seg of visible) {
      if (seg.points.length >= 2) {
        totalPairs += seg.points.length - 1;
      }
    }

    if (totalPairs === 0) return [];

    // Pre-compute the starting global index for each visible segment
    // (We need this for reachability mapping which is indexed across ALL segments)
    const segmentStartIdx: number[] = [];
    if (reachability && reachability.length > 0) {
      // Build a mapping: for each segment in the full list, find its point offset
      let idx = 0;
      const fullOffsets = new Map<number, number>();
      for (let si = 0; si < segments.length; si++) {
        fullOffsets.set(si, idx);
        idx += segments[si].points.length;
      }
      // Now map visible segments back to their full indices
      for (const seg of visible) {
        const fullIdx = segments.indexOf(seg);
        segmentStartIdx.push(fullOffsets.get(fullIdx) ?? 0);
      }
    }

    // Build chunks — each chunk has at most MAX_VERTICES_PER_CHUNK vertices.
    // Since we use segments=true, vertices come in pairs: [startA, endA, startB, endB, ...]
    // We must never split a pair across chunks.
    const result: LineChunk[] = [];
    let curPts: [number, number, number][] = [];
    let curCols: [number, number, number][] = [];

    for (let vi = 0; vi < visible.length; vi++) {
      const seg = visible[vi];
      if (seg.points.length < 2) continue;

      const reachOffset = segmentStartIdx[vi] ?? 0;

      for (let pi = 0; pi < seg.points.length - 1; pi++) {
        // Check if adding this pair would exceed the chunk limit
        if (curPts.length + 2 > MAX_VERTICES_PER_CHUNK && curPts.length > 0) {
          result.push({ points: curPts, vertexColors: curCols });
          curPts = [];
          curCols = [];
        }

        const a = toolpathPointToScene(seg.points[pi]);
        const b = toolpathPointToScene(seg.points[pi + 1]);

        // Compute color based on mode
        let cA: [number, number, number];
        let cB: [number, number, number];

        if (effectiveMode === 'type') {
          // Fast path: same color for entire segment
          const c = colorForType(seg.type);
          cA = c;
          cB = c;
        } else {
          // Per-point color using color map
          const infoA: SegmentColorInfo = {
            type: seg.type,
            speed: seg.speed,
            extrusionRate: seg.extrusionRate,
            layer: seg.layer,
            pointZ: seg.points[pi][2] ?? 0,
            reachable: reachability ? reachability[reachOffset + pi] : undefined,
          };
          const infoB: SegmentColorInfo = {
            type: seg.type,
            speed: seg.speed,
            extrusionRate: seg.extrusionRate,
            layer: seg.layer,
            pointZ: seg.points[pi + 1][2] ?? 0,
            reachable: reachability ? reachability[reachOffset + pi + 1] : undefined,
          };
          cA = getColorForMode(infoA, effectiveMode, effectiveRange);
          cB = getColorForMode(infoB, effectiveMode, effectiveRange);
        }

        curPts.push(a, b);
        curCols.push(cA, cB);
      }
    }

    // Push final chunk
    if (curPts.length > 0) {
      result.push({ points: curPts, vertexColors: curCols });
    }

    console.log(
      `[ToolpathRenderer] Built ${result.length} chunks from ${totalPairs} line segments, ` +
      `${visible.length}/${segments.length} path segments visible, mode=${effectiveMode}`
    );

    return result;
  }, [segments, currentLayer, showAllLayers, effectiveMode, effectiveRange, reachability]);

  if (chunks.length === 0) return null;

  return (
    <group>
      {chunks.map((chunk, i) => (
        <Line
          key={i}
          points={chunk.points}
          vertexColors={chunk.vertexColors}
          segments
          lineWidth={1.5}
          toneMapped={false}
        />
      ))}
    </group>
  );
}
