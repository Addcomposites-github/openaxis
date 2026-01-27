import React, { useMemo } from 'react';
import * as THREE from 'three';

export interface ToolpathSegment {
  type: string;  // PERIMETER, INFILL, TRAVEL, etc.
  layer: number;
  points: [number, number, number][];
  speed: number;
  extrusionRate: number;
}

interface ToolpathRendererProps {
  segments: ToolpathSegment[];
  currentLayer?: number;  // If set, only show this layer
  showAllLayers?: boolean;  // Show all layers at once
  colorByType?: boolean;  // Color code by segment type
}

const SEGMENT_COLORS: Record<string, string> = {
  PERIMETER: '#3b82f6',  // Blue
  INFILL: '#f59e0b',     // Orange
  TRAVEL: '#6b7280',     // Gray
  SUPPORT: '#10b981',    // Green
  MACHINING: '#8b5cf6',  // Purple
};

const DEFAULT_COLOR = '#3b82f6';

export default function ToolpathRenderer({
  segments,
  currentLayer,
  showAllLayers = false,
  colorByType = true
}: ToolpathRendererProps) {
  // Filter segments based on layer visibility
  const visibleSegments = useMemo(() => {
    if (showAllLayers) {
      return segments;
    }
    if (currentLayer !== undefined) {
      return segments.filter(seg => seg.layer === currentLayer);
    }
    return segments;
  }, [segments, currentLayer, showAllLayers]);

  // Group segments by type for efficient rendering
  const segmentsByType = useMemo(() => {
    const groups: Record<string, ToolpathSegment[]> = {};

    visibleSegments.forEach(segment => {
      const type = segment.type.toUpperCase();
      if (!groups[type]) {
        groups[type] = [];
      }
      groups[type].push(segment);
    });

    return groups;
  }, [visibleSegments]);

  return (
    <group>
      {Object.entries(segmentsByType).map(([type, segs]) => {
        const color = colorByType ? (SEGMENT_COLORS[type] || DEFAULT_COLOR) : DEFAULT_COLOR;

        return segs.map((segment, idx) => (
          <ToolpathLine
            key={`${type}-${segment.layer}-${idx}`}
            points={segment.points}
            color={color}
            lineWidth={segment.type === 'TRAVEL' ? 1 : 2}
            opacity={segment.type === 'TRAVEL' ? 0.3 : 1.0}
          />
        ));
      })}
    </group>
  );
}

interface ToolpathLineProps {
  points: [number, number, number][];
  color: string;
  lineWidth?: number;
  opacity?: number;
}

function ToolpathLine({ points, color, lineWidth = 2, opacity = 1.0 }: ToolpathLineProps) {
  const geometry = useMemo(() => {
    const vectors = points.map(p => new THREE.Vector3(p[0], p[1], p[2]));
    const geom = new THREE.BufferGeometry().setFromPoints(vectors);
    return geom;
  }, [points]);

  return (
    <line geometry={geometry}>
      <lineBasicMaterial
        color={color}
        linewidth={lineWidth}
        transparent={opacity < 1.0}
        opacity={opacity}
      />
    </line>
  );
}

/**
 * Alternative: Use Line from drei for better quality
 */
export function ToolpathRendererDrei({
  segments,
  currentLayer,
  showAllLayers = false,
  colorByType = true
}: ToolpathRendererProps) {
  const visibleSegments = useMemo(() => {
    if (showAllLayers) {
      return segments;
    }
    if (currentLayer !== undefined) {
      return segments.filter(seg => seg.layer === currentLayer);
    }
    return segments;
  }, [segments, currentLayer, showAllLayers]);

  return (
    <group>
      {visibleSegments.map((segment, idx) => {
        const type = segment.type.toUpperCase();
        const color = colorByType ? (SEGMENT_COLORS[type] || DEFAULT_COLOR) : DEFAULT_COLOR;
        const vectors = segment.points.map(p => new THREE.Vector3(p[0], p[1], p[2]));

        return (
          <line key={`${segment.layer}-${idx}`}>
            <bufferGeometry>
              <bufferAttribute
                attach="attributes-position"
                count={vectors.length}
                array={new Float32Array(vectors.flatMap(v => [v.x, v.y, v.z]))}
                itemSize={3}
              />
            </bufferGeometry>
            <lineBasicMaterial
              color={color}
              linewidth={segment.type === 'TRAVEL' ? 1 : 2}
              transparent={segment.type === 'TRAVEL'}
              opacity={segment.type === 'TRAVEL' ? 0.3 : 1.0}
            />
          </line>
        );
      })}
    </group>
  );
}
