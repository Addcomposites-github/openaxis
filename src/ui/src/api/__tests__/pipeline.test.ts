/**
 * Tests for the pipeline API client.
 *
 * Verifies:
 * - executePipeline sends correct request shape
 * - Success response is returned
 * - Error response throws with message
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { executePipeline } from '../pipeline';
import { apiClient } from '../client';

vi.mock('../client', () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

describe('executePipeline', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('sends correct request to /api/pipeline/execute', async () => {
    const mockResult = {
      success: true,
      toolpathData: { id: 'tp-1', totalLayers: 10 },
      simulationData: null,
      trajectoryData: null,
      errors: [],
      timings: { slicing: 1.5 },
      stepCompleted: 'slicing',
      steps: [{ name: 'slicing', success: true, error: null, duration: 1.5 }],
    };

    (apiClient.post as any).mockResolvedValue({
      data: { status: 'success', data: mockResult },
    });

    const result = await executePipeline({
      geometryPath: '/tmp/cube.stl',
      slicingParams: { layerHeight: 2.0 },
      robotName: 'abb_irb6700',
      tcpOffset: [0, 0, 0.15, 0, 0, 0],
      partPosition: [100, 0, 50],
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/api/pipeline/execute',
      {
        geometryPath: '/tmp/cube.stl',
        slicingParams: { layerHeight: 2.0 },
        robotName: 'abb_irb6700',
        tcpOffset: [0, 0, 0.15, 0, 0, 0],
        partPosition: [100, 0, 50],
      },
      { timeout: 600000 },
    );

    expect(result.success).toBe(true);
    expect(result.toolpathData).toEqual({ id: 'tp-1', totalLayers: 10 });
    expect(result.stepCompleted).toBe('slicing');
  });

  it('returns full pipeline result with trajectory data', async () => {
    const mockResult = {
      success: true,
      toolpathData: { id: 'tp-2', totalLayers: 5 },
      simulationData: { trajectory: { waypoints: [], totalTime: 60 } },
      trajectoryData: {
        trajectory: [[0, -0.5, 0.5, 0, -0.5, 0]],
        reachability: [true],
        reachableCount: 1,
        reachabilityPercent: 100,
      },
      errors: [],
      timings: { slicing: 1.0, simulation: 0.5, ik_solve: 3.0 },
      stepCompleted: 'ik_solve',
      steps: [
        { name: 'slicing', success: true, error: null, duration: 1.0 },
        { name: 'simulation', success: true, error: null, duration: 0.5 },
        { name: 'ik_solve', success: true, error: null, duration: 3.0 },
      ],
    };

    (apiClient.post as any).mockResolvedValue({
      data: { status: 'success', data: mockResult },
    });

    const result = await executePipeline({ geometryPath: '/tmp/test.stl' });

    expect(result.trajectoryData).toBeDefined();
    expect(result.trajectoryData.reachableCount).toBe(1);
    expect(result.steps).toHaveLength(3);
  });

  it('throws on error response', async () => {
    (apiClient.post as any).mockResolvedValue({
      data: { status: 'error', error: 'Slicing failed: mesh too small' },
    });

    await expect(
      executePipeline({ geometryPath: '/tmp/bad.stl' }),
    ).rejects.toThrow('Slicing failed: mesh too small');
  });

  it('throws generic message when no error detail', async () => {
    (apiClient.post as any).mockResolvedValue({
      data: { status: 'error' },
    });

    await expect(
      executePipeline({ geometryPath: '/tmp/bad.stl' }),
    ).rejects.toThrow('Pipeline execution failed');
  });

  it('uses 10 minute timeout', async () => {
    (apiClient.post as any).mockResolvedValue({
      data: { status: 'success', data: { success: true, errors: [], steps: [], timings: {}, stepCompleted: '' } },
    });

    await executePipeline({ geometryPath: '/tmp/test.stl' });

    expect(apiClient.post).toHaveBeenCalledWith(
      expect.anything(),
      expect.anything(),
      expect.objectContaining({ timeout: 600000 }),
    );
  });
});
