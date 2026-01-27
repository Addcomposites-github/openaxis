import React from 'react';
import { Grid, Html } from '@react-three/drei';
import * as THREE from 'three';

interface BuildPlateProps {
  size?: { x: number; y: number };  // in mm
  maxHeight?: number;  // maximum build height in mm
  visible?: boolean;
}

export default function BuildPlate({
  size = { x: 1000, y: 1000 },
  maxHeight = 1000,
  visible = true
}: BuildPlateProps) {
  if (!visible) return null;

  return (
    <group>
      {/* Main build plate surface */}
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, 0, 0]}
        receiveShadow
      >
        <planeGeometry args={[size.x, size.y]} />
        <meshStandardMaterial
          color="#2d3748"
          metalness={0.3}
          roughness={0.7}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Grid overlay */}
      <Grid
        args={[size.x, size.y]}
        position={[0, 0.1, 0]}  // Slightly above plate to avoid z-fighting
        cellSize={100}  // Major grid every 100mm
        cellThickness={1}
        cellColor="#4a5568"
        sectionSize={500}  // Extra thick lines every 500mm
        sectionThickness={2}
        sectionColor="#718096"
        fadeDistance={2000}
        fadeStrength={1}
        followCamera={false}
      />

      {/* Coordinate axes */}
      <axesHelper args={[150]} position={[0, 0.2, 0]} />

      {/* Origin marker (red sphere at 0,0,0) */}
      <mesh position={[0, 1, 0]}>
        <sphereGeometry args={[5, 16, 16]} />
        <meshStandardMaterial
          color="#ef4444"
          emissive="#ef4444"
          emissiveIntensity={0.5}
        />
      </mesh>

      {/* Build volume box (wireframe showing max printable space) */}
      <mesh position={[0, maxHeight / 2, 0]}>
        <boxGeometry args={[size.x, maxHeight, size.y]} />
        <meshBasicMaterial
          color="#3b82f6"
          wireframe
          transparent
          opacity={0.15}
        />
      </mesh>

      {/* Corner dimension labels */}
      <DimensionLabels size={size} maxHeight={maxHeight} />
    </group>
  );
}

function DimensionLabels({
  size,
  maxHeight
}: {
  size: { x: number; y: number };
  maxHeight: number;
}) {
  const halfX = size.x / 2;
  const halfY = size.y / 2;

  return (
    <group>
      {/* Bottom corner label */}
      <Html
        position={[-halfX + 50, 5, -halfY + 50]}
        distanceFactor={10}
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
        {size.x} × {size.y} mm<br/>
        Height: {maxHeight} mm
      </Html>

      {/* Origin label */}
      <Html
        position={[20, 5, 20]}
        distanceFactor={10}
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
