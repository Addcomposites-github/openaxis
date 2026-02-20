/**
 * Tests for robot API client — mocks axios, validates request shapes.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getRobotConfig,
  getAvailableRobots,
  getJointLimits,
  getRobotState,
  computeFK,
  computeIK,
  solveTrajectoryIK,
  connectRobot,
  disconnectRobot,
  homeRobot,
  loadRobot,
} from '../robot';
import { apiClient } from '../client';

// Mock the apiClient module
vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
  // Re-export the ApiResponse type (it's just used for type annotations)
}));

const mockGet = apiClient.get as ReturnType<typeof vi.fn>;
const mockPost = apiClient.post as ReturnType<typeof vi.fn>;

function successResponse(data: any) {
  return { data: { status: 'success', data } };
}

function errorResponse(error: string) {
  return { data: { status: 'error', error } };
}

describe('robot API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── GET endpoints ────────────────────────────────────────────────────

  describe('getRobotConfig', () => {
    it('sends correct request and returns config', async () => {
      const config = { name: 'abb_irb6700', manufacturer: 'ABB', type: '6-axis' };
      mockGet.mockResolvedValue(successResponse(config));

      const result = await getRobotConfig('abb_irb6700');
      expect(mockGet).toHaveBeenCalledWith(
        expect.stringContaining('/api/robot/config?name=abb_irb6700')
      );
      expect(result.name).toBe('abb_irb6700');
    });

    it('throws on error response', async () => {
      mockGet.mockResolvedValue(errorResponse('Robot not found'));
      await expect(getRobotConfig('bad')).rejects.toThrow('Robot not found');
    });
  });

  describe('getAvailableRobots', () => {
    it('returns robot list', async () => {
      mockGet.mockResolvedValue(successResponse(['abb_irb6700', 'kuka_kr6']));
      const result = await getAvailableRobots();
      expect(result).toEqual(['abb_irb6700', 'kuka_kr6']);
    });

    it('returns empty array when data is null', async () => {
      mockGet.mockResolvedValue({ data: { status: 'success', data: null } });
      const result = await getAvailableRobots();
      expect(result).toEqual([]);
    });
  });

  describe('getJointLimits', () => {
    it('returns joint limits', async () => {
      const limits = {
        jointNames: ['j1', 'j2'],
        limits: { j1: { min: -3.14, max: 3.14 }, j2: { min: -1.57, max: 1.57 } },
      };
      mockGet.mockResolvedValue(successResponse(limits));
      const result = await getJointLimits();
      expect(result.jointNames).toHaveLength(2);
    });
  });

  describe('getRobotState', () => {
    it('returns robot state', async () => {
      const state = {
        connected: false,
        enabled: false,
        moving: false,
        joint_positions: [0, 0, 0, 0, 0, 0],
        tcp_position: [0, 0, 0],
        tcp_orientation: [0, 0, 0],
      };
      mockGet.mockResolvedValue(successResponse(state));
      const result = await getRobotState();
      expect(result.connected).toBe(false);
      expect(result.joint_positions).toHaveLength(6);
    });
  });

  // ── POST endpoints ───────────────────────────────────────────────────

  describe('connectRobot', () => {
    it('returns updated state', async () => {
      mockPost.mockResolvedValue(
        successResponse({ connected: true, enabled: true, moving: false, joint_positions: [0, 0, 0, 0, 0, 0], tcp_position: [0, 0, 0], tcp_orientation: [0, 0, 0] })
      );
      const result = await connectRobot();
      expect(result.connected).toBe(true);
      expect(mockPost).toHaveBeenCalledWith(expect.stringContaining('/api/robot/connect'));
    });
  });

  describe('disconnectRobot', () => {
    it('returns updated state', async () => {
      mockPost.mockResolvedValue(
        successResponse({ connected: false, enabled: false, moving: false, joint_positions: [0, 0, 0, 0, 0, 0], tcp_position: [0, 0, 0], tcp_orientation: [0, 0, 0] })
      );
      const result = await disconnectRobot();
      expect(result.connected).toBe(false);
    });
  });

  describe('homeRobot', () => {
    it('throws on error', async () => {
      mockPost.mockResolvedValue(errorResponse('Not connected'));
      await expect(homeRobot()).rejects.toThrow('Not connected');
    });
  });

  describe('loadRobot', () => {
    it('returns true on success', async () => {
      mockPost.mockResolvedValue(successResponse({ loaded: true }));
      const result = await loadRobot('abb_irb6700');
      expect(result).toBe(true);
    });

    it('returns false when loaded is false', async () => {
      mockPost.mockResolvedValue(successResponse({ loaded: false }));
      const result = await loadRobot('bad');
      expect(result).toBe(false);
    });
  });

  describe('computeFK', () => {
    it('sends joint values and returns FK result', async () => {
      const fkResult = {
        position: { x: 1.5, y: 0, z: 2.0 },
        orientation: { xaxis: [1, 0, 0], yaxis: [0, 1, 0], zaxis: [0, 0, 1] },
        valid: true,
      };
      mockPost.mockResolvedValue(successResponse(fkResult));
      const result = await computeFK([0, -0.5, 0.5, 0, -0.5, 0]);
      expect(mockPost).toHaveBeenCalledWith(
        expect.stringContaining('/api/robot/fk'),
        expect.objectContaining({ jointValues: [0, -0.5, 0.5, 0, -0.5, 0] })
      );
      expect(result.valid).toBe(true);
      expect(result.position.x).toBe(1.5);
    });

    it('passes tcpOffset when provided', async () => {
      mockPost.mockResolvedValue(successResponse({ position: { x: 0, y: 0, z: 0 }, orientation: {}, valid: true }));
      await computeFK([0, 0, 0, 0, 0, 0], [0, 0, 0.15, 0, 0, 0]);
      expect(mockPost).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({ tcpOffset: [0, 0, 0.15, 0, 0, 0] })
      );
    });
  });

  describe('computeIK', () => {
    it('sends target and returns solution', async () => {
      mockPost.mockResolvedValue(
        successResponse({ solution: [0.1, -0.5, 0.5, 0, -0.5, 0], valid: true })
      );
      const result = await computeIK([1.5, 0, 2.0]);
      expect(result.valid).toBe(true);
      expect(result.solution).toHaveLength(6);
    });

    it('throws on failure', async () => {
      mockPost.mockResolvedValue(errorResponse('Target unreachable'));
      await expect(computeIK([99, 99, 99])).rejects.toThrow('Target unreachable');
    });
  });

  describe('solveTrajectoryIK', () => {
    it('sends waypoints and returns trajectory', async () => {
      const ikResult = {
        trajectory: [[0, 0, 0, 0, 0, 0], [0.1, -0.5, 0.5, 0, -0.5, 0]],
        reachability: [true, true],
        reachableCount: 2,
        totalPoints: 2,
        reachabilityPercent: 100,
      };
      mockPost.mockResolvedValue(successResponse(ikResult));

      const result = await solveTrajectoryIK(
        [[1.5, 0, 0.5], [1.5, 0.1, 0.5]],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0.15, 0, 0, 0],
      );

      expect(mockPost).toHaveBeenCalledWith(
        expect.stringContaining('/api/robot/solve-trajectory'),
        expect.objectContaining({
          waypoints: [[1.5, 0, 0.5], [1.5, 0.1, 0.5]],
          initialGuess: [0, 0, 0, 0, 0, 0],
          tcpOffset: [0, 0, 0.15, 0, 0, 0],
          chunkStart: 0,
          chunkSize: 0,
        }),
        expect.objectContaining({ timeout: 300000 })
      );
      expect(result.reachableCount).toBe(2);
      expect(result.trajectory).toHaveLength(2);
    });
  });
});
