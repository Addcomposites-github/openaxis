/**
 * coordinateChain.test.ts — End-to-end coordinate transform verification.
 *
 * Tests the full chain: slicer Z-up mm → scene Y-up m → robot Z-up m
 *
 * This catches exactly the class of bugs we've hit:
 * - Sign errors in Y/Z mapping
 * - Missing negation in Y-up ↔ Z-up conversion
 * - Incorrect build plate / robot position offsets
 *
 * The coordinate conventions:
 *   Slicer (Z-up, mm):  X=right, Y=depth, Z=height
 *   Scene  (Y-up, m):   X=right, Y=height, Z=-depth
 *   Robot  (Z-up, m):   X=forward, Y=left, Z=height
 */

import { describe, it, expect } from 'vitest';
import {
  mfgToScene,
  toolpathPointToScene,
  waypointToRobotFrame,
} from '../units';

// ─── Default cell layout values (must match SceneManager defaults) ─────
const BUILD_PLATE_ORIGIN: [number, number, number] = [2.0, 0.05, 0.0];
const ROBOT_POSITION: [number, number, number] = [0.4, 0, 0.1];

describe('mfgToScene — Z-up mm → Y-up m', () => {
  it('X axis preserved (scaled)', () => {
    const [sx, sy, sz] = mfgToScene([1000, 0, 0]);
    expect(sx).toBeCloseTo(1.0);
    expect(sy).toBeCloseTo(0);
    expect(sz).toBeCloseTo(0);
  });

  it('Z-up → Y-up (height maps to Y)', () => {
    const [sx, sy, sz] = mfgToScene([0, 0, 500]);
    expect(sx).toBeCloseTo(0);
    expect(sy).toBeCloseTo(0.5);  // Z_slicer → Y_scene
    expect(sz).toBeCloseTo(0);
  });

  it('Y → -Z (depth maps to negative Z)', () => {
    const [sx, sy, sz] = mfgToScene([0, 300, 0]);
    expect(sx).toBeCloseTo(0);
    expect(sy).toBeCloseTo(0);
    expect(sz).toBeCloseTo(-0.3);  // Y_slicer → -Z_scene
  });

  it('combined point transforms correctly', () => {
    const [sx, sy, sz] = mfgToScene([150, 200, 100]);
    expect(sx).toBeCloseTo(0.15);
    expect(sy).toBeCloseTo(0.1);   // Z=100 → Y=0.1
    expect(sz).toBeCloseTo(-0.2);  // Y=200 → Z=-0.2
  });
});

describe('waypointToRobotFrame — full chain', () => {
  it('slicer origin maps to correct robot-frame position', () => {
    // Slicer [0,0,0] → on the build plate surface
    const [rx, ry, rz] = waypointToRobotFrame(
      [0, 0, 0],
      BUILD_PLATE_ORIGIN,
      ROBOT_POSITION,
    );

    // Scene position = buildPlate + toolpathPointToScene([0,0,0])
    // = [2.0, 0.05, 0] + [0, 0, 0] = [2.0, 0.05, 0]
    // Relative to robot: [2.0-0.4, 0.05-0, 0-0.1] = [1.6, 0.05, -0.1]
    // Scene→Robot: [x, -z, y] = [1.6, 0.1, 0.05]
    expect(rx).toBeCloseTo(1.6, 4);
    expect(ry).toBeCloseTo(0.1, 4);
    expect(rz).toBeCloseTo(0.05, 4);
  });

  it('slicer point at [150, 0, 100] maps correctly', () => {
    // Slicer [150, 0, 100] → part position 150mm right, 100mm up
    const [rx, ry, rz] = waypointToRobotFrame(
      [150, 0, 100],
      BUILD_PLATE_ORIGIN,
      ROBOT_POSITION,
    );

    // Scene: buildPlate + toolpathPointToScene([150,0,100])
    //   tpScene = [0.15, 0.1, 0]
    //   scenePos = [2.15, 0.15, 0]
    // Relative to robot: [2.15-0.4, 0.15-0, 0-0.1] = [1.75, 0.15, -0.1]
    // Scene→Robot: [1.75, 0.1, 0.15]
    expect(rx).toBeCloseTo(1.75, 4);
    expect(ry).toBeCloseTo(0.1, 4);
    expect(rz).toBeCloseTo(0.15, 4);
  });

  it('slicer depth offset (Y in slicer) maps to robot Y', () => {
    // Slicer [0, 100, 0] → 100mm depth offset
    const [rx, ry, rz] = waypointToRobotFrame(
      [0, 100, 0],
      BUILD_PLATE_ORIGIN,
      ROBOT_POSITION,
    );

    // Scene: buildPlate + toolpathPointToScene([0,100,0])
    //   tpScene = [0, 0, -0.1]
    //   scenePos = [2.0, 0.05, -0.1]
    // Relative to robot: [1.6, 0.05, -0.2]
    // Scene→Robot: [1.6, 0.2, 0.05]
    expect(rx).toBeCloseTo(1.6, 4);
    expect(ry).toBeCloseTo(0.2, 4);  // Depth maps to robot Y
    expect(rz).toBeCloseTo(0.05, 4);
  });

  it('CRITICAL: negative depth offset sign is preserved', () => {
    // This is the exact bug we fixed (store_z negation)
    // Slicer [0, -100, 0] → -100mm depth offset
    const [rx, ry, rz] = waypointToRobotFrame(
      [0, -100, 0],
      BUILD_PLATE_ORIGIN,
      ROBOT_POSITION,
    );

    // tpScene = [0, 0, 0.1] (note: -(-100*0.001) = +0.1)
    // scenePos = [2.0, 0.05, 0.1]
    // Relative: [1.6, 0.05, 0.0]
    // Robot: [1.6, 0.0, 0.05]
    expect(rx).toBeCloseTo(1.6, 4);
    expect(ry).toBeCloseTo(0.0, 4);  // Negative depth → 0 robot Y
    expect(rz).toBeCloseTo(0.05, 4);
  });
});

describe('round-trip consistency', () => {
  it('toolpathPointToScene matches mfgToScene', () => {
    const points: [number, number, number][] = [
      [0, 0, 0],
      [100, 200, 300],
      [-50, 150, 75],
      [1000, 0, 0],
      [0, 1000, 0],
      [0, 0, 1000],
    ];

    for (const p of points) {
      const a = mfgToScene(p);
      const b = toolpathPointToScene(p);
      expect(a[0]).toBeCloseTo(b[0], 10);
      expect(a[1]).toBeCloseTo(b[1], 10);
      expect(a[2]).toBeCloseTo(b[2], 10);
    }
  });
});

describe('part offset integration', () => {
  it('slicer point + part offset produces correct robot-frame position', () => {
    // Simulates the actual IK computation in SimulationPanel:
    // partOffsetZUp = [store_x, -store_z, store_y] (the bug we fixed)
    // slicerPosWithOffset = slicerPos + partOffset

    const storePosition = { x: 150, y: 0, z: 100 };

    // Y-up → Z-up conversion (the fixed version with negation)
    const partOffsetZUp: [number, number, number] = [
      storePosition.x,
      -storePosition.z,  // NEGATED — this is the fix
      storePosition.y,
    ];

    // Slicer point at origin + part offset
    const slicerPosWithOffset: [number, number, number] = [
      0 + partOffsetZUp[0],
      0 + partOffsetZUp[1],
      0 + partOffsetZUp[2],
    ];

    const robotPos = waypointToRobotFrame(
      slicerPosWithOffset,
      BUILD_PLATE_ORIGIN,
      ROBOT_POSITION,
    );

    // Also compute scene position of the green TCP sphere
    // It lives in the buildPlateOrigin group, offset by toolpathPointToScene(slicerPosWithOffset)
    const sceneOffset = toolpathPointToScene(slicerPosWithOffset);
    const greenSphereWorld = [
      BUILD_PLATE_ORIGIN[0] + sceneOffset[0],
      BUILD_PLATE_ORIGIN[1] + sceneOffset[1],
      BUILD_PLATE_ORIGIN[2] + sceneOffset[2],
    ];

    // Robot FK world = robotPosition + FK_scene
    // FK is in Z-up meters, scene wrapper rotates -90° X: [rx, ry, rz]_Zup → [rx, rz, -ry]_scene
    // So FK_scene = [robotX_Zup, robotZ_Zup, -robotY_Zup]
    const fkScene = [robotPos[0], robotPos[2], -robotPos[1]];
    const fkWorld = [
      ROBOT_POSITION[0] + fkScene[0],
      ROBOT_POSITION[1] + fkScene[1],
      ROBOT_POSITION[2] + fkScene[2],
    ];

    // The key assertion: green sphere and FK world position must match
    expect(fkWorld[0]).toBeCloseTo(greenSphereWorld[0], 4);
    expect(fkWorld[1]).toBeCloseTo(greenSphereWorld[1], 4);
    expect(fkWorld[2]).toBeCloseTo(greenSphereWorld[2], 4);
  });

  it('without part offset negation fix, positions would NOT match', () => {
    // This test documents the old bug: if we DON'T negate store_z,
    // the positions diverge by 200mm
    const storePosition = { x: 150, y: 0, z: 100 };

    // BUG version (no negation)
    const buggyOffset: [number, number, number] = [
      storePosition.x,
      storePosition.z,  // NOT negated — this was the bug
      storePosition.y,
    ];

    // Fixed version
    const fixedOffset: [number, number, number] = [
      storePosition.x,
      -storePosition.z,  // Negated — the fix
      storePosition.y,
    ];

    const buggyRobot = waypointToRobotFrame(buggyOffset, BUILD_PLATE_ORIGIN, ROBOT_POSITION);
    const fixedRobot = waypointToRobotFrame(fixedOffset, BUILD_PLATE_ORIGIN, ROBOT_POSITION);

    // Buggy Y=+100 vs Fixed Y=-100 → slicer Y differs by 200mm
    // Slicer Y → scene -Z → robot -Y, so robot Y differs by 0.2m
    const yDiff = Math.abs(buggyRobot[1] - fixedRobot[1]);
    expect(yDiff).toBeCloseTo(0.2, 2); // 200mm difference — the exact bug we saw
  });
});
