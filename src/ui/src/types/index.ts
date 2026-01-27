// Core types for OpenAxis application

import * as THREE from 'three';

// Project Types
export interface Project {
  id: string;
  name: string;
  description: string;
  process: ProcessType;
  createdAt: string;
  modifiedAt: string;
  status: ProjectStatus;
  thumbnail?: string;
  geometry?: GeometryData;
  toolpath?: ToolpathData;
  settings: ProjectSettings;
}

export type ProjectStatus = 'draft' | 'ready' | 'in_progress' | 'completed' | 'failed';
export type ProcessType = 'waam' | 'pellet_extrusion' | 'milling' | 'hybrid';

export interface ProjectSettings {
  units: 'metric' | 'imperial';
  robotType: string;
  processParameters: Record<string, any>;
}

// Geometry Types
export interface GeometryData {
  id: string;
  name: string;
  format: 'stl' | 'obj' | 'step';
  filePath: string;
  parts: GeometryPart[];
  boundingBox: BoundingBox;
}

export interface GeometryPart {
  id: string;
  name: string;
  visible: boolean;
  color: string;
  mesh?: THREE.Mesh;
  transform: Transform;
}

export interface BoundingBox {
  min: THREE.Vector3;
  max: THREE.Vector3;
  center: THREE.Vector3;
  size: THREE.Vector3;
}

export interface Transform {
  position: [number, number, number];
  rotation: [number, number, number];
  scale: [number, number, number];
}

// Toolpath Types
export interface ToolpathData {
  id: string;
  name: string;
  process: ProcessType;
  segments: ToolpathSegment[];
  layers: number;
  totalLength: number;
  estimatedTime: number;
  metadata: ToolpathMetadata;
}

export interface ToolpathSegment {
  id: string;
  type: ToolpathType;
  points: THREE.Vector3[];
  speed: number;
  layer: number;
  processParameters: Record<string, any>;
}

export type ToolpathType = 'travel' | 'print' | 'retract' | 'arc' | 'blend';

export interface ToolpathMetadata {
  materialUsed: number;
  printTime: number;
  layerHeight: number;
  infillDensity: number;
  supports: boolean;
}

// Robot Types
export interface RobotConfiguration {
  id: string;
  name: string;
  manufacturer: string;
  model: string;
  type: 'industrial' | 'collaborative';
  dof: number;
  payload: number;
  reach: number;
  urdfPath?: string;
  ipAddress?: string;
  port?: number;
  jointLimits: JointLimit[];
  workEnvelope: WorkEnvelope;
}

export interface JointLimit {
  joint: number;
  min: number;
  max: number;
  maxSpeed: number;
  maxAcceleration: number;
}

export interface WorkEnvelope {
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
  zMin: number;
  zMax: number;
}

export interface RobotState {
  connected: boolean;
  enabled: boolean;
  moving: boolean;
  error: string | null;
  jointPositions: number[];
  tcpPosition: [number, number, number];
  tcpOrientation: [number, number, number];
}

// Process Types
export interface ProcessParameters {
  [key: string]: number | string | boolean;
}

export interface WAAMParameters extends ProcessParameters {
  wireDiameter: number;
  wireFeedRate: number;
  travelSpeed: number;
  arcVoltage: number;
  arcCurrent: number;
  shieldingGas: string;
  gasFlowRate: number;
  interLayerTemperature: number;
  coolingTime: number;
}

export interface PelletExtrusionParameters extends ProcessParameters {
  nozzleDiameter: number;
  layerHeight: number;
  extrusionTemperature: number;
  bedTemperature: number;
  extrusionRate: number;
  printSpeed: number;
  travelSpeed: number;
  retractionDistance: number;
}

export interface MillingParameters extends ProcessParameters {
  toolDiameter: number;
  spindleSpeed: number;
  feedRate: number;
  plungeRate: number;
  depthOfCut: number;
  stepover: number;
  climbMilling: boolean;
  coolantEnabled: boolean;
}

// Simulation Types
export interface SimulationState {
  isRunning: boolean;
  isPaused: boolean;
  currentTime: number;
  totalTime: number;
  speed: number;
  currentLayer: number;
  totalLayers: number;
  collisionDetected: boolean;
  warnings: SimulationWarning[];
}

export interface SimulationWarning {
  type: 'collision' | 'singularity' | 'joint_limit' | 'workspace';
  message: string;
  timestamp: number;
  severity: 'low' | 'medium' | 'high';
}

// Monitoring Types
export interface SensorData {
  timestamp: number;
  temperature?: number;
  flowRate?: number;
  pressure?: number;
  force?: number;
  current?: number;
  voltage?: number;
}

export interface SystemStatus {
  cpuUsage: number;
  memoryUsage: number;
  diskUsage: number;
  networkLatency: number;
}

export interface Alert {
  id: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
  dismissed: boolean;
}

// IPC Types (for Electron communication)
export interface IPCRequest {
  channel: string;
  method: string;
  params?: any;
}

export interface IPCResponse {
  success: boolean;
  data?: any;
  error?: string;
}

// API Types (for Python backend)
export interface APIResponse<T = any> {
  status: 'success' | 'error';
  data?: T;
  message?: string;
  error?: string;
}

export interface JobStatus {
  id: string;
  name: string;
  status: 'queued' | 'running' | 'paused' | 'completed' | 'failed';
  progress: number;
  startTime?: string;
  estimatedCompletion?: string;
  currentOperation?: string;
}
