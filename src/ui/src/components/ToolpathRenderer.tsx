import { useMemo } from 'react';
import { Line } from '@react-three/drei';
import { toolpathPointToScene } from '../utils/units';

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
}

/* ── colour look-up by segment type ─────────────────────────────── */
const TYPE_COLORS: Record<string, [number, number, number]> = {
  travel: [0.533, 0.533, 0.533],     // grey
  perimeter: [0.231, 0.510, 0.965],  // blue
  infill: [0.133, 0.773, 0.369],     // green
  support: [0.961, 0.620, 0.043],    // amber
  raft: [0.659, 0.333, 0.969],       // purple
  default: [0.937, 0.267, 0.267],    // red
};

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
 */
export default function ToolpathRenderer({
  segments,
  currentLayer,
  showAllLayers = false,
  colorByType = true,
  // reachability reserved for future use
  reachability: _reachability,
}: ToolpathRendererProps) {
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

    // Build chunks — each chunk has at most MAX_VERTICES_PER_CHUNK vertices.
    // Since we use segments=true, vertices come in pairs: [startA, endA, startB, endB, ...]
    // We must never split a pair across chunks.
    const result: LineChunk[] = [];
    let curPts: [number, number, number][] = [];
    let curCols: [number, number, number][] = [];

    for (const seg of visible) {
      if (seg.points.length < 2) continue;

      const c = colorByType ? colorForType(seg.type) : TYPE_COLORS.default;

      for (let pi = 0; pi < seg.points.length - 1; pi++) {
        // Check if adding this pair would exceed the chunk limit
        if (curPts.length + 2 > MAX_VERTICES_PER_CHUNK && curPts.length > 0) {
          result.push({ points: curPts, vertexColors: curCols });
          curPts = [];
          curCols = [];
        }

        const a = toolpathPointToScene(seg.points[pi]);
        const b = toolpathPointToScene(seg.points[pi + 1]);

        curPts.push(a, b);
        curCols.push(c, c);
      }
    }

    // Push final chunk
    if (curPts.length > 0) {
      result.push({ points: curPts, vertexColors: curCols });
    }

    console.log(
      `[ToolpathRenderer] Built ${result.length} chunks from ${totalPairs} line segments, ` +
      `${visible.length}/${segments.length} path segments visible`
    );

    return result;
  }, [segments, currentLayer, showAllLayers, colorByType]);

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
