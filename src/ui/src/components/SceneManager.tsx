/**
 * SceneManager — the ONE persistent 3D scene.
 *
 * Reads from workspaceStore and renders everything in a single Canvas.
 * All rendering is in METERS (Y-up). Store values are in mm (Z-up).
 * Conversion happens at the render boundary in this component.
 */
import { useState, useRef, useEffect, useMemo, Suspense } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import {
  OrbitControls,
  Grid,
  GizmoHelper,
  GizmoViewcube,
  TransformControls,
  Line,
} from '@react-three/drei';
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { useLoader } from '@react-three/fiber';
import RobotModel from './RobotModel';
import BuildPlate from './BuildPlate';
import ToolpathRenderer from './ToolpathRenderer';
import { useWorkspaceStore, type GeometryPartData } from '../stores/workspaceStore';
import { MM_TO_M, toolpathPointToScene } from '../utils/units';
import type { Waypoint } from '../api/simulation';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function waypointAtTime(waypoints: Waypoint[], t: number): Waypoint | null {
  if (waypoints.length === 0) return null;
  if (t <= waypoints[0].time) return waypoints[0];
  for (let i = 1; i < waypoints.length; i++) {
    if (waypoints[i].time >= t) {
      const prev = waypoints[i - 1];
      const next = waypoints[i];
      const dt = next.time - prev.time;
      const frac = dt > 0 ? (t - prev.time) / dt : 0;
      return {
        position: [
          prev.position[0] + (next.position[0] - prev.position[0]) * frac,
          prev.position[1] + (next.position[1] - prev.position[1]) * frac,
          prev.position[2] + (next.position[2] - prev.position[2]) * frac,
        ],
        time: t,
        segmentType: next.segmentType,
        layer: next.layer,
      };
    }
  }
  return waypoints[waypoints.length - 1];
}

// ─── Geometry Sub-components (hooks never called conditionally) ──────────────

/** Renders an STL geometry part. useLoader is always called. */
function STLMesh({ url, part }: { url: string; part: GeometryPartData }) {
  const geometry = useLoader(STLLoader, url);

  return (
    <MeshWithGeometry geometry={geometry} part={part} />
  );
}

/** Renders an OBJ geometry part. useLoader is always called. */
function OBJMesh({ url, part }: { url: string; part: GeometryPartData }) {
  const obj = useLoader(OBJLoader, url);
  const geometry = useMemo(() => {
    let geo: THREE.BufferGeometry | undefined;
    obj.traverse((child: any) => {
      if (child instanceof THREE.Mesh && !geo) {
        geo = child.geometry;
      }
    });
    return geo;
  }, [obj]);

  if (!geometry) return <FallbackBoxMesh part={part} />;
  return <MeshWithGeometry geometry={geometry} part={part} />;
}

/** Renders a loaded BufferGeometry with proper materials. */
function MeshWithGeometry({ geometry, part }: { geometry: THREE.BufferGeometry; part: GeometryPartData }) {
  return (
    <>
      <mesh
        visible={part.visible}
        geometry={geometry}
        castShadow
        receiveShadow
      >
        <meshStandardMaterial
          color={part.boundsValid === false ? '#ef4444' : part.color}
          emissive={part.boundsValid === false ? '#ef4444' : '#000000'}
          emissiveIntensity={part.boundsValid === false ? 0.3 : 0}
        />
      </mesh>
      {part.boundsValid === false && (
        <lineSegments>
          <edgesGeometry args={[geometry]} />
          <lineBasicMaterial color="#ef4444" linewidth={2} />
        </lineSegments>
      )}
    </>
  );
}

/** Fallback box mesh when no file is available. Dimensions in mm, rendered in meters. */
function FallbackBoxMesh({ part }: { part: GeometryPartData }) {
  const dims = part.dimensions || { x: 100, y: 100, z: 100 };
  return (
    <mesh visible={part.visible}>
      <boxGeometry args={[dims.x * MM_TO_M, dims.y * MM_TO_M, dims.z * MM_TO_M]} />
      <meshStandardMaterial color={part.color} />
    </mesh>
  );
}

/** Routes to the correct mesh sub-component. No hooks called conditionally. */
function GeometryMesh({ part }: { part: GeometryPartData }) {
  if (part.fileUrl && part.fileType === 'stl') {
    return (
      <Suspense fallback={<FallbackBoxMesh part={part} />}>
        <STLMesh url={part.fileUrl} part={part} />
      </Suspense>
    );
  }
  if (part.fileUrl && part.fileType === 'obj') {
    return (
      <Suspense fallback={<FallbackBoxMesh part={part} />}>
        <OBJMesh url={part.fileUrl} part={part} />
      </Suspense>
    );
  }
  return <FallbackBoxMesh part={part} />;
}

/** Auto-frames camera to fit all parts when a new part is added. Dimensions in meters. */
function CameraFramer({ parts }: { parts: GeometryPartData[] }) {
  const { camera, controls } = useThree();
  const prevPartCount = useRef(0);

  useEffect(() => {
    if (parts.length > prevPartCount.current && parts.length > 0) {
      const box = new THREE.Box3();
      let hasPos = false;

      for (const part of parts) {
        if (part.visible && part.position) {
          // Convert part position and dimensions from mm to meters
          const p = new THREE.Vector3(
            part.position.x * MM_TO_M,
            part.position.y * MM_TO_M,
            part.position.z * MM_TO_M
          );
          const dim = part.dimensions || { x: 100, y: 100, z: 100 };
          const halfSize = new THREE.Vector3(
            dim.x * MM_TO_M / 2,
            dim.y * MM_TO_M / 2,
            dim.z * MM_TO_M / 2
          );
          box.expandByPoint(p.clone().sub(halfSize));
          box.expandByPoint(p.clone().add(halfSize));
          hasPos = true;
        }
      }

      if (hasPos) {
        const center = new THREE.Vector3();
        const size = new THREE.Vector3();
        box.getCenter(center);
        box.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z);
        const dist = Math.max(maxDim * 2.5, 2); // At least 2m out

        camera.position.set(center.x + dist * 0.7, center.y + dist * 0.5, center.z + dist * 0.7);
        if (controls && (controls as any).target) {
          (controls as any).target.copy(center);
          (controls as any).update();
        }
      }
    }
    prevPartCount.current = parts.length;
  }, [parts, camera, controls]);

  return null;
}

/** Toolpath trail that builds up over time during simulation. Uses shared conversion. */
function ToolpathTrail({ waypoints, currentTime }: { waypoints: Waypoint[]; currentTime: number }) {
  const points = useMemo(() => {
    const visible = waypoints.filter((w) => w.time <= currentTime);
    if (visible.length < 2) return null;
    return visible.map(
      (w) => toolpathPointToScene(w.position as [number, number, number])
    );
  }, [waypoints, currentTime]);

  if (!points) return null;

  return <Line points={points} color="#22c55e" lineWidth={2} />;
}

/** Emits [SCENE_CHECK] console info periodically for closed-loop verification. */
function SceneCheckLogger() {
  const geometryParts = useWorkspaceStore((s) => s.geometryParts);
  const r3fState = useThree();
  const { camera, scene } = r3fState;
  const lastLog = useRef(0);

  // Expose scene, camera, and R3F state globally for debugging
  useEffect(() => {
    (window as any).__r3fScene = scene;
    (window as any).__r3fCamera = camera;
    (window as any).__r3fState = r3fState;
    (window as any).__r3fInvalidate = r3fState.invalidate;
    console.log('[SceneCheckLogger] R3F state exposed. frameloop:', r3fState.frameloop);
    return () => {
      delete (window as any).__r3fScene;
      delete (window as any).__r3fCamera;
      delete (window as any).__r3fState;
      delete (window as any).__r3fInvalidate;
    };
  }, [scene, camera, r3fState]);

  useFrame(() => {
    const now = Date.now();
    if (now - lastLog.current < 5000) return; // Log every 5 seconds max
    lastLog.current = now;

    // Compute geometry bounds in meters
    let geoMin = [Infinity, Infinity, Infinity];
    let geoMax = [-Infinity, -Infinity, -Infinity];
    for (const part of geometryParts) {
      if (part.visible && part.position && part.dimensions) {
        const px = (part.position.x || 0) * MM_TO_M;
        const py = (part.position.y || 0) * MM_TO_M;
        const pz = (part.position.z || 0) * MM_TO_M;
        const dx = (part.dimensions.x || 0) * MM_TO_M / 2;
        const dy = (part.dimensions.y || 0) * MM_TO_M / 2;
        const dz = (part.dimensions.z || 0) * MM_TO_M / 2;
        geoMin = [Math.min(geoMin[0], px - dx), Math.min(geoMin[1], py - dy), Math.min(geoMin[2], pz - dz)];
        geoMax = [Math.max(geoMax[0], px + dx), Math.max(geoMax[1], py + dy), Math.max(geoMax[2], pz + dz)];
      }
    }

    console.info('[SCENE_CHECK]', {
      buildPlateBounds: { min: [-0.5, 0, -0.5], max: [0.5, 1, 0.5] }, // 1m plate in meters
      geometryBounds: geoMin[0] !== Infinity
        ? { min: geoMin, max: geoMax }
        : null,
      cameraPosition: [camera.position.x, camera.position.y, camera.position.z],
      partsCount: geometryParts.length,
      allInMeters: true,
    });
  });

  return null;
}

// ─── Main SceneManager ──────────────────────────────────────────────────────

export default function SceneManager() {
  const mode = useWorkspaceStore((s) => s.mode);
  const cellSetup = useWorkspaceStore((s) => s.cellSetup);
  const geometryParts = useWorkspaceStore((s) => s.geometryParts);
  const selectedPartId = useWorkspaceStore((s) => s.selectedPartId);
  const transformMode = useWorkspaceStore((s) => s.transformMode);
  const toolpathData = useWorkspaceStore((s) => s.toolpathData);
  const currentLayer = useWorkspaceStore((s) => s.currentLayer);
  const showAllLayers = useWorkspaceStore((s) => s.showAllLayers);
  const simState = useWorkspaceStore((s) => s.simState);
  const jointAngles = useWorkspaceStore((s) => s.jointAngles);
  const jointTrajectory = useWorkspaceStore((s) => s.jointTrajectory);
  const trajectory = useWorkspaceStore((s) => s.trajectory);
  const simMode = useWorkspaceStore((s) => s.simMode);
  const reachability = useWorkspaceStore((s) => s.reachability);

  const setSelectedPartId = useWorkspaceStore((s) => s.setSelectedPartId);
  const updateGeometryPart = useWorkspaceStore((s) => s.updateGeometryPart);

  // TransformControls target
  const [targetMesh, setTargetMesh] = useState<THREE.Object3D | null>(null);
  const orbitControlsRef = useRef<any>(null);

  // ── Robot rotation (degrees → radians) ──────────────────────────────────

  const robotPosition = cellSetup.robot.basePosition;
  const robotRotation: [number, number, number] = [
    (cellSetup.robot.baseRotation[0] * Math.PI) / 180,
    (cellSetup.robot.baseRotation[1] * Math.PI) / 180,
    (cellSetup.robot.baseRotation[2] * Math.PI) / 180,
  ];

  // ── Build plate origin (meters, Y-up scene space) ─────────────────────
  // Build plate sits on top of the work table.
  // Table top Y = tablePos.y + tableSize.y/2
  const buildPlateOrigin: [number, number, number] = useMemo(() => [
    cellSetup.workTablePosition[0],
    cellSetup.workTablePosition[1] + cellSetup.workTableSize[1] / 2,
    cellSetup.workTablePosition[2],
  ], [cellSetup.workTablePosition, cellSetup.workTableSize]);

  // ── Active joint angles (interpolated for simulation playback) ──────────

  const activeJointAngles = useMemo(() => {
    if (mode !== 'simulation' || simMode !== 'toolpath' || !jointTrajectory || !trajectory) {
      return jointAngles;
    }

    const waypoints = trajectory.waypoints;
    if (waypoints.length === 0 || jointTrajectory.length === 0) return jointAngles;

    const t = simState.currentTime;
    let idx = 0;
    for (let i = 1; i < waypoints.length; i++) {
      if (waypoints[i].time >= t) {
        idx = i - 1;
        break;
      }
      idx = i;
    }

    const nextIdx = Math.min(idx + 1, waypoints.length - 1);
    const prev = waypoints[idx];
    const next = waypoints[nextIdx];
    const dt = next.time - prev.time;
    const frac = dt > 0 ? Math.max(0, Math.min(1, (t - prev.time) / dt)) : 0;

    const prevJoints = jointTrajectory[Math.min(idx, jointTrajectory.length - 1)] || [];
    const nextJoints = jointTrajectory[Math.min(nextIdx, jointTrajectory.length - 1)] || [];

    const jointNames = ['joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5', 'joint_6'];
    const result: Record<string, number> = {};
    for (let j = 0; j < jointNames.length; j++) {
      const pv = prevJoints[j] ?? 0;
      const nv = nextJoints[j] ?? 0;
      result[jointNames[j]] = pv + (nv - pv) * frac;
    }
    return result;
  }, [mode, simMode, jointTrajectory, trajectory, simState.currentTime, jointAngles]);

  // ── Simulation waypoints ────────────────────────────────────────────────

  const waypoints = trajectory?.waypoints || [];
  const currentWp = mode === 'simulation' && simMode === 'toolpath'
    ? waypointAtTime(waypoints, simState.currentTime)
    : null;
  const tcpPos: [number, number, number] | null = currentWp
    ? toolpathPointToScene(currentWp.position as [number, number, number])
    : null;

  // ── Robot joint angles for current mode ─────────────────────────────────

  const robotJointAngles = mode === 'simulation'
    ? activeJointAngles
    : mode === 'setup'
      ? { joint_1: 0, joint_2: -0.5, joint_3: 1.57, joint_4: 0, joint_5: 0.5, joint_6: 0 }
      : {}; // geometry/toolpath mode: default pose

  // ── Geometry visibility by mode ─────────────────────────────────────────

  const showGeometry = mode === 'geometry' || mode === 'toolpath' || mode === 'simulation';
  const showToolpath = mode === 'toolpath' || mode === 'simulation';

  const showTransformControls = mode === 'geometry' && selectedPartId !== null;
  const showSimTrail = mode === 'simulation' && simMode === 'toolpath' && waypoints.length > 0;

  return (
    <>
      {/* SCENE_CHECK logger for closed-loop verification */}
      <SceneCheckLogger />

      {/* Lighting — always present */}
      <ambientLight intensity={0.6} />
      <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
      <directionalLight position={[-10, -10, -5]} intensity={0.3} />
      <spotLight position={[0, 10, 0]} angle={0.3} penumbra={1} intensity={0.5} castShadow />

      {/* Grid — always present, in meters */}
      <Grid
        args={[20, 20]}
        cellSize={1}
        cellThickness={0.5}
        cellColor="#6b7280"
        sectionSize={5}
        sectionThickness={1}
        sectionColor="#374151"
        fadeDistance={30}
        fadeStrength={1}
        followCamera={false}
        infiniteGrid
      />

      {/* Floor Plane — 50m x 50m */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.001, 0]} receiveShadow>
        <planeGeometry args={[50, 50]} />
        <meshStandardMaterial color="#1e293b" />
      </mesh>

      {/* Work Table — cellSetup values are in meters already */}
      <mesh position={cellSetup.workTablePosition} receiveShadow>
        <boxGeometry args={cellSetup.workTableSize} />
        <meshStandardMaterial color="#475569" metalness={0.5} roughness={0.5} />
      </mesh>

      {/* Build Plate — on top of the work table, in the robot's working area */}
      <group position={buildPlateOrigin}>
        <BuildPlate size={{ x: 1000, y: 1000 }} maxHeight={1000} visible={true} />
      </group>

      {/* Robot Base Platform */}
      <mesh position={[robotPosition[0], 0.05, robotPosition[2]]}>
        <cylinderGeometry args={[0.3, 0.35, 0.1, 32]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.6} roughness={0.4} />
      </mesh>

      {/* Robot — always present (URDF is in meters natively) */}
      <RobotModel
        position={robotPosition}
        rotation={robotRotation}
        urdfPath="/config/urdf/abb_irb6700.urdf"
        meshPath="/config/"
        jointAngles={robotJointAngles}
      />

      {/* External Axis Visualization */}
      {cellSetup.externalAxis.enabled && cellSetup.externalAxis.type === 'turntable' && (
        <group position={cellSetup.externalAxis.position}>
          <mesh position={[0, 0.1, 0]}>
            <cylinderGeometry args={[0.8, 0.9, 0.2, 32]} />
            <meshStandardMaterial color="#334155" metalness={0.7} roughness={0.3} />
          </mesh>
          <mesh position={[0, 0.25, 0]}>
            <cylinderGeometry args={[0.75, 0.75, 0.1, 32]} />
            <meshStandardMaterial color="#64748b" metalness={0.6} roughness={0.4} />
          </mesh>
        </group>
      )}

      {cellSetup.externalAxis.enabled && cellSetup.externalAxis.type === 'positioner_2axis' && (
        <group position={cellSetup.externalAxis.position}>
          <mesh position={[0, 0.3, 0]}>
            <boxGeometry args={[0.4, 0.6, 0.4]} />
            <meshStandardMaterial color="#334155" metalness={0.7} roughness={0.3} />
          </mesh>
          <mesh position={[0, 0.7, 0.3]} rotation={[-0.5, 0, 0]}>
            <boxGeometry args={[0.3, 0.8, 0.15]} />
            <meshStandardMaterial color="#475569" metalness={0.6} roughness={0.4} />
          </mesh>
        </group>
      )}

      {/* ── Build-plate-relative content ──────────────────────────────────
          Everything that lives "on the build plate" is wrapped in this group.
          Part positions (mm, Y-up) are relative to the plate origin.
          The group places them in world space at the build plate location. */}
      <group position={buildPlateOrigin}>
        {/* Geometry Parts — visible in geometry/toolpath/simulation */}
        {showGeometry &&
          geometryParts.map((part) => (
            <group
              key={part.id}
              onClick={(e) => {
                if (mode === 'geometry') {
                  e.stopPropagation();
                  setSelectedPartId(part.id);
                }
              }}
              onPointerOver={(e) => {
                if (mode === 'geometry') {
                  e.stopPropagation();
                  document.body.style.cursor = 'pointer';
                }
              }}
              onPointerOut={(e) => {
                if (mode === 'geometry') {
                  e.stopPropagation();
                  document.body.style.cursor = 'default';
                }
              }}
            >
              <mesh
                ref={(ref) => {
                  if (part.id === selectedPartId && ref) {
                    setTargetMesh(ref);
                  }
                }}
                position={[
                  (part.position?.x || 0) * MM_TO_M,
                  (part.position?.y || 0) * MM_TO_M,
                  (part.position?.z || 0) * MM_TO_M,
                ]}
                rotation={[
                  part.rotation?.x || 0,
                  part.rotation?.y || 0,
                  part.rotation?.z || 0,
                ]}
                scale={[
                  (part.scale?.x || 1) * MM_TO_M,
                  (part.scale?.y || 1) * MM_TO_M,
                  (part.scale?.z || 1) * MM_TO_M,
                ]}
              >
                {/* GeometryMesh renders at native mm scale; parent scales to meters */}
                <GeometryMesh part={{ ...part, position: { x: 0, y: 0, z: 0 } }} />
              </mesh>
            </group>
          ))}

        {/* Transform Controls — only in geometry mode when part selected.
            TransformControls reports LOCAL position (relative to parent group =
            build plate), so we can read it directly without offset subtraction. */}
        {showTransformControls && targetMesh && (
          <TransformControls
            object={targetMesh}
            mode={transformMode}
            onMouseDown={() => {
              if (orbitControlsRef.current) {
                orbitControlsRef.current.enabled = false;
              }
            }}
            onMouseUp={() => {
              if (orbitControlsRef.current) {
                orbitControlsRef.current.enabled = true;
              }
              if (targetMesh && selectedPartId) {
                // Position is local to the build-plate group (meters → mm)
                updateGeometryPart(selectedPartId, {
                  position: {
                    x: targetMesh.position.x / MM_TO_M,
                    y: targetMesh.position.y / MM_TO_M,
                    z: targetMesh.position.z / MM_TO_M,
                  },
                  rotation: {
                    x: targetMesh.rotation.x,
                    y: targetMesh.rotation.y,
                    z: targetMesh.rotation.z,
                  },
                  scale: {
                    x: targetMesh.scale.x / MM_TO_M,
                    y: targetMesh.scale.y / MM_TO_M,
                    z: targetMesh.scale.z / MM_TO_M,
                  },
                });
              }
            }}
          />
        )}

        {/* Toolpath Visualization — visible in toolpath & simulation */}
        {showToolpath && toolpathData?.segments?.length > 0 && (
          <ToolpathRenderer
            segments={toolpathData.segments}
            currentLayer={currentLayer}
            showAllLayers={showAllLayers}
            colorByType={true}
            reachability={reachability}
          />
        )}

        {/* Simulation Trail */}
        {showSimTrail && (
          <ToolpathTrail waypoints={waypoints} currentTime={simState.currentTime} />
        )}

        {/* TCP target indicator during simulation */}
        {mode === 'simulation' && tcpPos && (
          <mesh position={tcpPos}>
            <sphereGeometry args={[0.03, 16, 16]} />
            <meshStandardMaterial color="#22c55e" emissive="#22c55e" emissiveIntensity={0.5} />
          </mesh>
        )}
      </group>

      {/* Camera auto-framing in geometry mode */}
      {mode === 'geometry' && <CameraFramer parts={geometryParts} />}

      {/* Orbit Controls */}
      <OrbitControls ref={orbitControlsRef} makeDefault />

      {/* Gizmo */}
      <GizmoHelper alignment="bottom-right" margin={[80, 80]}>
        <GizmoViewcube />
      </GizmoHelper>
    </>
  );
}
