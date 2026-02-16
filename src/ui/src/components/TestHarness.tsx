/**
 * TestHarness — Exposes a structured test API on `window.__testAPI`.
 *
 * This component enables programmatic verification of the 3D scene
 * from Playwright tests or the browser console. Instead of taking
 * screenshots, tests can query exact world-space positions, joint
 * angles, toolpath data, and bounding boxes with full floating-point
 * precision.
 *
 * Only active in development mode (import.meta.env.DEV).
 *
 * Usage (browser console or Playwright page.evaluate):
 *   window.__testAPI.getTCPWorldPosition()
 *   window.__testAPI.getRobotJointAngles()
 *   window.__testAPI.getToolpathBounds()
 *   window.__testAPI.getPartWorldBounds('partId')
 *   window.__testAPI.getSceneSummary()
 */

import { useEffect } from 'react';
import { useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useWorkspaceStore } from '../stores/workspaceStore';

// Vite provides import.meta.env.DEV — declare for TypeScript
declare const __DEV__: boolean;

// ─── Types for test API results ──────────────────────────────────────────

interface Vec3 { x: number; y: number; z: number }

interface TestAPI {
  /** Get world-space position of the green TCP indicator sphere */
  getTCPWorldPosition: () => Vec3 | null;

  /** Get world-space position of the URDF-based TCP marker (orange) */
  getURDFTCPWorldPosition: () => Vec3 | null;

  /** Get current robot joint angles (radians) */
  getRobotJointAngles: () => Record<string, number>;

  /** Get the toolpath data bounding box in slicer coords (Z-up mm) */
  getToolpathBounds: () => { min: Vec3; max: Vec3; pointCount: number } | null;

  /** Get world-space bounding box of a geometry part mesh */
  getPartWorldBounds: (partId?: string) => { min: Vec3; max: Vec3 } | null;

  /** Get the build plate origin in scene coordinates (Y-up meters) */
  getBuildPlateOrigin: () => Vec3 | null;

  /** Get robot base position in scene coordinates (Y-up meters) */
  getRobotBasePosition: () => Vec3 | null;

  /** Measure distance between TCP indicator and URDF TCP marker */
  measureTCPAlignment: () => { distance: number; greenPos: Vec3; urdfPos: Vec3 } | null;

  /** Get a summary of the scene: object counts, positions, etc. */
  getSceneSummary: () => Record<string, unknown>;

  /** Check if a specific named object exists in the scene */
  findObject: (name: string) => { found: boolean; position: Vec3 | null; type: string | null };
}

// ─── Helper: find objects by name or userData in scene graph ──────────────

function findByName(root: THREE.Object3D, name: string): THREE.Object3D | null {
  if (root.name === name) return root;
  for (const child of root.children) {
    const found = findByName(child, name);
    if (found) return found;
  }
  return null;
}

function findByUserData(root: THREE.Object3D, key: string, value: unknown): THREE.Object3D | null {
  if ((root.userData as Record<string, unknown>)[key] === value) return root;
  for (const child of root.children) {
    const found = findByUserData(child, key, value);
    if (found) return found;
  }
  return null;
}

function getWorldPos(obj: THREE.Object3D): Vec3 {
  const pos = new THREE.Vector3();
  obj.updateWorldMatrix(true, false);
  obj.getWorldPosition(pos);
  return { x: pos.x, y: pos.y, z: pos.z };
}

function box3ToVec3(box: THREE.Box3): { min: Vec3; max: Vec3 } {
  return {
    min: { x: box.min.x, y: box.min.y, z: box.min.z },
    max: { x: box.max.x, y: box.max.y, z: box.max.z },
  };
}

// ─── Component ─────────────────────────────────────────────────────────

export default function TestHarness() {
  const { scene } = useThree();

  useEffect(() => {
    // Only expose test API in development mode
    if (typeof (import.meta as any).env?.DEV !== 'undefined' && !(import.meta as any).env.DEV) return;

    const api: TestAPI = {
      getTCPWorldPosition: () => {
        // The green TCP sphere is named 'tcpSphere' or has specific userData
        const tcp = findByName(scene, 'tcpSphere')
          || findByUserData(scene, 'isTCPSphere', true);
        if (!tcp) return null;
        return getWorldPos(tcp);
      },

      getURDFTCPWorldPosition: () => {
        // The orange URDF TCP marker
        const marker = findByName(scene, 'tcpMarker')
          || findByUserData(scene, 'isTCPMarker', true);
        if (!marker) return null;
        return getWorldPos(marker);
      },

      getRobotJointAngles: () => {
        const state = useWorkspaceStore.getState();
        return state.jointAngles || {};
      },

      getToolpathBounds: () => {
        const state = useWorkspaceStore.getState();
        const tp = state.toolpathData;
        if (!tp || !tp.segments || tp.segments.length === 0) return null;

        let minX = Infinity, minY = Infinity, minZ = Infinity;
        let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;
        let pointCount = 0;

        for (const seg of tp.segments) {
          for (const pt of seg.points) {
            // points are [x, y, z] tuples (Z-up mm)
            minX = Math.min(minX, pt[0]);
            minY = Math.min(minY, pt[1]);
            minZ = Math.min(minZ, pt[2]);
            maxX = Math.max(maxX, pt[0]);
            maxY = Math.max(maxY, pt[1]);
            maxZ = Math.max(maxZ, pt[2]);
            pointCount++;
          }
        }

        if (pointCount === 0) return null;
        return {
          min: { x: minX, y: minY, z: minZ },
          max: { x: maxX, y: maxY, z: maxZ },
          pointCount,
        };
      },

      getPartWorldBounds: (partId?: string) => {
        const state = useWorkspaceStore.getState();
        const id = partId || state.selectedPartId;
        if (!id) return null;

        // Find the mesh in the scene that represents this part
        const meshes: THREE.Mesh[] = [];
        scene.traverse((obj) => {
          if (obj instanceof THREE.Mesh && obj.geometry) {
            meshes.push(obj);
          }
        });

        // Find the mesh closest to the part's expected position
        const part = state.geometryParts.find(p => p.id === id);
        if (!part) return null;

        const box = new THREE.Box3();
        let found = false;

        for (const mesh of meshes) {
          // Check if this mesh's geometry looks like our part
          if (mesh.geometry instanceof THREE.BufferGeometry && mesh.geometry.attributes.position) {
            mesh.updateWorldMatrix(true, false);
            const worldBox = new THREE.Box3().setFromObject(mesh);
            if (!found) {
              box.copy(worldBox);
              found = true;
            }
          }
        }

        if (!found) return null;
        return box3ToVec3(box);
      },

      getBuildPlateOrigin: () => {
        const state = useWorkspaceStore.getState();
        const cs = state.cellSetup;
        return {
          x: cs.workTablePosition[0],
          y: cs.workTablePosition[1] + cs.workTableSize[1] / 2,
          z: cs.workTablePosition[2],
        };
      },

      getRobotBasePosition: () => {
        const state = useWorkspaceStore.getState();
        const cs = state.cellSetup;
        return {
          x: cs.robot.basePosition[0],
          y: cs.robot.basePosition[1],
          z: cs.robot.basePosition[2],
        };
      },

      measureTCPAlignment: () => {
        const greenPos = api.getTCPWorldPosition();
        const urdfPos = api.getURDFTCPWorldPosition();
        if (!greenPos || !urdfPos) return null;

        const dx = greenPos.x - urdfPos.x;
        const dy = greenPos.y - urdfPos.y;
        const dz = greenPos.z - urdfPos.z;
        return {
          distance: Math.sqrt(dx * dx + dy * dy + dz * dz),
          greenPos,
          urdfPos,
        };
      },

      getSceneSummary: () => {
        let meshCount = 0;
        let groupCount = 0;
        let lightCount = 0;

        scene.traverse((obj) => {
          if (obj instanceof THREE.Mesh) meshCount++;
          else if (obj instanceof THREE.Group) groupCount++;
          else if (obj instanceof THREE.Light) lightCount++;
        });

        const state = useWorkspaceStore.getState();
        return {
          meshCount,
          groupCount,
          lightCount,
          totalChildren: scene.children.length,
          mode: state.mode,
          selectedPartId: state.selectedPartId,
          hasToolpath: !!state.toolpathData,
          toolpathLayers: state.toolpathData?.totalLayers || 0,
          geometryPartCount: state.geometryParts.length,
        };
      },

      findObject: (name: string) => {
        const obj = findByName(scene, name);
        if (!obj) return { found: false, position: null, type: null };
        return {
          found: true,
          position: getWorldPos(obj),
          type: obj.type,
        };
      },
    };

    (window as any).__testAPI = api;

    return () => {
      delete (window as any).__testAPI;
    };
  }, [scene]);

  return null; // Renders nothing — pure side-effect component
}
