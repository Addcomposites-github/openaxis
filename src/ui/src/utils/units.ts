/**
 * Unit conversion utilities for OpenAxis.
 *
 * Convention:
 * - workspaceStore values are in MILLIMETERS (manufacturing standard)
 * - Three.js scene rendering is in METERS (URDF standard)
 * - Manufacturing convention: Z-up
 * - Three.js convention: Y-up
 *
 * Conversion happens ONLY at the render boundary.
 */

export const MM_TO_M = 0.001;
export const M_TO_MM = 1000;

/**
 * Convert a manufacturing point [x_mm, y_mm, z_mm] (Z-up, mm)
 * to scene coordinates [x_m, height_m, -depth_m] (Y-up, meters).
 */
export function mfgToScene(p: [number, number, number]): [number, number, number] {
  return [p[0] * MM_TO_M, p[2] * MM_TO_M, -p[1] * MM_TO_M];
}

/**
 * Convert a toolpath point [x, y, z] (Z-up mm from slicer)
 * to scene coordinates (Y-up meters).
 * Same transform as mfgToScene but named for clarity.
 */
export function toolpathPointToScene(p: [number, number, number]): [number, number, number] {
  return [p[0] * MM_TO_M, p[2] * MM_TO_M, -p[1] * MM_TO_M];
}

/**
 * Convert mm dimension value to meters for scene rendering.
 */
export function mmToM(mm: number): number {
  return mm * MM_TO_M;
}
