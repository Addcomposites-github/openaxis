/**
 * DepositionVisualization — Growing-part visualization during simulation.
 *
 * Uses THREE.InstancedMesh to efficiently render deposited material beads
 * as small boxes, progressively appearing as the simulation advances.
 *
 * Performance: renders up to 50K instances using instanced rendering.
 * Beyond 50K points, we subsample to keep frame rate smooth.
 */
import { useRef, useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { toolpathPointToScene } from '../utils/units';
import type { Waypoint } from '../api/simulation';

const MAX_INSTANCES = 50000;
const BEAD_SIZE_X = 0.0025; // 2.5mm in meters
const BEAD_SIZE_Y = 0.002;  // 2mm height
const BEAD_SIZE_Z = 0.0025; // 2.5mm depth

// Pre-create shared geometry and material
const beadGeometry = new THREE.BoxGeometry(BEAD_SIZE_X, BEAD_SIZE_Y, BEAD_SIZE_Z);

// Color palette for different segment types
const COLOR_PERIMETER = new THREE.Color('#ef4444'); // red
const COLOR_INFILL = new THREE.Color('#f59e0b');    // amber
const COLOR_DEFAULT = new THREE.Color('#6366f1');    // indigo

function getBeadColor(segmentType?: string): THREE.Color {
  if (!segmentType) return COLOR_DEFAULT;
  const t = segmentType.toLowerCase();
  if (t.includes('perim') || t.includes('wall')) return COLOR_PERIMETER;
  if (t.includes('infill') || t.includes('fill')) return COLOR_INFILL;
  return COLOR_DEFAULT;
}

interface DepositionVisualizationProps {
  /** Waypoints from the trajectory */
  waypoints: Waypoint[];
  /** Current simulation time */
  currentTime: number;
  /** Whether visualization is visible */
  visible: boolean;
}

export default function DepositionVisualization({
  waypoints,
  currentTime,
  visible,
}: DepositionVisualizationProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const prevCountRef = useRef(0);

  // Subsample waypoints if too many (only non-travel waypoints get beads)
  const printWaypoints = useMemo(() => {
    const prints = waypoints.filter(
      (w) => w.segmentType !== 'travel' && w.segmentType !== 'rapid'
    );
    if (prints.length <= MAX_INSTANCES) return prints;

    // Subsample uniformly
    const step = prints.length / MAX_INSTANCES;
    const sampled: Waypoint[] = [];
    for (let i = 0; i < MAX_INSTANCES; i++) {
      sampled.push(prints[Math.floor(i * step)]);
    }
    return sampled;
  }, [waypoints]);

  // Pre-compute transforms and colors
  const { matrices, colors } = useMemo(() => {
    const mats: THREE.Matrix4[] = [];
    const cols: THREE.Color[] = [];
    const dummy = new THREE.Object3D();

    for (const wp of printWaypoints) {
      const pos = toolpathPointToScene(wp.position as [number, number, number]);
      dummy.position.set(pos[0], pos[1], pos[2]);
      dummy.updateMatrix();
      mats.push(dummy.matrix.clone());
      cols.push(getBeadColor(wp.segmentType));
    }

    return { matrices: mats, colors: cols };
  }, [printWaypoints]);

  // Update instance count based on current time
  useFrame(() => {
    const mesh = meshRef.current;
    if (!mesh || !visible) return;

    // Binary search for the last waypoint <= currentTime
    let lo = 0;
    let hi = printWaypoints.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (printWaypoints[mid].time <= currentTime) {
        lo = mid;
      } else {
        hi = mid - 1;
      }
    }
    const activeCount = printWaypoints.length > 0 && printWaypoints[lo].time <= currentTime
      ? lo + 1
      : 0;

    // Only update if count changed
    if (activeCount !== prevCountRef.current) {
      // Set new instances
      for (let i = prevCountRef.current; i < activeCount; i++) {
        mesh.setMatrixAt(i, matrices[i]);
        mesh.setColorAt(i, colors[i]);
      }

      mesh.count = activeCount;
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;

      prevCountRef.current = activeCount;
    }
  });

  // Reset on waypoints change
  useEffect(() => {
    prevCountRef.current = 0;
    const mesh = meshRef.current;
    if (mesh) {
      mesh.count = 0;
    }
  }, [printWaypoints]);

  if (!visible || printWaypoints.length === 0) return null;

  return (
    <instancedMesh
      ref={meshRef}
      args={[beadGeometry, undefined, printWaypoints.length]}
      frustumCulled={false}
    >
      <meshStandardMaterial
        vertexColors
        metalness={0.3}
        roughness={0.7}
      />
    </instancedMesh>
  );
}
