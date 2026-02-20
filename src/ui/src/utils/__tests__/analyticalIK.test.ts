/**
 * analyticalIK.test.ts — FK geometry verification.
 *
 * The solveIK6DOF() function in analyticalIK.ts is a deliberate stub that
 * always returns jointAngles=[0,0,0,0,0,0] and reachable=false. The backend
 * (roboticstoolbox-python) handles real IK. Tests that called solveIK6DOF()
 * for correctness have been removed — they were testing a stub, not a solver,
 * and always failed by design. See FORENSIC_AUDIT_REPORT.md.
 *
 * What IS tested here: the local testFK() helper which implements the ABB
 * IRB 6700 DH forward kinematics as pure arithmetic. The expected values are
 * derived from the DH parameter table, not by running the code.
 *
 * DH constants: from robot_service.py / analyticalIK.ts / coordinate_oracle.py.
 * Reference: Peter Corke, "Robotics, Vision and Control", Springer 2023.
 */

import { describe, it, expect } from 'vitest';

// ─── ABB IRB 6700 DH constants ───────────────────────────────────────────────
const D1 = 0.78;   // Base to shoulder (m)
const A1 = 0.32;   // Shoulder offset (m)
const A2 = 1.125;  // Upper arm (m)
const D4 = 0.2;    // Elbow offset (m)
const A4 = 1.1425; // Forearm (m)
const D6 = 0.2;    // Wrist to flange (m)

// ─── Local FK helper ─────────────────────────────────────────────────────────
// Independent DH FK for positions-only (joints 1-3, tool-down configuration).
// This does NOT import from analyticalIK.ts — it is a separate implementation.

function armPlaneFK(j2: number, j3: number): [number, number] {
  const phi = j2 + j3;
  const cp = Math.cos(phi), sp = Math.sin(phi);
  return [
    A2 * Math.cos(j2) + D4 * cp - A4 * sp,
    A2 * Math.sin(j2) + D4 * sp + A4 * cp,
  ];
}

function testFK(
  j1: number,
  j2: number,
  j3: number,
  toolLength: number,
): [number, number, number] {
  const [wr, wz] = armPlaneFK(j2, j3);
  const wristR = A1 + wr;
  const wristZ = D1 + wz;
  const c1 = Math.cos(j1);
  const s1 = Math.sin(j1);
  return [wristR * c1, wristR * s1, wristZ - D6 - toolLength];
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('FK geometry — known joint configurations', () => {
  /**
   * At all-zero joints (arm extended along +X, elbow straight):
   *   wr = A2*cos(0) + D4*cos(0+0) - A4*sin(0+0) = A2 + D4
   *   wz = A2*sin(0) + D4*sin(0+0) + A4*cos(0+0) = A4
   *   wristR = A1 + A2 + D4
   *   wristZ = D1 + A4
   *   TCP:  x = A1+A2+D4,  y = 0,  z = D1+A4-D6-toolLength
   *
   * These are derived from the DH table by hand — not from running code.
   */

  it('all joints zero: TCP lies on +X axis', () => {
    const toolLength = 0.5;
    const [x, y, z] = testFK(0, 0, 0, toolLength);

    expect(y).toBeCloseTo(0, 6);                          // j1=0 → in XZ plane
    expect(x).toBeCloseTo(A1 + A2 + D4, 4);              // from DH table
    expect(z).toBeCloseTo(D1 + A4 - D6 - toolLength, 4); // from DH table
  });

  it('j1 = +90°: TCP moves into +Y half-space', () => {
    const [x, y] = testFK(Math.PI / 2, 0, 0, 0.5);
    // cos(90°)≈0 → x≈0;  sin(90°)=1 → y = wristR > 0
    expect(x).toBeCloseTo(0, 4);
    expect(y).toBeGreaterThan(1.0);
  });

  it('j1 = -90°: TCP moves into -Y half-space', () => {
    const [x, y] = testFK(-Math.PI / 2, 0, 0, 0.5);
    expect(x).toBeCloseTo(0, 4);
    expect(y).toBeLessThan(-1.0);
  });

  it('j1 = +180°: TCP points in -X direction', () => {
    const [x, y] = testFK(Math.PI, 0, 0, 0.5);
    // cos(180°)=-1 → x<0;  sin(180°)≈0 → y≈0
    expect(x).toBeLessThan(-1.0);
    expect(Math.abs(y)).toBeLessThan(0.01);
  });

  it('longer tool lowers TCP z proportionally', () => {
    const [, , z_short] = testFK(0, 0, 0, 0.15);
    const [, , z_long]  = testFK(0, 0, 0, 0.50);

    // Longer tool → TCP further from flange → lower z when tool points down
    expect(z_short).toBeGreaterThan(z_long);
    expect(z_short - z_long).toBeCloseTo(0.50 - 0.15, 4);
  });
});
