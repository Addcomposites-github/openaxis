/**
 * InfillPatternPreview — 2D canvas preview of infill patterns.
 *
 * Renders a simplified visual preview of the selected infill pattern
 * in a small canvas element, showing the fill pattern within a square boundary.
 */

import { useEffect, useRef } from 'react';

interface InfillPatternPreviewProps {
  pattern: string;
  size?: number;
  lineColor?: string;
  bgColor?: string;
}

export default function InfillPatternPreview({
  pattern,
  size = 64,
  lineColor = '#3b82f6',
  bgColor = '#f9fafb',
}: InfillPatternPreviewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const s = size;
    const pad = 4;
    const inner = s - pad * 2;

    // Clear
    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, s, s);

    // Draw boundary
    ctx.strokeStyle = '#d1d5db';
    ctx.lineWidth = 1;
    ctx.strokeRect(pad, pad, inner, inner);

    // Draw pattern
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 0.8;
    ctx.beginPath();

    const spacing = inner / 6;

    switch (pattern) {
      case 'grid': {
        for (let i = 1; i < 6; i++) {
          const y = pad + i * spacing;
          ctx.moveTo(pad, y);
          ctx.lineTo(pad + inner, y);
        }
        for (let i = 1; i < 6; i++) {
          const x = pad + i * spacing;
          ctx.moveTo(x, pad);
          ctx.lineTo(x, pad + inner);
        }
        break;
      }

      case 'triangles': {
        for (let i = 0; i < 8; i++) {
          const y = pad + i * spacing;
          ctx.moveTo(pad, y);
          ctx.lineTo(pad + inner, y);
        }
        // 60° lines
        for (let i = -6; i < 12; i++) {
          const x0 = pad + i * spacing;
          ctx.moveTo(x0, pad);
          ctx.lineTo(x0 + inner * 0.577, pad + inner);
        }
        break;
      }

      case 'triangle_grid': {
        for (let angle of [0, 60, 120]) {
          const rad = (angle * Math.PI) / 180;
          const cos = Math.cos(rad);
          const sin = Math.sin(rad);
          for (let i = -8; i < 16; i++) {
            const offset = i * spacing;
            const cx = pad + inner / 2 + offset * (-sin);
            const cy = pad + inner / 2 + offset * cos;
            ctx.moveTo(cx - inner * cos, cy - inner * sin);
            ctx.lineTo(cx + inner * cos, cy + inner * sin);
          }
        }
        break;
      }

      case 'radial': {
        const cx = pad + inner / 2;
        const cy = pad + inner / 2;
        for (let r = spacing; r < inner / 2; r += spacing) {
          ctx.moveTo(cx + r, cy);
          for (let a = 0; a <= Math.PI * 2; a += 0.1) {
            ctx.lineTo(cx + r * Math.cos(a), cy + r * Math.sin(a));
          }
        }
        break;
      }

      case 'offset': {
        for (let d = spacing / 2; d < inner / 2; d += spacing) {
          ctx.moveTo(pad + d, pad + d);
          ctx.lineTo(pad + inner - d, pad + d);
          ctx.lineTo(pad + inner - d, pad + inner - d);
          ctx.lineTo(pad + d, pad + inner - d);
          ctx.lineTo(pad + d, pad + d);
        }
        break;
      }

      case 'hexgrid': {
        const hexR = spacing / 2;
        const hexH = hexR * Math.sqrt(3);
        for (let row = 0; row < 6; row++) {
          const offsetX = row % 2 === 1 ? hexR * 1.5 : 0;
          for (let col = 0; col < 5; col++) {
            const cx = pad + offsetX + col * hexR * 3;
            const cy = pad + row * hexH / 2 + hexH / 2;
            if (cx > pad + inner || cy > pad + inner) continue;
            ctx.moveTo(cx + hexR, cy);
            for (let i = 1; i <= 6; i++) {
              const a = (Math.PI / 3) * i;
              ctx.lineTo(cx + hexR * Math.cos(a), cy + hexR * Math.sin(a));
            }
          }
        }
        break;
      }

      case 'medial': {
        // Center lines + offsets
        const cx = pad + inner / 2;
        const cy = pad + inner / 2;
        ctx.moveTo(pad, cy);
        ctx.lineTo(pad + inner, cy);
        ctx.moveTo(cx, pad);
        ctx.lineTo(cx, pad + inner);
        // Inner rectangle
        const d = spacing * 1.5;
        ctx.moveTo(pad + d, pad + d);
        ctx.lineTo(pad + inner - d, pad + d);
        ctx.lineTo(pad + inner - d, pad + inner - d);
        ctx.lineTo(pad + d, pad + inner - d);
        ctx.lineTo(pad + d, pad + d);
        break;
      }

      case 'zigzag':
      default: {
        // Connected zigzag
        let y = pad + spacing;
        let dir = 1;
        while (y < pad + inner) {
          if (dir === 1) {
            ctx.moveTo(pad, y);
            ctx.lineTo(pad + inner, y);
          } else {
            ctx.moveTo(pad + inner, y);
            ctx.lineTo(pad, y);
          }
          if (y + spacing <= pad + inner) {
            const nextY = y + spacing;
            if (dir === 1) {
              ctx.lineTo(pad + inner, nextY);
            } else {
              ctx.lineTo(pad, nextY);
            }
          }
          y += spacing;
          dir *= -1;
        }
        break;
      }
    }

    ctx.stroke();
  }, [pattern, size, lineColor, bgColor]);

  return (
    <canvas
      ref={canvasRef}
      width={size}
      height={size}
      className="rounded border border-gray-200"
    />
  );
}
