import { describe, it, expect } from 'vitest';
import { MM_TO_M, M_TO_MM, mfgToScene, toolpathPointToScene, mmToM } from '../units';

describe('units.ts — conversion constants', () => {
  it('MM_TO_M is 0.001', () => {
    expect(MM_TO_M).toBe(0.001);
  });

  it('M_TO_MM is 1000', () => {
    expect(M_TO_MM).toBe(1000);
  });

  it('round-trip: mm → m → mm', () => {
    const mm = 1234.5;
    expect(mm * MM_TO_M * M_TO_MM).toBeCloseTo(mm);
  });
});

describe('mmToM', () => {
  it('converts 1000mm to 1m', () => {
    expect(mmToM(1000)).toBe(1);
  });

  it('converts 0 to 0', () => {
    expect(mmToM(0)).toBe(0);
  });

  it('converts 50mm to 0.05m', () => {
    expect(mmToM(50)).toBeCloseTo(0.05);
  });
});

describe('mfgToScene — Z-up mm → Y-up meters', () => {
  it('converts origin to origin', () => {
    expect(mfgToScene([0, 0, 0])).toEqual([0, 0, -0]);
  });

  it('converts X-axis correctly (X stays X)', () => {
    const result = mfgToScene([1000, 0, 0]);
    expect(result[0]).toBeCloseTo(1); // 1000mm → 1m
    expect(result[1]).toBeCloseTo(0);
    expect(result[2]).toBeCloseTo(0);
  });

  it('converts Y-axis to -Z (depth)', () => {
    const result = mfgToScene([0, 1000, 0]);
    expect(result[0]).toBeCloseTo(0);
    expect(result[1]).toBeCloseTo(0);
    expect(result[2]).toBeCloseTo(-1); // Y_mfg → -Z_scene
  });

  it('converts Z-axis to Y (height)', () => {
    const result = mfgToScene([0, 0, 1000]);
    expect(result[0]).toBeCloseTo(0);
    expect(result[1]).toBeCloseTo(1); // Z_mfg → Y_scene (up)
    expect(result[2]).toBeCloseTo(0);
  });

  it('converts a general point', () => {
    const result = mfgToScene([100, 200, 300]);
    expect(result[0]).toBeCloseTo(0.1);  // X: 100mm → 0.1m
    expect(result[1]).toBeCloseTo(0.3);  // Z→Y: 300mm → 0.3m
    expect(result[2]).toBeCloseTo(-0.2); // Y→-Z: 200mm → -0.2m
  });
});

describe('toolpathPointToScene', () => {
  it('is equivalent to mfgToScene', () => {
    const point: [number, number, number] = [150, 250, 75];
    expect(toolpathPointToScene(point)).toEqual(mfgToScene(point));
  });
});
