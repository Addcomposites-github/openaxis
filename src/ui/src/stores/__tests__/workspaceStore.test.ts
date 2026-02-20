/**
 * Tests for workspaceStore — mode changes, geometry CRUD, toolpath state.
 *
 * Focuses on state logic; IndexedDB hydration is mocked since jsdom
 * doesn't have a real IDB implementation.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock geometryDB before importing the store (it uses IndexedDB which jsdom lacks)
vi.mock('../geometryDB', () => ({
  saveGeometryFile: vi.fn().mockResolvedValue(undefined),
  loadAllGeometryFiles: vi.fn().mockResolvedValue(new Map()),
  deleteGeometryFile: vi.fn().mockResolvedValue(undefined),
}));

import { useWorkspaceStore } from '../workspaceStore';
import type { GeometryPartData, ToolpathData } from '../workspaceStore';

function getState() {
  return useWorkspaceStore.getState();
}

const makePart = (overrides: Partial<GeometryPartData> = {}): GeometryPartData => ({
  id: `part-${Math.random().toString(36).slice(2, 8)}`,
  name: 'Test Part',
  visible: true,
  color: '#ff0000',
  fileType: 'stl',
  ...overrides,
});

const makeToolpath = (overrides: Partial<ToolpathData> = {}): ToolpathData => ({
  id: 'tp-1',
  layerHeight: 1.0,
  totalLayers: 10,
  processType: 'waam',
  segments: [],
  statistics: {
    totalSegments: 0,
    totalPoints: 0,
    layerCount: 10,
    estimatedTime: 100,
    estimatedMaterial: 50,
  },
  ...overrides,
});

describe('workspaceStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    const state = getState();
    state.setMode('setup');
    state.setGeometryParts([]);
    state.setSelectedPartId(null);
    state.setToolpathData(null);
    state.setToolpathStale(false);
    state.setIKStatus('idle');
    state.setJointTrajectory(null);
    state.setReachability(null);
    state.setTrajectory(null);
  });

  // ── Mode transitions ─────────────────────────────────────────────────

  describe('setMode', () => {
    it('changes mode to geometry', () => {
      getState().setMode('geometry');
      expect(getState().mode).toBe('geometry');
    });

    it('changes mode to toolpath', () => {
      getState().setMode('toolpath');
      expect(getState().mode).toBe('toolpath');
    });

    it('changes mode to simulation', () => {
      getState().setMode('simulation');
      expect(getState().mode).toBe('simulation');
    });
  });

  // ── Geometry CRUD ────────────────────────────────────────────────────

  describe('geometry parts', () => {
    it('addGeometryPart appends a part', () => {
      const part = makePart({ id: 'p1', name: 'Cube' });
      getState().addGeometryPart(part);
      expect(getState().geometryParts).toHaveLength(1);
      expect(getState().geometryParts[0].name).toBe('Cube');
    });

    it('removeGeometryPart removes by id', () => {
      const p1 = makePart({ id: 'p1' });
      const p2 = makePart({ id: 'p2' });
      getState().addGeometryPart(p1);
      getState().addGeometryPart(p2);
      getState().removeGeometryPart('p1');
      expect(getState().geometryParts).toHaveLength(1);
      expect(getState().geometryParts[0].id).toBe('p2');
    });

    it('removeGeometryPart clears selection when removing selected part', () => {
      const part = makePart({ id: 'p1' });
      getState().addGeometryPart(part);
      getState().setSelectedPartId('p1');
      getState().removeGeometryPart('p1');
      expect(getState().selectedPartId).toBeNull();
    });

    it('updateGeometryPart updates fields', () => {
      const part = makePart({ id: 'p1', name: 'Old', color: '#000' });
      getState().addGeometryPart(part);
      getState().updateGeometryPart('p1', { name: 'New', color: '#fff' });
      const updated = getState().geometryParts[0];
      expect(updated.name).toBe('New');
      expect(updated.color).toBe('#fff');
    });

    it('updateGeometryPart marks toolpath stale on position change', () => {
      const part = makePart({ id: 'p1' });
      getState().addGeometryPart(part);
      getState().setToolpathData(makeToolpath());
      expect(getState().toolpathStale).toBe(false);

      getState().updateGeometryPart('p1', { position: { x: 1, y: 0, z: 0 } });
      expect(getState().toolpathStale).toBe(true);
    });

    it('setGeometryParts replaces all parts', () => {
      getState().addGeometryPart(makePart({ id: 'p1' }));
      getState().addGeometryPart(makePart({ id: 'p2' }));
      getState().setGeometryParts([makePart({ id: 'p3' })]);
      expect(getState().geometryParts).toHaveLength(1);
      expect(getState().geometryParts[0].id).toBe('p3');
    });
  });

  // ── Selection & Transform ────────────────────────────────────────────

  describe('selection', () => {
    it('setSelectedPartId sets selection', () => {
      getState().setSelectedPartId('abc');
      expect(getState().selectedPartId).toBe('abc');
    });

    it('setTransformMode changes mode', () => {
      getState().setTransformMode('rotate');
      expect(getState().transformMode).toBe('rotate');
    });
  });

  // ── Toolpath ─────────────────────────────────────────────────────────

  describe('toolpath', () => {
    it('setToolpathData stores data and resets layer', () => {
      getState().setCurrentLayer(5);
      getState().setToolpathData(makeToolpath({ id: 'tp-new' }));
      expect(getState().toolpathData?.id).toBe('tp-new');
      expect(getState().currentLayer).toBe(0);
      expect(getState().toolpathStale).toBe(false);
    });

    it('setToolpathData with null clears data', () => {
      getState().setToolpathData(makeToolpath());
      getState().setToolpathData(null);
      expect(getState().toolpathData).toBeNull();
    });

    it('setCurrentLayer and setShowAllLayers', () => {
      getState().setCurrentLayer(7);
      expect(getState().currentLayer).toBe(7);
      getState().setShowAllLayers(true);
      expect(getState().showAllLayers).toBe(true);
    });
  });

  // ── Simulation state ─────────────────────────────────────────────────

  describe('simulation', () => {
    it('setSimMode changes mode', () => {
      getState().setSimMode('toolpath');
      expect(getState().simMode).toBe('toolpath');
    });

    it('setSimState merges partial updates', () => {
      getState().setSimState({ isRunning: true, speed: 2.0 });
      const s = getState().simState;
      expect(s.isRunning).toBe(true);
      expect(s.speed).toBe(2.0);
      expect(s.showDeposition).toBe(true); // unchanged default
    });

    it('setJointAngle updates a single joint', () => {
      getState().setJointAngle('joint_1', 1.5);
      expect(getState().jointAngles.joint_1).toBe(1.5);
    });

    it('setIKStatus updates status', () => {
      getState().setIKStatus('computing');
      expect(getState().ikStatus).toBe('computing');
    });

    it('setTrajectory resets IK state on change', () => {
      getState().setJointTrajectory([[0, 0, 0, 0, 0, 0]]);
      getState().setReachability([true]);
      getState().setIKStatus('ready');

      getState().setTrajectory({
        totalTime: 10,
        waypoints: [{ position: [0, 0, 0], orientation: [0, 0, 0, 1], time: 0 }],
      } as any);

      expect(getState().jointTrajectory).toBeNull();
      expect(getState().reachability).toBeNull();
      expect(getState().ikStatus).toBe('idle');
    });
  });

  // ── Cell Setup ───────────────────────────────────────────────────────

  describe('cellSetup', () => {
    it('updateCellSetup merges partial updates', () => {
      getState().updateCellSetup({
        workTableSize: [2, 0.1, 2],
      });
      expect(getState().cellSetup.workTableSize).toEqual([2, 0.1, 2]);
      // Other fields remain
      expect(getState().cellSetup.robot.model).toBe('abb_irb6700');
    });
  });
});
