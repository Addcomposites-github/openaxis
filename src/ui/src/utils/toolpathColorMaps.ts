/**
 * toolpathColorMaps — color mapping utilities for toolpath visualization.
 *
 * Provides 7 color overlay modes:
 * - type:        Categorical by segment type (perimeter, infill, travel, etc.)
 * - speed:       Continuous gradient by feed rate
 * - layer_time:  Continuous gradient by time spent per layer
 * - deposition:  Continuous gradient by extrusion/deposition rate
 * - reachability: Binary red/green for IK reachability
 * - layer:       Rainbow gradient by layer index
 * - z_height:    Continuous gradient by Z coordinate
 */

export type ToolpathColorMode =
  | 'type'
  | 'speed'
  | 'layer_time'
  | 'deposition'
  | 'reachability'
  | 'layer'
  | 'z_height';

export interface ColorRange {
  min: number;
  max: number;
}

// ─── Categorical Colors (type mode) ───────────────────────────────────────

export const TYPE_COLORS: Record<string, [number, number, number]> = {
  travel:    [0.533, 0.533, 0.533],    // grey
  perimeter: [0.231, 0.510, 0.965],    // blue
  infill:    [0.133, 0.773, 0.369],    // green
  support:   [0.961, 0.620, 0.043],    // amber
  raft:      [0.659, 0.333, 0.969],    // purple
  brim:      [0.369, 0.808, 0.808],    // teal
  default:   [0.937, 0.267, 0.267],    // red
};

// ─── Viridis-like Gradient (continuous modes) ────────────────────────────

const VIRIDIS_STOPS: [number, number, number][] = [
  [0.267, 0.004, 0.329],  // dark purple
  [0.282, 0.141, 0.459],  // purple
  [0.244, 0.290, 0.537],  // blue-purple
  [0.190, 0.408, 0.557],  // blue
  [0.149, 0.510, 0.557],  // teal-blue
  [0.122, 0.616, 0.537],  // teal
  [0.208, 0.718, 0.471],  // green-teal
  [0.431, 0.804, 0.349],  // green
  [0.675, 0.867, 0.204],  // yellow-green
  [0.992, 0.906, 0.145],  // yellow
];

/** Interpolate the viridis gradient at parameter t ∈ [0, 1]. */
function viridis(t: number): [number, number, number] {
  const clamped = Math.max(0, Math.min(1, t));
  const idx = clamped * (VIRIDIS_STOPS.length - 1);
  const lo = Math.floor(idx);
  const hi = Math.min(lo + 1, VIRIDIS_STOPS.length - 1);
  const frac = idx - lo;
  return [
    VIRIDIS_STOPS[lo][0] + (VIRIDIS_STOPS[hi][0] - VIRIDIS_STOPS[lo][0]) * frac,
    VIRIDIS_STOPS[lo][1] + (VIRIDIS_STOPS[hi][1] - VIRIDIS_STOPS[lo][1]) * frac,
    VIRIDIS_STOPS[lo][2] + (VIRIDIS_STOPS[hi][2] - VIRIDIS_STOPS[lo][2]) * frac,
  ];
}

// ─── Rainbow Gradient (layer mode) ────────────────────────────────────────

function rainbow(t: number): [number, number, number] {
  const clamped = Math.max(0, Math.min(1, t));
  // HSL to RGB with S=0.85, L=0.55
  const h = clamped * 360;
  const s = 0.85;
  const l = 0.55;
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  let r = 0, g = 0, b = 0;
  if (h < 60) { r = c; g = x; }
  else if (h < 120) { r = x; g = c; }
  else if (h < 180) { g = c; b = x; }
  else if (h < 240) { g = x; b = c; }
  else if (h < 300) { r = x; b = c; }
  else { r = c; b = x; }
  return [r + m, g + m, b + m];
}

// ─── Main Color Function ──────────────────────────────────────────────────

export interface SegmentColorInfo {
  type: string;
  speed: number;
  extrusionRate: number;
  layer: number;
  pointZ: number;
  reachable?: boolean;
  layerTime?: number;
}

/**
 * Get color for a toolpath point based on the active color mode.
 * Returns [r, g, b] in 0-1 range.
 */
export function getColorForMode(
  info: SegmentColorInfo,
  mode: ToolpathColorMode,
  range: ColorRange,
): [number, number, number] {
  switch (mode) {
    case 'type':
      return TYPE_COLORS[info.type] || TYPE_COLORS.default;

    case 'speed': {
      const t = range.max > range.min
        ? (info.speed - range.min) / (range.max - range.min)
        : 0.5;
      return viridis(t);
    }

    case 'layer_time': {
      const t = range.max > range.min
        ? ((info.layerTime ?? 0) - range.min) / (range.max - range.min)
        : 0.5;
      return viridis(t);
    }

    case 'deposition': {
      const t = range.max > range.min
        ? (info.extrusionRate - range.min) / (range.max - range.min)
        : 0.5;
      return viridis(t);
    }

    case 'reachability':
      return info.reachable !== false
        ? [0.133, 0.773, 0.369]   // green — reachable
        : [0.937, 0.267, 0.267];  // red — unreachable

    case 'layer': {
      const t = range.max > range.min
        ? (info.layer - range.min) / (range.max - range.min)
        : 0.5;
      return rainbow(t);
    }

    case 'z_height': {
      const t = range.max > range.min
        ? (info.pointZ - range.min) / (range.max - range.min)
        : 0.5;
      return viridis(t);
    }

    default:
      return TYPE_COLORS.default;
  }
}

// ─── Gradient Legend Helpers ───────────────────────────────────────────────

/** Generate an array of N gradient stops for drawing a legend bar. */
export function getGradientStops(
  mode: ToolpathColorMode,
  range: ColorRange,
  steps: number = 32,
): { t: number; color: string }[] {
  const stops: { t: number; color: string }[] = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const value = range.min + t * (range.max - range.min);
    const info: SegmentColorInfo = {
      type: 'perimeter',
      speed: mode === 'speed' ? value : 0,
      extrusionRate: mode === 'deposition' ? value : 0,
      layer: mode === 'layer' ? Math.round(value) : 0,
      pointZ: mode === 'z_height' ? value : 0,
      layerTime: mode === 'layer_time' ? value : 0,
      reachable: true,
    };
    const [r, g, b] = getColorForMode(info, mode, range);
    stops.push({
      t,
      color: `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`,
    });
  }
  return stops;
}

/** Human-readable label for a color mode. */
export const COLOR_MODE_LABELS: Record<ToolpathColorMode, string> = {
  type: 'Segment Type',
  speed: 'Feed Speed',
  layer_time: 'Layer Time',
  deposition: 'Deposition Rate',
  reachability: 'Reachability',
  layer: 'Layer Number',
  z_height: 'Z Height',
};

/** Unit suffix for gradient legend. */
export const COLOR_MODE_UNITS: Record<ToolpathColorMode, string> = {
  type: '',
  speed: 'mm/s',
  layer_time: 's',
  deposition: 'mm³/s',
  reachability: '',
  layer: '',
  z_height: 'mm',
};
