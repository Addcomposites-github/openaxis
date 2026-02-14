/**
 * SimulationPanel — Simulation controls, joint sliders, IK status
 * (extracted from Simulation.tsx).
 * Reads/writes to workspaceStore simulation state.
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  PlayIcon,
  PauseIcon,
  ForwardIcon,
  BackwardIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useRobotStore } from '../../stores/robotStore';
import { getRobotConfig, getJointLimits, computeFK, loadRobot, solveTrajectoryIK } from '../../api/robot';
import type { RobotConfig, JointLimits, FKResult } from '../../api/robot';
import { createSimulation, getTrajectory } from '../../api/simulation';
import { checkHealth } from '../../api/client';
import type { Waypoint } from '../../api/simulation';
import { waypointToRobotFrame } from '../../utils/units';
import { solveTrajectoryIKLocal } from '../../utils/analyticalIK';

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

  // Backend state (local to this panel)
  const [backendConnected, setBackendConnected] = useState(false);
  const [robotConfig, setRobotConfig] = useState<RobotConfig | null>(null);
  const [jointLimits, setJointLimits] = useState<JointLimits | null>(null);
  const [fkResult, setFkResult] = useState<FKResult | null>(null);
  const [loadingTrajectory, setLoadingTrajectory] = useState(false);
  const [currentLayer, setCurrentLayer] = useState(0);
  const [totalLayers, setTotalLayers] = useState(0);

  // Refs to prevent double-fire in React strict mode
  const backendConnectedRef = useRef(false);
  const ikComputingRef = useRef(false);
  const trajectoryLoadedRef = useRef(false);
  backendConnectedRef.current = backendConnected;

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
        setSimState({ totalTime: traj.totalTime, currentTime: 0 });
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

  // Pre-compute IK for trajectory — two-stage: backend first, then frontend fallback
  useEffect(() => {
    if (!trajectory || ikStatus !== 'idle') return;
    // Guard: prevent double computation in React strict mode
    if (ikComputingRef.current) return;
    ikComputingRef.current = true;

    const computeIK = async () => {
      setIKStatus('computing');
      console.log('[IK] Starting IK computation...');

      // Transform waypoints to robot base frame (meters, Z-up)
      const robotPositionScene: [number, number, number] = [0, 0, 0]; // Robot at scene origin
      const robotFramePositions: [number, number, number][] = trajectory.waypoints.map(
        (w) => waypointToRobotFrame(
          w.position as [number, number, number],
          buildPlateOrigin,
          robotPositionScene,
        )
      );

      // Stage 1: Try backend IK if connected
      if (backendConnectedRef.current) {
        try {
          const tcpOffset = [...endEffectorOffset];
          const ikResult = await solveTrajectoryIK(robotFramePositions, undefined, tcpOffset);
          if (ikResult.trajectory && ikResult.trajectory.length > 0) {
            setJointTrajectory(ikResult.trajectory);
            setReachability(ikResult.reachability);
            setIKStatus('ready');
            ikComputingRef.current = false;
            console.log(
              `[IK Backend] Solved: ${ikResult.reachableCount}/${ikResult.totalPoints} reachable ` +
              `(${ikResult.reachabilityPercent.toFixed(1)}%)`
            );
            return;
          }
          console.warn('[IK Backend] Returned empty trajectory, falling back to frontend IK');
        } catch (e) {
          console.warn('[IK Backend] Failed, falling back to frontend IK:', e);
        }
      }

      // Stage 2: Frontend analytical IK fallback
      try {
        const toolLength = endEffectorOffset[2] || 0.15;
        console.log(`[IK Fallback] Computing analytical IK for ${robotFramePositions.length} waypoints...`);
        const t0 = performance.now();
        const result = solveTrajectoryIKLocal(robotFramePositions, toolLength);
        const dt = performance.now() - t0;
        setJointTrajectory(result.trajectory);
        setReachability(result.reachability);
        setIKStatus('fallback');
        ikComputingRef.current = false;
        console.log(
          `[IK Fallback] Solved in ${dt.toFixed(0)}ms: ${result.reachableCount}/${result.totalPoints} reachable ` +
          `(${result.reachabilityPercent.toFixed(1)}%)`
        );
      } catch (e) {
        console.error('[IK] Both backend and frontend IK failed:', e);
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
          const result = await computeFK(Object.values(angles));
          setFkResult(result);
        } catch {
          // FK not available
        }
      }, 100);
    },
    [backendConnected]
  );

  useEffect(() => {
    return () => { if (fkTimerRef.current) clearTimeout(fkTimerRef.current); };
  }, []);

  useEffect(() => {
    if (simMode === 'manual') updateFK(jointAngles);
  }, [jointAngles, updateFK, simMode]);

  // Simulation timer
  useEffect(() => {
    if (simState.isRunning && simState.currentTime < simState.totalTime) {
      const interval = setInterval(() => {
        setSimState({
          currentTime: Math.min(simState.currentTime + simState.speed * 0.1, simState.totalTime),
        });
      }, 100);
      return () => clearInterval(interval);
    } else if (simState.isRunning && simState.currentTime >= simState.totalTime) {
      setSimState({ isRunning: false });
    }
  }, [simState.isRunning, simState.currentTime, simState.totalTime, simState.speed, setSimState]);

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
        <h3 className="text-sm font-semibold text-gray-900">Simulation Status</h3>
        {robotConfig && <p className="text-xs text-gray-500 mt-1">{robotConfig.name}</p>}
      </div>

      {/* Status Badges */}
      <div className="px-4 pt-3 flex items-center flex-wrap gap-2">
        {simMode === 'toolpath' && (
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-600 text-white">Toolpath Mode</span>
        )}
        {ikStatus === 'computing' && (
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-yellow-500 text-white animate-pulse">Computing IK...</span>
        )}
        {ikStatus === 'ready' && (
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-600 text-white">IK Ready</span>
        )}
        {ikStatus === 'fallback' && (
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-yellow-600 text-white">IK Approx.</span>
        )}
        {ikStatus === 'failed' && (
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-red-500 text-white">IK Unavailable</span>
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
              <span className="text-xs font-medium text-gray-600">Collision Check</span>
              <span className="px-2 py-1 bg-gray-400 text-white text-xs font-semibold rounded">N/A</span>
            </div>
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
        </div>

        {/* Joint Control / Trajectory Info */}
        {simMode === 'manual' ? (
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
            {simMode === 'manual' && fkResult?.mock && <span className="text-yellow-600 ml-1">(estimated)</span>}
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
            ) : fkResult ? (
              <>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-600">X</span>
                  <span className="font-medium text-gray-900 font-mono">{(fkResult.position.x * 1000).toFixed(1)} mm</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-600">Y</span>
                  <span className="font-medium text-gray-900 font-mono">{(fkResult.position.y * 1000).toFixed(1)} mm</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-600">Z</span>
                  <span className="font-medium text-gray-900 font-mono">{(fkResult.position.z * 1000).toFixed(1)} mm</span>
                </div>
              </>
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
              <span className="font-medium text-gray-900">220&deg;C</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-600">Flow Rate</span>
              <span className="font-medium text-gray-900">10 mm&sup3;/s</span>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-600">Layer</span>
              <span className="font-medium text-gray-900">
                {simMode === 'toolpath' ? `${currentLayer}/${totalLayers}` : '\u2014'}
              </span>
            </div>
          </div>
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
