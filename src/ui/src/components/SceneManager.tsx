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
import DepositionVisualization from './DepositionVisualization';
import TestHarness from './TestHarness';
import { useWorkspaceStore, type GeometryPartData } from '../stores/workspaceStore';
import { useWorkFrameStore } from '../stores/workFrameStore';
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

/**
 * Toolpath trail that builds up over time during simulation.
 * Splits waypoints into PRINT (perimeter/infill) vs TRAVEL segments
 * to avoid drawing green lines across travel jumps.
 */
function ToolpathTrail({ waypoints, currentTime }: { waypoints: Waypoint[]; currentTime: number }) {
  const { printSegments, travelSegments } = useMemo(() => {
    const visible = waypoints.filter((w) => w.time <= currentTime);
    if (visible.length < 2) return { printSegments: [] as [number, number, number][][], travelSegments: [] as [number, number, number][][] };

    // Split into contiguous runs by segment type
    const printSegs: [number, number, number][][] = [];
    const travelSegs: [number, number, number][][] = [];
    let currentPrint: [number, number, number][] = [];
    let currentTravel: [number, number, number][] = [];

    for (let i = 0; i < visible.length; i++) {
      const w = visible[i];
      const pt = toolpathPointToScene(w.position as [number, number, number]);
      const isTravel = w.segmentType === 'travel';

      if (isTravel) {
        // Flush print segment
        if (currentPrint.length >= 2) {
          printSegs.push(currentPrint);
        }
        currentPrint = [];
        // Continue travel
        currentTravel.push(pt);
      } else {
        // Flush travel segment
        if (currentTravel.length >= 2) {
          travelSegs.push(currentTravel);
        }
        currentTravel = [];
        // Continue print
        currentPrint.push(pt);
      }
    }
    // Flush remaining
    if (currentPrint.length >= 2) printSegs.push(currentPrint);
    if (currentTravel.length >= 2) travelSegs.push(currentTravel);

    return { printSegments: printSegs, travelSegments: travelSegs };
  }, [waypoints, currentTime]);

  return (
    <>
      {printSegments.map((pts, i) => (
        <Line key={`print-${i}`} points={pts} color="#22c55e" lineWidth={2} />
      ))}
      {travelSegments.map((pts, i) => (
        <Line key={`travel-${i}`} points={pts} color="#9ca3af" lineWidth={1} />
      ))}
    </>
  );
}

/**
 * Render-loop simulation timer.
 *
 * Drives simState.currentTime at the correct speed using requestAnimationFrame
 * (via useFrame), producing perfectly smooth 60fps updates.
 * Replaces the 10fps setInterval in SimulationPanel.
 */
function SimulationClock() {
  const simState = useWorkspaceStore((s) => s.simState);
  const setSimState = useWorkspaceStore((s) => s.setSimState);

  // Use refs to avoid re-creating the frame callback on every state change
  const stateRef = useRef(simState);
  stateRef.current = simState;
  const setRef = useRef(setSimState);
  setRef.current = setSimState;

  useFrame((_, delta) => {
    const s = stateRef.current;
    if (!s.isRunning || s.currentTime >= s.totalTime) return;

    // Clamp delta to avoid huge jumps when tab is backgrounded
    const dt = Math.min(delta, 0.1);
    const newTime = Math.min(s.currentTime + s.speed * dt, s.totalTime);

    // Only update if time actually changed (avoid unnecessary re-renders)
    if (Math.abs(newTime - s.currentTime) > 0.0001) {
      setRef.current({ currentTime: newTime });
    }

    // Auto-stop at end
    if (newTime >= s.totalTime) {
      setRef.current({ isRunning: false });
    }
  });

  return null;
}

/** Exposes R3F scene/camera globally for external diagnostic scripts. */
function SceneStateExposer() {
  const r3fState = useThree();
  const { camera, scene } = r3fState;

  useEffect(() => {
    (window as any).__r3fScene = scene;
    (window as any).__r3fCamera = camera;
    (window as any).__r3fState = r3fState;
    return () => {
      delete (window as any).__r3fScene;
      delete (window as any).__r3fCamera;
      delete (window as any).__r3fState;
    };
  }, [scene, camera, r3fState]);

  return null;
}

/**
 * Smoothly moves the OrbitControls target to follow the TCP position.
 * Uses LERP for smooth camera tracking instead of hard snapping.
 */
function FollowTCPCamera({ tcpPos }: { tcpPos: [number, number, number] }) {
  const { controls, camera } = useThree();
  const targetRef = useRef(new THREE.Vector3());
  const initialized = useRef(false);

  useFrame(() => {
    if (!controls || !(controls as any).target) return;

    const orbitTarget = (controls as any).target as THREE.Vector3;
    const tcp = new THREE.Vector3(tcpPos[0], tcpPos[1], tcpPos[2]);

    if (!initialized.current) {
      // First frame: snap camera close to TCP
      orbitTarget.copy(tcp);
      const offset = new THREE.Vector3(0.5, 0.3, 0.5);
      camera.position.copy(tcp).add(offset);
      (controls as any).update();
      initialized.current = true;
      targetRef.current.copy(tcp);
      return;
    }

    // Smooth follow: lerp the orbit target towards TCP
    targetRef.current.lerp(tcp, 0.1);
    orbitTarget.copy(targetRef.current);
    (controls as any).update();
  });

  // Reset when unmounted
  useEffect(() => {
    return () => {
      initialized.current = false;
    };
  }, []);

  return null;
}

// ─── Work Frame Gizmo ────────────────────────────────────────────────────────

/**
 * Renders a coordinate axes gizmo for a work frame.
 * Shows XYZ arrows at the frame origin with color coding (R=X, G=Y, B=Z).
 * Also renders a semi-transparent platform matching the frame size.
 */
function WorkFrameGizmo({ frameId, active }: { frameId: string; active: boolean }) {
  const frame = useWorkFrameStore((s) => s.frames.find((f) => f.id === frameId));
  const getScenePosition = useWorkFrameStore((s) => s.getFrameScenePosition);

  if (!frame || !frame.visible) return null;

  const scenePos = getScenePosition(frameId);
  const axisLength = 0.3; // 30cm axes
  const axisThickness = active ? 3 : 1.5;

  // Euler rotation (degrees to radians, Z-up to Y-up)
  const rx = (frame.rotation[0] * Math.PI) / 180;
  const ry = (frame.rotation[1] * Math.PI) / 180;
  const rz = (frame.rotation[2] * Math.PI) / 180;

  return (
    <group position={scenePos} rotation={[rx, rz, -ry]}>
      {/* Platform surface */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
        <planeGeometry args={[frame.size[0], frame.size[2]]} />
        <meshStandardMaterial
          color={frame.color}
          transparent
          opacity={active ? 0.15 : 0.08}
          side={2} // DoubleSide
        />
      </mesh>

      {/* Platform edge ring */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.001, 0]}>
        <ringGeometry args={[
          Math.min(frame.size[0], frame.size[2]) * 0.48,
          Math.min(frame.size[0], frame.size[2]) * 0.5,
          32,
        ]} />
        <meshBasicMaterial color={frame.color} transparent opacity={active ? 0.6 : 0.3} />
      </mesh>

      {/* X-axis (Red) */}
      <Line
        points={[[0, 0, 0], [axisLength, 0, 0]]}
        color="#ef4444"
        lineWidth={axisThickness}
      />
      <mesh position={[axisLength + 0.02, 0, 0]}>
        <sphereGeometry args={[0.015, 8, 8]} />
        <meshBasicMaterial color="#ef4444" />
      </mesh>

      {/* Y-axis (Green) — scene Y = world Z */}
      <Line
        points={[[0, 0, 0], [0, axisLength, 0]]}
        color="#22c55e"
        lineWidth={axisThickness}
      />
      <mesh position={[0, axisLength + 0.02, 0]}>
        <sphereGeometry args={[0.015, 8, 8]} />
        <meshBasicMaterial color="#22c55e" />
      </mesh>

      {/* Z-axis (Blue) — scene Z = -world Y */}
      <Line
        points={[[0, 0, 0], [0, 0, axisLength]]}
        color="#3b82f6"
        lineWidth={axisThickness}
      />
      <mesh position={[0, 0, axisLength + 0.02]}>
        <sphereGeometry args={[0.015, 8, 8]} />
        <meshBasicMaterial color="#3b82f6" />
      </mesh>

      {/* Origin marker */}
      <mesh>
        <sphereGeometry args={[active ? 0.025 : 0.018, 16, 16]} />
        <meshStandardMaterial
          color={frame.color}
          emissive={frame.color}
          emissiveIntensity={active ? 0.8 : 0.3}
        />
      </mesh>

      {/* Frame name label (using a small billboard sprite would be ideal,
          but for now a simple colored dot distinguishes frames) */}
    </group>
  );
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
  const homeJoints = useWorkspaceStore((s) => s.homeJoints);
  const homeTransitTime = useWorkspaceStore((s) => s.homeTransitTime);
  const toolpathColorMode = useWorkspaceStore((s) => s.toolpathColorMode);
  const toolpathColorRange = useWorkspaceStore((s) => s.toolpathColorRange);
  const toolpathPartId = useWorkspaceStore((s) => s.toolpathPartId);

  const setSelectedPartId = useWorkspaceStore((s) => s.setSelectedPartId);
  const updateGeometryPart = useWorkspaceStore((s) => s.updateGeometryPart);

  // Work frames
  const workFrames = useWorkFrameStore((s) => s.frames);
  const activeFrameId = useWorkFrameStore((s) => s.activeFrameId);

  // Debug: expose live state for diagnostic scripts
  useEffect(() => {
    (window as any).__simDiag = { trajectory, jointTrajectory, simState, jointAngles, reachability };
  }, [trajectory, jointTrajectory, simState, jointAngles, reachability]);

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

    const wpList = trajectory.waypoints;
    if (wpList.length === 0 || jointTrajectory.length < 2) return jointAngles;

    const t = simState.currentTime;
    const jointNames = ['joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5', 'joint_6'];

    // Helper: interpolate between two joint arrays
    const interpolateJoints = (a: number[], b: number[], frac: number): Record<string, number> => {
      const res: Record<string, number> = {};
      for (let j = 0; j < jointNames.length; j++) {
        const pv = a[j] ?? 0;
        const nv = b[j] ?? 0;
        res[jointNames[j]] = pv + (nv - pv) * frac;
      }
      return res;
    };

    // If home position padding exists, jointTrajectory = [home, ...toolpathJoints, home]
    // Timeline: [0, homeTransitTime] = home→first | [homeTransitTime, totalTime-homeTransitTime] = toolpath | [totalTime-homeTransitTime, totalTime] = last→home
    const hasHomePad = homeJoints && jointTrajectory.length === wpList.length + 2;
    const htt = hasHomePad ? homeTransitTime : 0;

    if (hasHomePad) {
      const totalTime = simState.totalTime;

      // Phase 1: Home → first waypoint
      if (t < htt) {
        const frac = htt > 0 ? Math.max(0, Math.min(1, t / htt)) : 1;
        return interpolateJoints(jointTrajectory[0], jointTrajectory[1], frac);
      }

      // Phase 3: Last waypoint → home
      if (t > totalTime - htt) {
        const lastIKIdx = jointTrajectory.length - 2;
        const homeIdx = jointTrajectory.length - 1;
        const elapsed = t - (totalTime - htt);
        const frac = htt > 0 ? Math.max(0, Math.min(1, elapsed / htt)) : 1;
        return interpolateJoints(jointTrajectory[lastIKIdx], jointTrajectory[homeIdx], frac);
      }

      // Phase 2: Toolpath playback — adjust time and use offset indices
      const adjT = t - htt;
      let idx = 0;
      for (let i = 1; i < wpList.length; i++) {
        if (wpList[i].time >= adjT) { idx = i - 1; break; }
        idx = i;
      }
      const nextIdx = Math.min(idx + 1, wpList.length - 1);
      const dt = wpList[nextIdx].time - wpList[idx].time;
      const frac = dt > 0 ? Math.max(0, Math.min(1, (adjT - wpList[idx].time) / dt)) : 0;

      // +1 offset because jointTrajectory[0] is home
      const result = interpolateJoints(jointTrajectory[idx + 1], jointTrajectory[nextIdx + 1], frac);

      // Defensive guard
      const allZero = jointNames.every(n => Math.abs(result[n]) < 0.001);
      if (allZero && reachability && !reachability.some(Boolean)) return jointAngles;

      return result;
    }

    // No home padding — original behavior
    let idx = 0;
    for (let i = 1; i < wpList.length; i++) {
      if (wpList[i].time >= t) { idx = i - 1; break; }
      idx = i;
    }
    const nextIdx = Math.min(idx + 1, wpList.length - 1);
    const dt = wpList[nextIdx].time - wpList[idx].time;
    const frac = dt > 0 ? Math.max(0, Math.min(1, (t - wpList[idx].time) / dt)) : 0;

    const result = interpolateJoints(
      jointTrajectory[Math.min(idx, jointTrajectory.length - 1)] || [],
      jointTrajectory[Math.min(nextIdx, jointTrajectory.length - 1)] || [],
      frac,
    );

    // Defensive guard
    const allZero = jointNames.every(n => Math.abs(result[n]) < 0.001);
    if (allZero && reachability && !reachability.some(Boolean)) return jointAngles;

    return result;
  }, [mode, simMode, jointTrajectory, trajectory, simState.currentTime, jointAngles, reachability, homeJoints, homeTransitTime]);

  // ── Simulation waypoints ────────────────────────────────────────────────

  const waypoints = trajectory?.waypoints || [];
  // Adjust time for home transit padding: during home→first and last→home, no toolpath point
  const hasHomePad = homeJoints && jointTrajectory && trajectory && jointTrajectory.length === waypoints.length + 2;
  const htt = hasHomePad ? homeTransitTime : 0;
  const adjustedTime = simState.currentTime - htt;
  const inToolpathPhase = !hasHomePad || (simState.currentTime >= htt && simState.currentTime <= simState.totalTime - htt);
  const currentWp = mode === 'simulation' && simMode === 'toolpath' && inToolpathPhase
    ? waypointAtTime(waypoints, adjustedTime)
    : null;
  const tcpPos: [number, number, number] | null = currentWp
    ? toolpathPointToScene(currentWp.position as [number, number, number])
    : null;

  // ── Robot joint angles for current mode ─────────────────────────────────

  const robotJointAngles = mode === 'simulation'
    ? activeJointAngles
    : mode === 'setup'
      ? jointAngles  // Use store joint angles (editable via joint jog sliders)
      : {}; // geometry/toolpath mode: default pose

  // ── Geometry visibility by mode ─────────────────────────────────────────

  const showGeometry = mode === 'geometry' || mode === 'toolpath' || mode === 'simulation';
  const showToolpath = mode === 'toolpath' || mode === 'simulation';

  const showTransformControls = mode === 'geometry' && selectedPartId !== null;
  const showSimTrail = mode === 'simulation' && simMode === 'toolpath' && waypoints.length > 0;

  return (
    <>
      {/* Simulation clock — drives animation in the render loop */}
      <SimulationClock />

      {/* Follow-TCP camera updater */}
      {simState.followTCP && mode === 'simulation' && tcpPos && (
        <FollowTCPCamera tcpPos={tcpPos} />
      )}

      {/* Expose R3F state for diagnostic scripts */}
      <SceneStateExposer />
      {/* Test API for programmatic scene verification (dev only) */}
      <TestHarness />

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

      {/* Work Frame Gizmos — coordinate axes at each frame origin */}
      {workFrames.map((frame) => (
        <WorkFrameGizmo
          key={frame.id}
          frameId={frame.id}
          active={frame.id === activeFrameId}
        />
      ))}

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
        tcpOffset={cellSetup.endEffector.offset}
        showTCP={true}
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

        {/* ── Toolpath-related visuals (toolpath, trail, deposition, TCP marker) ──
            The toolpath is generated at mesh origin (centered XY, bottom at Z=0).
            We offset ALL toolpath visuals by the part's position so they align
            with the geometry mesh in the scene. */}
        {(() => {
          const tp = toolpathPartId ? geometryParts.find(p => p.id === toolpathPartId) : geometryParts[0];
          const tpPos: [number, number, number] = tp?.position
            ? [(tp.position.x || 0) * MM_TO_M, (tp.position.y || 0) * MM_TO_M, (tp.position.z || 0) * MM_TO_M]
            : [0, 0, 0];
          return (
            <group position={tpPos}>
              {/* Toolpath lines */}
              {showToolpath && toolpathData && toolpathData.segments && toolpathData.segments.length > 0 && (
                <ToolpathRenderer
                  segments={toolpathData.segments}
                  currentLayer={currentLayer}
                  showAllLayers={showAllLayers}
                  colorByType={true}
                  reachability={reachability}
                  colorMode={toolpathColorMode}
                  colorRange={toolpathColorRange}
                />
              )}

              {/* Simulation Trail */}
              {showSimTrail && (
                <ToolpathTrail waypoints={waypoints} currentTime={simState.currentTime} />
              )}

              {/* Deposition Visualization (growing part) */}
              {mode === 'simulation' && simMode === 'toolpath' && waypoints.length > 0 && (
                <DepositionVisualization
                  waypoints={waypoints}
                  currentTime={simState.currentTime}
                  visible={simState.showDeposition ?? true}
                />
              )}

              {/* TCP target indicator during simulation */}
              {mode === 'simulation' && tcpPos && (
                <mesh position={tcpPos}>
                  <sphereGeometry args={[0.03, 16, 16]} />
                  <meshStandardMaterial color="#22c55e" emissive="#22c55e" emissiveIntensity={0.5} />
                </mesh>
              )}
            </group>
          );
        })()}
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
