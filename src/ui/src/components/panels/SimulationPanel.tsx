/**
 * SimulationPanel — Simulation controls, joint sliders, IK status
 * (extracted from Simulation.tsx).
 * Reads/writes to workspaceStore simulation state.
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import toast from 'react-hot-toast';
import {
  PlayIcon,
  PauseIcon,
  ForwardIcon,
  BackwardIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useRobotStore } from '../../stores/robotStore';
import { getRobotConfig, getJointLimits, computeFK, computeIK, loadRobot, solveTrajectoryIK } from '../../api/robot';
import type { RobotConfig, JointLimits, FKResult } from '../../api/robot';
import { createSimulation, getTrajectory } from '../../api/simulation';
import { checkHealth } from '../../api/client';
import type { Waypoint } from '../../api/simulation';
import { waypointToRobotFrame } from '../../utils/units';
import { solveTrajectoryIKLocal } from '../../utils/analyticalIK';
import QualityPanel from '../QualityPanel';

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

export default function SimulationPanel() {
  const toolpathData = useWorkspaceStore((s) => s.toolpathData);
  const toolpathPartId = useWorkspaceStore((s) => s.toolpathPartId);
  const geometryParts = useWorkspaceStore((s) => s.geometryParts);
  const simMode = useWorkspaceStore((s) => s.simMode);
  const simState = useWorkspaceStore((s) => s.simState);
  const jointAngles = useWorkspaceStore((s) => s.jointAngles);
  const ikStatus = useWorkspaceStore((s) => s.ikStatus);
  const trajectory = useWorkspaceStore((s) => s.trajectory);

  const setSimMode = useWorkspaceStore((s) => s.setSimMode);
  const setSimState = useWorkspaceStore((s) => s.setSimState);
  const setJointAngle = useWorkspaceStore((s) => s.setJointAngle);
  const setJointTrajectory = useWorkspaceStore((s) => s.setJointTrajectory);
  const setReachability = useWorkspaceStore((s) => s.setReachability);
  const setIKStatus = useWorkspaceStore((s) => s.setIKStatus);
  const setTrajectory = useWorkspaceStore((s) => s.setTrajectory);
  const setHomeJoints = useWorkspaceStore((s) => s.setHomeJoints);
  const homeTransitTime = useWorkspaceStore((s) => s.homeTransitTime);

  // Backend state (local to this panel)
  const [backendConnected, setBackendConnected] = useState(false);
  const [robotConfig, setRobotConfig] = useState<RobotConfig | null>(null);
  const [jointLimits, setJointLimits] = useState<JointLimits | null>(null);
  const [fkResult, setFkResult] = useState<FKResult | null>(null);
  const [loadingTrajectory, setLoadingTrajectory] = useState(false);
  const [currentLayer, setCurrentLayer] = useState(0);
  const [totalLayers, setTotalLayers] = useState(0);

  // TCP target move state
  const [tcpTarget, setTcpTarget] = useState({ x: '', y: '', z: '', rx: '', ry: '', rz: '' });
  const [tcpMoveStatus, setTcpMoveStatus] = useState<'idle' | 'solving' | 'ok' | 'error'>('idle');
  const [tcpMoveError, setTcpMoveError] = useState<string | null>(null);

  // Refs to prevent double-fire in React strict mode
  const backendConnectedRef = useRef(false);
  const ikComputingRef = useRef(false);
  const trajectoryLoadedRef = useRef(false);
  const ikAbortRef = useRef(false);
  backendConnectedRef.current = backendConnected;

  // Elapsed time for IK computation
  const [ikElapsedMs, setIkElapsedMs] = useState(0);
  const ikTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startIkTimer = useCallback(() => {
    setIkElapsedMs(0);
    if (ikTimerRef.current) clearInterval(ikTimerRef.current);
    const t0 = performance.now();
    ikTimerRef.current = setInterval(() => {
      setIkElapsedMs(Math.round(performance.now() - t0));
    }, 200);
  }, []);

  const stopIkTimer = useCallback(() => {
    if (ikTimerRef.current) {
      clearInterval(ikTimerRef.current);
      ikTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => { stopIkTimer(); };
  }, [stopIkTimer]);

  const handleCancelIK = useCallback(() => {
    ikAbortRef.current = true;
    ikComputingRef.current = false;
    stopIkTimer();
    setIKStatus('idle');
  }, [stopIkTimer, setIKStatus]);

  const handleTcpMove = useCallback(async () => {
    const x = parseFloat(tcpTarget.x);
    const y = parseFloat(tcpTarget.y);
    const z = parseFloat(tcpTarget.z);
    if (isNaN(x) || isNaN(y) || isNaN(z)) {
      setTcpMoveError('X, Y, Z are required and must be numbers.');
      setTcpMoveStatus('error');
      return;
    }
    // Convert mm → metres for the IK solver
    const pos: [number, number, number] = [x / 1000, y / 1000, z / 1000];

    // Build optional orientation as [rx, ry, rz] in degrees (backend expects degrees)
    const rxDeg = parseFloat(tcpTarget.rx);
    const ryDeg = parseFloat(tcpTarget.ry);
    const rzDeg = parseFloat(tcpTarget.rz);
    const hasOrientation = !isNaN(rxDeg) && !isNaN(ryDeg) && !isNaN(rzDeg);
    const orientation = hasOrientation ? [rxDeg, ryDeg, rzDeg] : undefined;

    // TCP offset from the configured end-effector: [x,y,z,rx,ry,rz] meters+degrees, flange frame.
    const tcpOff = [
      endEffectorOffset[0] || 0,
      endEffectorOffset[1] || 0,
      endEffectorOffset[2] || 0,
      endEffectorOffset[3] || 0,
      endEffectorOffset[4] || 0,
      endEffectorOffset[5] || 0,
    ];

    setTcpMoveStatus('solving');
    setTcpMoveError(null);
    try {
      const result = await computeIK(pos, orientation, undefined, tcpOff);
      if (result.valid && result.solution) {
        // Prefer names returned by the solver; fall back to jointLimits state
        const names = result.jointNames ?? jointLimits?.jointNames ?? Object.keys(jointAngles);
        names.forEach((name, i) => {
          if (i < result.solution!.length) setJointAngle(name, result.solution![i]);
        });
        setTcpMoveStatus('ok');
      } else {
        setTcpMoveError(result.error || 'IK solver found no solution for this target.');
        setTcpMoveStatus('error');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setTcpMoveError(msg);
      setTcpMoveStatus('error');
    }
  }, [tcpTarget, jointLimits, jointAngles, setJointAngle]);

  // Init backend connection and load robot config
  useEffect(() => {
    const init = async () => {
      const health = await checkHealth();
      setBackendConnected(health.ok);

      const storedConfig = useRobotStore.getState().configuration;
      if (storedConfig) {
        setRobotConfig({
          name: storedConfig.name,
          manufacturer: storedConfig.manufacturer,
          type: storedConfig.type,
          dof: storedConfig.dof,
          maxPayload: storedConfig.payload,
          maxReach: storedConfig.reach,
          urdfPath: storedConfig.urdfPath,
        });
      }

      if (health.ok) {
        try {
          if (!storedConfig) {
            const config = await getRobotConfig();
            setRobotConfig(config);
          }
          const limits = await getJointLimits();
          setJointLimits(limits);
          await loadRobot();
        } catch (e) {
          console.warn('Failed to load robot data from backend:', e);
        }
      }
    };
    init();
  }, []);

  // If we have toolpath data, create simulation trajectory
  useEffect(() => {
    if (!toolpathData || !backendConnected) return;
    // Guard: don't reload if we already have a trajectory or are already loading
    if (trajectory || trajectoryLoadedRef.current) return;

    trajectoryLoadedRef.current = true;

    const loadSim = async () => {
      setLoadingTrajectory(true);
      try {
        console.log('[SimPanel] Loading simulation trajectory...');
        const simInfo = await createSimulation(toolpathData.id);
        const traj = await getTrajectory(simInfo.id);
        console.log(`[SimPanel] Trajectory loaded: ${traj.waypoints?.length} waypoints, ${traj.totalTime}s`);
        // Derive totalLayers: prefer API value, then toolpath data, then max layer from waypoints
        let layers = simInfo.totalLayers || toolpathData.totalLayers || 0;
        if (layers === 0 && traj.waypoints?.length > 0) {
          let maxL = 0;
          for (const w of traj.waypoints) { if ((w.layer ?? 0) > maxL) maxL = w.layer ?? 0; }
          layers = maxL + 1;
        }
        setTotalLayers(layers);
        setTrajectory(traj);

        // Auto-speed: calculate a speed that makes the full simulation play in ~3 minutes
        // This ensures intra-layer motion is visible to the user
        const TARGET_PLAYBACK_SECONDS = 180; // 3 minutes for full sim
        let autoSpeed = 1.0;
        if (traj.totalTime > TARGET_PLAYBACK_SECONDS) {
          autoSpeed = Math.round(traj.totalTime / TARGET_PLAYBACK_SECONDS);
          // Snap to nearest standard speed option
          const speedOptions = [1, 2, 5, 10, 50, 100, 500, 1000];
          autoSpeed = speedOptions.reduce((prev, curr) =>
            Math.abs(curr - autoSpeed) < Math.abs(prev - autoSpeed) ? curr : prev
          );
        }
        console.log(`[SimPanel] Auto-speed: ${autoSpeed}x (totalTime=${traj.totalTime.toFixed(0)}s, target=${TARGET_PLAYBACK_SECONDS}s)`);

        setSimState({ totalTime: traj.totalTime, currentTime: 0, speed: autoSpeed });
        setSimMode('toolpath');
      } catch (e) {
        console.warn('Failed to create simulation from toolpath:', e);
        trajectoryLoadedRef.current = false; // Allow retry
        setSimMode('manual');
      } finally {
        setLoadingTrajectory(false);
      }
    };
    loadSim();
  }, [toolpathData, backendConnected]); // eslint-disable-line react-hooks/exhaustive-deps

  // Read cell setup for coordinate transforms
  const cellSetup = useWorkspaceStore((s) => s.cellSetup);
  const endEffectorOffset = cellSetup.endEffector.offset;

  // Compute build plate origin in scene space (Y-up, meters)
  const buildPlateOrigin: [number, number, number] = useMemo(() => [
    cellSetup.workTablePosition[0],
    cellSetup.workTablePosition[1] + cellSetup.workTableSize[1] / 2,
    cellSetup.workTablePosition[2],
  ], [cellSetup.workTablePosition, cellSetup.workTableSize]);

  // ── IK computation — backend roboticstoolbox-python solver ──────────────────
  //
  // Primary: Backend IK via roboticstoolbox-python (Peter Corke).
  //   Production-grade DH-based solver using Levenberg-Marquardt optimization.
  //   Each solution seeds the next for smooth joint trajectories (~30-90μs/pt).
  //
  // Fallback: If backend is unavailable, use local stub (returns unreachable).
  //

  useEffect(() => {
    if (!trajectory || ikStatus !== 'idle') return;
    if (ikComputingRef.current) return;
    ikComputingRef.current = true;

    const computeIK = async () => {
      setIKStatus('computing');
      ikAbortRef.current = false;
      startIkTimer();

      // Transform all waypoints to robot base frame (meters, Z-up)
      const robotPositionScene: [number, number, number] = [
        cellSetup.robot.basePosition[0],
        cellSetup.robot.basePosition[1],
        cellSetup.robot.basePosition[2],
      ];

      // The toolpath is origin-centered (backend slices at origin).
      // Add the part's position offset before converting to robot frame.
      const tpPart = toolpathPartId
        ? geometryParts.find(p => p.id === toolpathPartId)
        : geometryParts[0];
      const partOffsetZUp: [number, number, number] = tpPart?.position
        ? [tpPart.position.x || 0, -(tpPart.position.z || 0), tpPart.position.y || 0]
        : [0, 0, 0];

      const positions: [number, number, number][] = trajectory.waypoints.map(
        (w) => {
          const wp = w.position as [number, number, number];
          const offsetWp: [number, number, number] = [
            wp[0] + partOffsetZUp[0],
            wp[1] + partOffsetZUp[1],
            wp[2] + partOffsetZUp[2],
          ];
          return waypointToRobotFrame(
            offsetWp,
            buildPlateOrigin,
            robotPositionScene,
          );
        }
      );

      const totalWps = positions.length;
      const eox = endEffectorOffset[0] || 0;
      const eoy = endEffectorOffset[1] || 0;
      const eoz = endEffectorOffset[2] || 0;
      // Full 6DOF TCP offset: translation (meters) + rotation (degrees ZYX Euler), in flange frame.
      // Matches ABB tooldata, KUKA $TOOL, Fanuc UTOOL conventions.
      const eorx = endEffectorOffset[3] || 0;
      const eory = endEffectorOffset[4] || 0;
      const eorz = endEffectorOffset[5] || 0;
      const toolLength = Math.sqrt(eox * eox + eoy * eoy + eoz * eoz) || 0.15;

      // Build per-waypoint normals in robot base frame.
      // The normal from the slicer is in slicer frame (Z-up mm) — same axes as robot
      // base frame (both Z-up), so we apply only the coordinate-axis swap used in
      // waypointToRobotFrame but for a direction vector (no translation, no scale).
      // Slicer frame Z-up → robot frame Z-up:
      //   scene Y-up transform: slicer (x,y,z) → scene (x, z, -y)
      //   scene→robot inverse:  scene (x,y,z)  → robot (x, -z, y)
      //   combined:             slicer (nx,ny,nz) → robot (nx, nz, ny)
      //   Note: scale (mm→m) cancels for a unit vector.
      const robotNormals: [number, number, number][] = trajectory.waypoints.map((w) => {
        const n = (w.normal as [number, number, number]) ?? [0, 0, 1];
        // Apply same axis swap as waypointToRobotFrame (direction vector, no translation)
        return [n[0], n[2], n[1]];
      });

      const t0 = performance.now();

      // Try backend roboticstoolbox-python solver first
      if (backendConnectedRef.current) {
        try {
          // Full 6DOF TCP offset: [x,y,z,rx,ry,rz] meters + degrees, flange frame.
          const tcpOffset = [eox, eoy, eoz, eorx, eory, eorz];
          console.log(`[IK] Solving ${totalWps} waypoints via backend (roboticstoolbox-python, Levenberg-Marquardt)...`);
          const result = await solveTrajectoryIK(positions, undefined, tcpOffset, 0, 0, robotNormals);
          const dt = performance.now() - t0;
          stopIkTimer();

          // Check if cancelled during solve
          if (ikAbortRef.current) return;

          // Pad trajectory with home position at start and end
          const home = cellSetup.robot.homePosition;
          if (home && home.length === 6) {
            const padded = [home, ...result.trajectory, home];
            const paddedReach = [true, ...result.reachability, true];
            setJointTrajectory(padded);
            setReachability(paddedReach);
            setHomeJoints(home);
            // Extend total time to include home transit
            const originalTime = trajectory?.totalTime || simState.totalTime;
            setSimState({ totalTime: originalTime + 2 * homeTransitTime });
          } else {
            setJointTrajectory(result.trajectory);
            setReachability(result.reachability);
          }
          setIKStatus('ready');
          ikComputingRef.current = false;

          console.log(
            `[IK] Backend solved ${totalWps} waypoints in ${dt.toFixed(0)}ms: ` +
            `${result.reachableCount}/${totalWps} reachable (${result.reachabilityPercent.toFixed(1)}%)`
          );
          return;
        } catch (backendErr) {
          console.error('[IK] Backend IK failed:', {
            error: backendErr instanceof Error ? backendErr.message : String(backendErr),
            waypoints: totalWps,
            samplePosition: positions[0],
            robotBase: robotPositionScene,
          });
        }
      }

      // Fallback: local stub (offline mode)
      try {
        console.log(`[IK] Using local fallback IK for ${totalWps} waypoints (tool=${toolLength.toFixed(3)}m)...`);
        const result = solveTrajectoryIKLocal(positions, toolLength);
        const dt = performance.now() - t0;
        stopIkTimer();

        if (ikAbortRef.current) return;

        if (result.reachableCount === 0) {
          // Stub returned all-zeros — treat as failure, don't freeze the robot
          console.warn('[IK] Fallback IK returned 0 reachable — backend unavailable. Robot arm will not move.');
          setJointTrajectory(null);
          setReachability(null);
          setIKStatus('failed');
        } else {
          setJointTrajectory(result.trajectory);
          setReachability(result.reachability);
          setIKStatus('fallback');
        }
        ikComputingRef.current = false;

        console.log(
          `[IK] Fallback: ${totalWps} waypoints in ${dt.toFixed(0)}ms: ` +
          `${result.reachableCount}/${totalWps} reachable (${result.reachabilityPercent.toFixed(1)}%)`
        );
      } catch (e) {
        console.error('[IK] All IK solvers failed:', e);
        toast.error('IK solver failed. Check that the toolpath is within robot reach.');
        stopIkTimer();
        setIKStatus('failed');
        ikComputingRef.current = false;
      }
    };
    computeIK();
  }, [trajectory, ikStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  // Derive totalLayers from trajectory when available (handles cached trajectories)
  useEffect(() => {
    if (!trajectory || totalLayers > 0) return;
    const wps = trajectory.waypoints;
    if (wps && wps.length > 0) {
      let maxLayer = 0;
      for (const w of wps) { if ((w.layer ?? 0) > maxLayer) maxLayer = w.layer ?? 0; }
      setTotalLayers(maxLayer + 1);
    }
  }, [trajectory, totalLayers]);

  // Update current layer from sim time
  useEffect(() => {
    if (simMode !== 'toolpath' || !trajectory) return;
    const wp = waypointAtTime(trajectory.waypoints, simState.currentTime);
    if (wp) setCurrentLayer(wp.layer);
  }, [simState.currentTime, trajectory, simMode]);

  // FK computation (debounced)
  const fkTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const updateFK = useCallback(
    (angles: Record<string, number>) => {
      if (!backendConnected) return;
      if (fkTimerRef.current) clearTimeout(fkTimerRef.current);
      fkTimerRef.current = setTimeout(async () => {
        try {
          // Full 6DOF TCP offset: [x,y,z,rx,ry,rz] meters + degrees, flange frame.
          // fkine() with robot.tool set returns TCP position (not just flange).
          const tcpOff = [
            endEffectorOffset[0] || 0,
            endEffectorOffset[1] || 0,
            endEffectorOffset[2] || 0,
            endEffectorOffset[3] || 0,
            endEffectorOffset[4] || 0,
            endEffectorOffset[5] || 0,
          ];
          const result = await computeFK(Object.values(angles), tcpOff);
          setFkResult(result);
        } catch {
          // FK not available
        }
      }, 100);
    },
    [backendConnected, endEffectorOffset]
  );

  useEffect(() => {
    return () => { if (fkTimerRef.current) clearTimeout(fkTimerRef.current); };
  }, []);

  useEffect(() => {
    if (simMode === 'manual') updateFK(jointAngles);
  }, [jointAngles, updateFK, simMode]);

  // Simulation timer is now driven by useFrame in SceneManager (SimulationClock)
  // for perfectly smooth 60fps updates. This effect only handles end-of-sim stop.
  useEffect(() => {
    if (simState.isRunning && simState.currentTime >= simState.totalTime) {
      setSimState({ isRunning: false });
    }
  }, [simState.isRunning, simState.currentTime, simState.totalTime, setSimState]);

  // Joint limit checking
  const jointLimitStatus = useMemo(() => {
    if (!jointLimits) return { ok: true, violations: [] as string[] };
    const violations: string[] = [];
    for (const name of jointLimits.jointNames) {
      const limit = jointLimits.limits[name];
      const value = jointAngles[name] ?? 0;
      if (limit && (value < limit.min || value > limit.max)) {
        violations.push(name);
      }
    }
    return { ok: violations.length === 0, violations };
  }, [jointAngles, jointLimits]);

  const singularityWarning = useMemo(() => {
    const j5 = jointAngles.joint_5 ?? 0;
    return Math.abs(j5) < 0.05;
  }, [jointAngles]);

  const handlePlayPause = () => setSimState({ isRunning: !simState.isRunning });
  const handleReset = () => setSimState({ isRunning: false, currentTime: 0 });
  const handleSpeedChange = (speed: number) => setSimState({ speed });
  const handleTimeChange = (time: number) => setSimState({ currentTime: time });

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const toDegrees = (rad: number) => (rad * 180) / Math.PI;

  const reachability = useWorkspaceStore((s) => s.reachability);
  const jointNames = jointLimits?.jointNames || Object.keys(jointAngles);
  const limits = jointLimits?.limits || {};
  const waypoints = trajectory?.waypoints || [];
  const currentWp = simMode === 'toolpath' ? waypointAtTime(waypoints, simState.currentTime) : null;

  // Reachability stats
  const reachableCount = reachability ? reachability.filter(Boolean).length : 0;
  const totalWpCount = reachability ? reachability.length : 0;
  const reachabilityPct = totalWpCount > 0 ? (reachableCount / totalWpCount) * 100 : 0;
  const allReachable = reachableCount === totalWpCount && totalWpCount > 0;

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">Trajectory Preview</h3>
        {robotConfig && <p className="text-xs text-gray-500 mt-1">{robotConfig.name}</p>}
      </div>

      {/* Status Badges */}
      <div className="px-4 pt-3 flex items-center flex-wrap gap-2">
        {simMode === 'toolpath' && (
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-600 text-white">Toolpath Mode</span>
        )}
        {ikStatus === 'computing' && (
          <span className="inline-flex items-center gap-1.5">
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-yellow-500 text-white animate-pulse">
              Computing IK{trajectory ? ` (${trajectory.waypoints.length} pts)` : ''}
              {ikElapsedMs > 0 ? ` — ${(ikElapsedMs / 1000).toFixed(1)}s` : '...'}
            </span>
            <button
              onClick={handleCancelIK}
              className="px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700 hover:bg-yellow-200 transition-colors"
              title="Cancel IK computation"
            >
              Cancel
            </button>
          </span>
        )}
        {ikStatus === 'ready' && (
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-600 text-white" title="roboticstoolbox-python (Levenberg-Marquardt)">
            IK Ready — {reachabilityPct.toFixed(0)}% reachable
          </span>
        )}
        {ikStatus === 'fallback' && (
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-yellow-600 text-white" title="Local fallback — backend unavailable">IK Offline</span>
        )}
        {ikStatus === 'failed' && (
          <span className="inline-flex items-center gap-1.5">
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-red-500 text-white">IK Failed</span>
            <button
              onClick={() => setIKStatus('idle')}
              className="px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700 hover:bg-red-200 transition-colors"
              title="Re-attempt IK computation"
            >
              Retry
            </button>
          </span>
        )}
        <span
          className={`px-3 py-1 rounded-full text-xs font-medium ${
            backendConnected ? 'bg-green-600 text-white' : 'bg-yellow-500 text-white'
          }`}
        >
          {backendConnected ? 'Backend Connected' : 'Offline Mode'}
        </span>
      </div>

      {/* Loading indicator */}
      {loadingTrajectory && (
        <div className="mx-4 mt-3 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg">
          Loading trajectory...
        </div>
      )}

      <div className="flex-1 overflow-auto p-4 space-y-6">
        {/* Mode Toggle */}
        <div className="flex rounded-lg overflow-hidden border border-gray-200">
          <button
            onClick={() => setSimMode('manual')}
            className={`flex-1 py-2 text-xs font-medium ${
              simMode === 'manual' ? 'bg-blue-600 text-white' : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
            }`}
          >
            Manual
          </button>
          <button
            onClick={() => setSimMode('toolpath')}
            disabled={!trajectory}
            className={`flex-1 py-2 text-xs font-medium ${
              simMode === 'toolpath'
                ? 'bg-blue-600 text-white'
                : trajectory
                  ? 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            Toolpath {!trajectory && '(none)'}
          </button>
        </div>

        {/* Status Cards */}
        <div className="space-y-3">
          <div className="border rounded-lg p-3 bg-gray-50 border-gray-200">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-600" title="Requires PyBullet physics backend">Collision Check</span>
              <span className="px-2 py-1 bg-gray-400 text-white text-xs font-semibold rounded">Not Active</span>
            </div>
            <p className="text-xs text-gray-400 mt-1">PyBullet physics not active</p>
          </div>

          <div className={`border rounded-lg p-3 ${jointLimitStatus.ok ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
            <div className="flex items-center justify-between">
              <span className={`text-xs font-medium ${jointLimitStatus.ok ? 'text-green-800' : 'text-red-800'}`}>Joint Limits</span>
              <span className={`px-2 py-1 text-white text-xs font-semibold rounded ${jointLimitStatus.ok ? 'bg-green-600' : 'bg-red-600'}`}>
                {jointLimitStatus.ok ? 'OK' : `${jointLimitStatus.violations.length} VIOLATION`}
              </span>
            </div>
          </div>

          <div className={`border rounded-lg p-3 ${singularityWarning ? 'bg-yellow-50 border-yellow-200' : 'bg-green-50 border-green-200'}`}>
            <div className="flex items-center justify-between">
              <span className={`text-xs font-medium ${singularityWarning ? 'text-yellow-800' : 'text-green-800'}`}>Singularities</span>
              <span className={`px-2 py-1 text-white text-xs font-semibold rounded ${singularityWarning ? 'bg-yellow-500' : 'bg-green-600'}`}>
                {singularityWarning ? 'WRIST' : 'NONE'}
              </span>
            </div>
          </div>

          {/* Reachability */}
          {reachability && (
            <div className={`border rounded-lg p-3 ${allReachable ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
              <div className="flex items-center justify-between">
                <span className={`text-xs font-medium ${allReachable ? 'text-green-800' : 'text-red-800'}`}>Reachability</span>
                <span className={`px-2 py-1 text-white text-xs font-semibold rounded ${allReachable ? 'bg-green-600' : 'bg-red-600'}`}>
                  {allReachable ? 'ALL OK' : `${totalWpCount - reachableCount} FAIL`}
                </span>
              </div>
              {!allReachable && (
                <div className="mt-2">
                  <div className="flex justify-between text-xs text-red-700 mb-1">
                    <span>{reachableCount}/{totalWpCount} reachable</span>
                    <span>{reachabilityPct.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-red-200 rounded-full h-1.5">
                    <div
                      className="bg-green-500 h-1.5 rounded-full"
                      style={{ width: `${reachabilityPct}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Quality Summary (compact) */}
          {toolpathData && (
            <div className="border rounded-lg p-3 bg-gray-50 border-gray-200">
              <QualityPanel compact />
            </div>
          )}
        </div>

        {/* Joint Control / Trajectory Info */}
        {simMode === 'manual' ? (
          <>
          <div>
            <h4 className="text-xs font-semibold text-gray-700 mb-3">Joint Angles (drag to move robot)</h4>
            <div className="space-y-2">
              {jointNames.map((name) => {
                const limit = limits[name] || { min: -3.14, max: 3.14 };
                const value = jointAngles[name] || 0;
                const isViolation = jointLimitStatus.violations.includes(name);
                return (
                  <div key={name} className="space-y-1">
                    <div className="flex justify-between items-center text-sm">
                      <span className={isViolation ? 'text-red-600 font-semibold' : 'text-gray-600'}>
                        {name.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                      </span>
                      <span className={`font-medium font-mono text-xs ${isViolation ? 'text-red-600' : 'text-gray-900'}`}>
                        {toDegrees(value).toFixed(1)}&deg;
                      </span>
                    </div>
                    <input
                      type="range"
                      min={limit.min}
                      max={limit.max}
                      step="0.01"
                      value={value}
                      onChange={(e) => setJointAngle(name, parseFloat(e.target.value))}
                      className="w-full h-1"
                    />
                  </div>
                );
              })}
            </div>
          </div>

          {/* TCP Target Move */}
          <div className="border rounded-lg p-3 bg-gray-50 border-gray-200">
            <h4 className="text-xs font-semibold text-gray-700 mb-3">
              Move TCP to Target
              <span className="text-gray-400 ml-1 font-normal text-[10px]">(Robot Base Frame)</span>
            </h4>
            <div className="grid grid-cols-2 gap-2 mb-2">
              {([
                { key: 'x', label: 'X — forward', color: 'text-red-500' },
                { key: 'y', label: 'Y — left',    color: 'text-green-500' },
                { key: 'z', label: 'Z — up ↑',    color: 'text-blue-500' },
              ] as const).map(({ key: axis, label, color }) => (
                <div key={axis} className="flex flex-col">
                  <label className={`text-[10px] mb-0.5 font-semibold ${color}`}>{label} (mm)</label>
                  <input
                    type="number"
                    step="0.1"
                    placeholder="0.0"
                    value={tcpTarget[axis]}
                    onChange={(e) => {
                      setTcpTarget((prev) => ({ ...prev, [axis]: e.target.value }));
                      setTcpMoveStatus('idle');
                    }}
                    className="border border-gray-300 rounded px-2 py-1 text-xs font-mono bg-white focus:outline-none focus:border-blue-400 w-full"
                  />
                </div>
              ))}
              {(['rx', 'ry', 'rz'] as const).map((axis) => (
                <div key={axis} className="flex flex-col">
                  <label className="text-[10px] text-gray-500 mb-0.5 uppercase">{axis} (deg)</label>
                  <input
                    type="number"
                    step="0.1"
                    placeholder="optional"
                    value={tcpTarget[axis]}
                    onChange={(e) => {
                      setTcpTarget((prev) => ({ ...prev, [axis]: e.target.value }));
                      setTcpMoveStatus('idle');
                    }}
                    className="border border-gray-300 rounded px-2 py-1 text-xs font-mono bg-white focus:outline-none focus:border-blue-400 w-full"
                  />
                </div>
              ))}
            </div>
            <button
              onClick={handleTcpMove}
              disabled={tcpMoveStatus === 'solving' || !backendConnected}
              className={`w-full py-1.5 text-xs font-semibold rounded transition-colors ${
                tcpMoveStatus === 'solving'
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : !backendConnected
                    ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              {tcpMoveStatus === 'solving' ? 'Solving IK…' : 'Move to Target'}
            </button>
            {tcpMoveStatus === 'ok' && (
              <p className="text-[10px] text-green-600 mt-1">IK solved — robot moved to target.</p>
            )}
            {tcpMoveStatus === 'error' && tcpMoveError && (
              <p className="text-[10px] text-red-500 mt-1">{tcpMoveError}</p>
            )}
            {!backendConnected && (
              <p className="text-[10px] text-gray-400 mt-1">Backend offline — start server to enable.</p>
            )}
          </div>
          </>
        ) : (
          <div>
            <h4 className="text-xs font-semibold text-gray-700 mb-3">Trajectory Info</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Waypoints</span>
                <span className="font-medium text-gray-900">{trajectory?.totalWaypoints ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Duration</span>
                <span className="font-medium text-gray-900">{formatTime(trajectory?.totalTime ?? 0)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Current Layer</span>
                <span className="font-medium text-gray-900">{currentLayer} / {totalLayers}</span>
              </div>
              {currentWp && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Segment</span>
                  <span className="font-medium text-gray-900 capitalize">{currentWp.segmentType}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TCP Position */}
        <div>
          <h4 className="text-xs font-semibold text-gray-700 mb-3">
            TCP Position
            <span className="text-gray-400 ml-1 font-normal text-[10px]">(Robot Base Frame, mm)</span>
            {simMode === 'manual' && fkResult?.solver && (
              <span className="text-gray-400 ml-1 font-normal text-[10px]" title={`FK solver: ${fkResult.solver}`}>
                [{fkResult.solver}]
              </span>
            )}
          </h4>
          <div className="space-y-2">
            {simMode === 'toolpath' && currentWp ? (
              <>
                {(['X', 'Y', 'Z'] as const).map((axis, i) => (
                  <div key={axis} className="flex justify-between items-center text-sm">
                    <span className="text-gray-600">{axis}</span>
                    <span className="font-medium text-gray-900 font-mono">
                      {currentWp.position[i].toFixed(1)} mm
                    </span>
                  </div>
                ))}
              </>
            ) : fkResult?.valid ? (
              <>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-600">
                    <span className="text-red-500 font-bold text-xs">X</span>
                    <span className="text-gray-400 ml-1 text-[10px]">forward</span>
                  </span>
                  <span className="font-medium text-gray-900 font-mono">{(fkResult.position.x * 1000).toFixed(1)} mm</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-600">
                    <span className="text-green-500 font-bold text-xs">Y</span>
                    <span className="text-gray-400 ml-1 text-[10px]">left</span>
                  </span>
                  <span className="font-medium text-gray-900 font-mono">{(fkResult.position.y * 1000).toFixed(1)} mm</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-600">
                    <span className="text-blue-500 font-bold text-xs">Z</span>
                    <span className="text-gray-400 ml-1 text-[10px]">up ↑</span>
                  </span>
                  <span className="font-medium text-gray-900 font-mono">{(fkResult.position.z * 1000).toFixed(1)} mm</span>
                </div>
              </>
            ) : fkResult && !fkResult.valid ? (
              <p className="text-xs text-red-500">FK error: {fkResult.error || 'Solver unavailable'}</p>
            ) : (
              <p className="text-xs text-gray-400">Start backend for live FK</p>
            )}
          </div>
        </div>

        {/* Process Parameters */}
        <div>
          <h4 className="text-xs font-semibold text-gray-700 mb-3">Process Status</h4>
          <div className="space-y-2">
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-600">Temperature</span>
              <span className="font-medium text-gray-400 italic">No sensor connected</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-600">Flow Rate</span>
              <span className="font-medium text-gray-400 italic">No sensor connected</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-600">Layer</span>
              <span className="font-medium text-gray-900">
                {simMode === 'toolpath' ? `${currentLayer}/${totalLayers}` : '\u2014'}
              </span>
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Hardware monitoring available in Phase 4 (Robot Raconteur integration).
          </p>
        </div>
      </div>

      {/* Playback Controls (bottom of panel) */}
      <div className="border-t border-gray-200 p-4 bg-gray-50">
        <div className="flex items-center justify-center space-x-3 mb-3">
          <button
            onClick={() => handleTimeChange(Math.max(0, simState.currentTime - simState.totalTime * 0.03))}
            className="p-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
          >
            <BackwardIcon className="w-4 h-4" />
          </button>

          <button
            onClick={handlePlayPause}
            className="p-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            {simState.isRunning ? <PauseIcon className="w-5 h-5" /> : <PlayIcon className="w-5 h-5" />}
          </button>

          <button
            onClick={() => handleTimeChange(Math.min(simState.totalTime, simState.currentTime + simState.totalTime * 0.03))}
            className="p-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
          >
            <ForwardIcon className="w-4 h-4" />
          </button>

          <button onClick={handleReset} className="p-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors">
            <ArrowPathIcon className="w-4 h-4" />
          </button>

          <select
            value={simState.speed}
            onChange={(e) => handleSpeedChange(Number(e.target.value))}
            className="px-2 py-1 border border-gray-300 rounded text-xs"
          >
            <option value="0.25">0.25x</option>
            <option value="0.5">0.5x</option>
            <option value="1">1x</option>
            <option value="2">2x</option>
            <option value="5">5x</option>
            <option value="10">10x</option>
            <option value="50">50x</option>
            <option value="100">100x</option>
            <option value="500">500x</option>
            <option value="1000">1000x</option>
          </select>
        </div>

        <input
          type="range"
          min="0"
          max={simState.totalTime || 1}
          step={simState.totalTime > 0 ? simState.totalTime / 1000 : 0.1}
          value={simState.currentTime}
          onChange={(e) => handleTimeChange(Number(e.target.value))}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-gray-600 mt-1">
          <span>{formatTime(simState.currentTime)}</span>
          {simMode === 'toolpath' && trajectory && (
            <span className="text-blue-600">
              Layer {currentLayer}/{totalLayers}
            </span>
          )}
          <span>{formatTime(simState.totalTime)}</span>
        </div>

        {/* Follow TCP toggle + Show Deposition toggle */}
        {simMode === 'toolpath' && trajectory && (
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <button
              onClick={() => setSimState({ followTCP: !simState.followTCP })}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                simState.followTCP
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {simState.followTCP ? 'Following TCP' : 'Follow TCP'}
            </button>
            <button
              onClick={() => setSimState({ showDeposition: !simState.showDeposition })}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                simState.showDeposition
                  ? 'bg-amber-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {simState.showDeposition ? 'Deposition ON' : 'Show Deposition'}
            </button>
          </div>
        )}

        {/* Jump-to-layer input */}
        {simMode === 'toolpath' && trajectory && totalLayers > 0 && (
          <div className="flex items-center gap-2 mt-2">
            <label className="text-xs text-gray-600 whitespace-nowrap">Jump to layer:</label>
            <input
              type="number"
              min={0}
              max={totalLayers}
              placeholder={String(currentLayer)}
              className="w-16 px-2 py-1 border border-gray-300 rounded text-xs text-center"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const target = parseInt((e.target as HTMLInputElement).value, 10);
                  if (!isNaN(target) && target >= 0 && target <= totalLayers) {
                    // Find the first waypoint at the target layer
                    const wp = trajectory.waypoints.find((w) => w.layer >= target);
                    if (wp) {
                      handleTimeChange(wp.time);
                      (e.target as HTMLInputElement).value = '';
                    }
                  }
                }
              }}
            />
            <span className="text-xs text-gray-400">/ {totalLayers}</span>
          </div>
        )}
      </div>
    </div>
  );
}
