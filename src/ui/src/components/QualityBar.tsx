/**
 * QualityBar — Horizontal segmented quality indicator bar.
 *
 * Shows green/yellow/red segments proportional to good/warning/error percentages.
 * Used in QualityPanel for per-metric quality visualization.
 */

interface QualityBarProps {
  /** Value from 0 to 100. */
  value: number;
  /** Label shown to the left. */
  label: string;
  /** Display value text (e.g., "95%", "3 violations"). */
  display?: string;
  /** Thresholds: [yellow, red] — below yellow = green, below red = yellow, else red. */
  thresholds?: [number, number];
  /** Inverted: higher is worse (e.g., violation count). */
  inverted?: boolean;
}

export default function QualityBar({
  value,
  label,
  display,
  thresholds = [80, 50],
  inverted = false,
}: QualityBarProps) {
  const pct = Math.max(0, Math.min(100, value));
  const effectiveValue = inverted ? 100 - pct : pct;

  let barColor: string;
  let textColor: string;
  if (effectiveValue >= thresholds[0]) {
    barColor = 'bg-green-500';
    textColor = 'text-green-700';
  } else if (effectiveValue >= thresholds[1]) {
    barColor = 'bg-yellow-500';
    textColor = 'text-yellow-700';
  } else {
    barColor = 'bg-red-500';
    textColor = 'text-red-700';
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-700">{label}</span>
        <span className={`text-xs font-semibold ${textColor}`}>
          {display ?? `${pct.toFixed(0)}%`}
        </span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
