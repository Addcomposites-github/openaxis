import React from 'react';
import { Grid, Html } from '@react-three/drei';
import * as THREE from 'three';
import { MM_TO_M } from '../utils/units';

interface BuildPlateProps {
  size?: { x: number; y: number };  // in mm (store convention)
  maxHeight?: number;  // maximum build height in mm
  visible?: boolean;
}

/**
 * BuildPlate renders the build plate in the 3D scene.
 * Accepts dimensions in mm but internally converts to meters for rendering.
 */
export default function BuildPlate({
  size = { x: 1000, y: 1000 },
  maxHeight = 1000,
  visible = true
}: BuildPlateProps) {
  if (!visible) return null;

  // Convert mm to meters at the render boundary
  const sizeM = { x: size.x * MM_TO_M, y: size.y * MM_TO_M };
  const maxHeightM = maxHeight * MM_TO_M;

  return (
    <group>
      {/* Main build plate surface */}
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, 0, 0]}
        receiveShadow
      >
        <planeGeometry args={[sizeM.x, sizeM.y]} />
        <meshStandardMaterial
          color="#2d3748"
          metalness={0.3}
          roughness={0.7}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Grid overlay */}
      <Grid
        args={[sizeM.x, sizeM.y]}
        position={[0, 0.001, 0]}  // Slightly above plate to avoid z-fighting
        cellSize={0.1}            // Major grid every 100mm = 0.1m
        cellThickness={1}
        cellColor="#4a5568"
        sectionSize={0.5}         // Extra thick lines every 500mm = 0.5m
        sectionThickness={2}
        sectionColor="#718096"
        fadeDistance={5}
        fadeStrength={1}
        followCamera={false}
      />

      {/* Coordinate axes — 150mm = 0.15m */}
      <axesHelper args={[0.15]} position={[0, 0.002, 0]} />

      {/* Origin marker (red sphere at 0,0,0) */}
      <mesh position={[0, 0.005, 0]}>
        <sphereGeometry args={[0.005, 16, 16]} />
        <meshStandardMaterial
          color="#ef4444"
          emissive="#ef4444"
          emissiveIntensity={0.5}
        />
      </mesh>

      {/* Build volume box (wireframe showing max printable space) */}
      <mesh position={[0, maxHeightM / 2, 0]}>
        <boxGeometry args={[sizeM.x, maxHeightM, sizeM.y]} />
        <meshBasicMaterial
          color="#3b82f6"
          wireframe
          transparent
          opacity={0.15}
        />
      </mesh>

      {/* Corner dimension labels */}
      <DimensionLabels size={size} sizeM={sizeM} maxHeight={maxHeight} />
    </group>
  );
}

function DimensionLabels({
  size,
  sizeM,
  maxHeight
}: {
  size: { x: number; y: number };
  sizeM: { x: number; y: number };
  maxHeight: number;
}) {
  const halfX = sizeM.x / 2;
  const halfY = sizeM.y / 2;

  return (
    <group>
      {/* Bottom corner label */}
      <Html
        position={[-halfX + 0.05, 0.01, -halfY + 0.05]}
        distanceFactor={2}
        style={{
          background: 'rgba(0, 0, 0, 0.7)',
          color: 'white',
          padding: '4px 8px',
          borderRadius: '4px',
          fontSize: '12px',
          fontFamily: 'monospace',
          pointerEvents: 'none',
          userSelect: 'none'
        }}
      >
        Build Plate<br/>
        {size.x} &times; {size.y} mm<br/>
        Height: {maxHeight} mm
      </Html>

      {/* Origin label */}
      <Html
        position={[0.02, 0.01, 0.02]}
        distanceFactor={2}
        style={{
          background: 'rgba(239, 68, 68, 0.9)',
          color: 'white',
          padding: '2px 6px',
          borderRadius: '3px',
          fontSize: '10px',
          fontFamily: 'monospace',
          pointerEvents: 'none',
          userSelect: 'none'
        }}
      >
        Origin (0,0,0)
      </Html>
    </group>
  );
}
