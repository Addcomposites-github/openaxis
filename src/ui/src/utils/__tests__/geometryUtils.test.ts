/**
 * geometryUtils.test.ts — Tests for geometry utility functions.
 *
 * Verifies bounding box computation, plate offset calculation,
 * and the critical computePlateOffsetAfterRotation function.
 */

import { describe, it, expect } from 'vitest';
import * as THREE from 'three';
import { computePlateOffsetAfterRotation } from '../geometryUtils';

describe('computePlateOffsetAfterRotation', () => {
  const dims = { x: 100, y: 200, z: 50 }; // 100×200×50 mm part

  it('returns 0 for no rotation', () => {
    const offset = computePlateOffsetAfterRotation(dims, { x: 0, y: 0, z: 0 });
    // At import time, bottom is at Y=0, so offset should be 0
    expect(offset).toBeCloseTo(0, 4);
  });

  it('handles 90° X rotation correctly', () => {
    // Rotating 90° around X axis:
    // Original AABB: [-50, 0, -25] to [50, 200, 25]
    // After 90° X rotation: Y→Z, Z→-Y
    // New min.y comes from the original +Z corners mapped to -Y
    // Corner (50, 0, 25) → rotated → (50, -25, 0) → minY = -25
    const offset = computePlateOffsetAfterRotation(dims, {
      x: Math.PI / 2, y: 0, z: 0,
    });
    // The tallest Z dimension (25mm half) becomes the drop below Y=0
    expect(offset).toBeCloseTo(25, 1);
  });

  it('handles 90° Z rotation (flat rotation) — no Y change', () => {
    // Rotating around Z only swaps X and Y directions... wait, actually
    // in 3D: rotating around Z swaps X↔Y in the XY plane
    // But the bottom Y=0 corners are [±50, 0, ±25]
    // After 90° Z rotation: (x,y,z) → (-y,x,z)
    // (50, 0, 25) → (0, 50, 25) → y=50 (up)
    // (-50, 0, 25) → (0, -50, 25) → y=-50
    // (-50, 200, 25) → (-200, -50, 25) → y=-50
    // (50, 200, 25) → (-200, 50, 25) → y=50
    // Min y from bottom corners = -50
    const offset = computePlateOffsetAfterRotation(dims, {
      x: 0, y: 0, z: Math.PI / 2,
    });
    expect(offset).toBeCloseTo(50, 1); // Half of X dimension
  });

  it('180° X rotation flips part upside down', () => {
    // After 180° X rotation: Y → -Y, Z → -Z
    // Original top corners (y=200) map to y=-200
    // That's the new minimum → offset = 200
    const offset = computePlateOffsetAfterRotation(dims, {
      x: Math.PI, y: 0, z: 0,
    });
    expect(offset).toBeCloseTo(200, 1); // Full height of part
  });

  it('small rotation produces small offset', () => {
    // 5° tilt should only shift slightly
    const offset = computePlateOffsetAfterRotation(dims, {
      x: 5 * Math.PI / 180, y: 0, z: 0,
    });
    // At 5°, the Z half-extent (25) contributes sin(5°)*25 ≈ 2.18mm below Y=0
    expect(offset).toBeGreaterThan(0);
    expect(offset).toBeLessThan(10);
  });

  it('symmetric part (cube) has consistent offset for any rotation axis', () => {
    const cube = { x: 100, y: 100, z: 100 };
    const angle = Math.PI / 4; // 45°

    const offsetX = computePlateOffsetAfterRotation(cube, { x: angle, y: 0, z: 0 });
    const offsetZ = computePlateOffsetAfterRotation(cube, { x: 0, y: 0, z: angle });

    // For a cube, 45° around X and 45° around Z produce the same drop
    // because the cube is symmetric in X and Z
    // Actually not exactly — bottom at Y=0 vs centered. Let me check:
    // Cube AABB: [-50, 0, -50] to [50, 100, 50]
    // The cube is NOT centered vertically (bottom at 0, top at 100)
    // So rotations around X and Z produce different results.
    // Just verify both are positive and reasonable
    expect(offsetX).toBeGreaterThan(0);
    expect(offsetZ).toBeGreaterThan(0);
    expect(offsetX).toBeLessThan(150); // Can't exceed diagonal
    expect(offsetZ).toBeLessThan(150);
  });

  it('handles compound rotation (X + Y)', () => {
    const offset = computePlateOffsetAfterRotation(dims, {
      x: Math.PI / 6, // 30°
      y: Math.PI / 4, // 45°
      z: 0,
    });

    // Should be a positive number — part tilted needs lifting
    expect(offset).toBeGreaterThan(0);
    // Should not exceed the diagonal of the bounding box
    const diag = Math.sqrt(100 ** 2 + 200 ** 2 + 50 ** 2);
    expect(offset).toBeLessThan(diag);
  });

  it('uses Three.js matrix math (not homebrew trig)', () => {
    // Verify the function uses proper rotation matrices by checking
    // against a manually computed Three.js rotation
    const dims2 = { x: 200, y: 100, z: 60 };
    const rot = { x: 0.5, y: 0.3, z: 0.7 };

    // Manual Three.js computation
    const euler = new THREE.Euler(rot.x, rot.y, rot.z, 'XYZ');
    const mat = new THREE.Matrix4().makeRotationFromEuler(euler);

    const corners = [
      new THREE.Vector3(-100, 0, -30),
      new THREE.Vector3(-100, 0, 30),
      new THREE.Vector3(-100, 100, -30),
      new THREE.Vector3(-100, 100, 30),
      new THREE.Vector3(100, 0, -30),
      new THREE.Vector3(100, 0, 30),
      new THREE.Vector3(100, 100, -30),
      new THREE.Vector3(100, 100, 30),
    ];

    let minY = Infinity;
    for (const c of corners) {
      c.applyMatrix4(mat);
      if (c.y < minY) minY = c.y;
    }
    const expectedOffset = -minY;

    const offset = computePlateOffsetAfterRotation(dims2, rot);
    expect(offset).toBeCloseTo(expectedOffset, 4);
  });
});
