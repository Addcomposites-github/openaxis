/**
 * SlicingStrategySelector — Strategy cards with visual previews.
 *
 * Lets the user choose from 5 slicing strategies:
 * - Planar (default horizontal slicing)
 * - Angled (tilted slice planes)
 * - Radial (concentric cylindrical paths)
 * - Curve-following (layers follow a guide curve)
 * - Revolved (helical paths for rotational parts)
 */

import { useRef, useEffect } from 'react';

export type SlicingStrategy = 'planar' | 'angled' | 'radial' | 'curve' | 'revolved';

interface SlicingStrategySelectorProps {
  strategy: SlicingStrategy;
  onChange: (strategy: SlicingStrategy) => void;
  angleParam?: number;
  onAngleChange?: (angle: number) => void;
}

const STRATEGIES: {
  value: SlicingStrategy;
  label: string;
  desc: string;
  available: boolean;
}[] = [
  { value: 'planar', label: 'Planar', desc: 'Horizontal layer-by-layer slicing (ORNL Slicer 2)', available: true },
  { value: 'angled', label: 'Angled', desc: 'Coming soon \u2014 requires compas_slicer integration', available: false },
  { value: 'radial', label: 'Radial', desc: 'Coming soon \u2014 requires compas_slicer integration', available: false },
  { value: 'curve', label: 'Curve', desc: 'Coming soon \u2014 requires compas_slicer integration', available: false },
  { value: 'revolved', label: 'Revolved', desc: 'Coming soon \u2014 requires compas_slicer integration', available: false },
];

// ─── Strategy Preview Canvas ─────────────────────────────────────────────────

function StrategyPreview({
  strategy,
  size = 48,
  active = false,
}: {
  strategy: SlicingStrategy;
  size?: number;
  active?: boolean;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, size, size);

    const color = active ? '#3b82f6' : '#9ca3af';
    const cx = size / 2;
    const cy = size / 2;
    const r = size * 0.35;

    ctx.strokeStyle = color;
    ctx.lineWidth = 1.2;
    ctx.lineCap = 'round';

    switch (strategy) {
      case 'planar': {
        // Horizontal lines through a box outline
        ctx.strokeStyle = color + '40';
        ctx.strokeRect(cx - r, cy - r, r * 2, r * 2);
        ctx.strokeStyle = color;
        for (let i = 0; i < 5; i++) {
          const y = cy - r + (r * 2 * (i + 0.5)) / 5;
          ctx.beginPath();
          ctx.moveTo(cx - r + 2, y);
          ctx.lineTo(cx + r - 2, y);
          ctx.stroke();
        }
        break;
      }
      case 'angled': {
        // Tilted lines through a box
        ctx.strokeStyle = color + '40';
        ctx.strokeRect(cx - r, cy - r, r * 2, r * 2);
        ctx.strokeStyle = color;
        const angle = Math.PI / 6; // 30 degrees
        for (let i = 0; i < 5; i++) {
          const offset = -r + (r * 2 * (i + 0.5)) / 5;
          const dx = r * Math.cos(angle);
          const dy = r * Math.sin(angle);
          ctx.beginPath();
          ctx.moveTo(cx - dx, cy + offset - dy * 0.3);
          ctx.lineTo(cx + dx, cy + offset + dy * 0.3);
          ctx.stroke();
        }
        break;
      }
      case 'radial': {
        // Concentric circles
        for (let i = 1; i <= 4; i++) {
          const cr = r * (i / 4);
          ctx.beginPath();
          ctx.arc(cx, cy, cr, 0, Math.PI * 2);
          ctx.stroke();
        }
        break;
      }
      case 'curve': {
        // Wavy layers following a curve
        ctx.strokeStyle = color + '40';
        ctx.beginPath();
        ctx.moveTo(cx - r, cy + r * 0.3);
        ctx.quadraticCurveTo(cx, cy - r * 0.5, cx + r, cy + r * 0.3);
        ctx.stroke();
        ctx.strokeStyle = color;
        for (let i = 0; i < 4; i++) {
          const off = -r * 0.3 + (r * 0.6 * (i + 0.5)) / 4;
          ctx.beginPath();
          ctx.moveTo(cx - r + 4, cy + off + r * 0.15);
          ctx.quadraticCurveTo(cx, cy + off - r * 0.25, cx + r - 4, cy + off + r * 0.15);
          ctx.stroke();
        }
        break;
      }
      case 'revolved': {
        // Spiral / helix
        ctx.beginPath();
        for (let t = 0; t < Math.PI * 4; t += 0.1) {
          const sr = r * 0.3 + (t / (Math.PI * 4)) * r * 0.5;
          const x = cx + sr * Math.cos(t);
          const y = cy + sr * Math.sin(t);
          if (t === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
        break;
      }
    }
  }, [strategy, size, active]);

  return (
    <canvas
      ref={canvasRef}
      width={size}
      height={size}
      style={{ width: size, height: size }}
    />
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export default function SlicingStrategySelector({
  strategy,
  onChange,
  angleParam,
  onAngleChange,
}: SlicingStrategySelectorProps) {
  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
        Slicing Strategy
      </h3>

      <div className="grid grid-cols-5 gap-1.5">
        {STRATEGIES.map((s) => (
          <button
            key={s.value}
            onClick={() => s.available && onChange(s.value)}
            disabled={!s.available}
            className={`flex flex-col items-center gap-1 p-2 rounded-lg border-2 transition-colors ${
              !s.available
                ? 'border-gray-100 bg-gray-50 opacity-50 cursor-not-allowed'
                : strategy === s.value
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
            }`}
            title={s.desc}
          >
            <StrategyPreview
              strategy={s.value}
              size={40}
              active={strategy === s.value && s.available}
            />
            <span className={`text-xs leading-tight text-center font-medium ${s.available ? 'text-gray-700' : 'text-gray-400'}`}>
              {s.label}
            </span>
          </button>
        ))}
      </div>

      {/* Angled strategy: show angle input */}
      {strategy === 'angled' && onAngleChange && (
        <div className="flex items-center gap-2 mt-2">
          <label className="text-xs text-gray-600">Slice Angle:</label>
          <input
            type="number"
            step="5"
            min="0"
            max="90"
            value={angleParam ?? 30}
            onChange={(e) => onAngleChange(parseFloat(e.target.value) || 0)}
            className="w-20 px-2 py-1 text-xs border border-gray-300 rounded font-mono"
          />
          <span className="text-xs text-gray-400">degrees</span>
        </div>
      )}

      {/* Strategy description */}
      <p className="text-xs text-gray-500">
        {STRATEGIES.find((s) => s.value === strategy)?.desc}
      </p>
    </div>
  );
}
