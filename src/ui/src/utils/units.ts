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

/**
 * Convert a toolpath waypoint position (mm, Z-up, relative to build plate)
 * to the robot's IK frame (meters, Z-up, robot base frame).
 *
 * Transform chain:
 * 1. Slicer mm Z-up → Scene meters Y-up (add build plate offset)
 * 2. Scene Y-up → Robot base Z-up (inverse of robot placement rotation)
 *
 * The robot URDF is Z-up. In the scene, the robot wrapper has rotation
 * [-90 deg, 0, 0] around X to convert from Z-up to Y-up. So the inverse
 * (scene Y-up → robot Z-up) is: [x, y, z]_scene → [x, -z, y]_robot.
 *
 * @param slicerPos    - [x, y, z] in mm, Z-up, relative to build plate
 * @param buildPlateOrigin - Build plate position in scene space [x, y, z] Y-up meters
 * @param robotPosition    - Robot base position in scene space [x, y, z] Y-up meters
 * @returns [x, y, z] in meters, Z-up, robot base frame
 */
export function waypointToRobotFrame(
  slicerPos: [number, number, number],
  buildPlateOrigin: [number, number, number],
  robotPosition: [number, number, number] = [0, 0, 0],
): [number, number, number] {
  // Step 1: slicer (mm, Z-up) → scene (meters, Y-up) world position
  // Uses the same transform as toolpathPointToScene, then adds build plate offset
  const sceneX = buildPlateOrigin[0] + slicerPos[0] * MM_TO_M;
  const sceneY = buildPlateOrigin[1] + slicerPos[2] * MM_TO_M;    // slicer Z → scene Y
  const sceneZ = buildPlateOrigin[2] + (-slicerPos[1]) * MM_TO_M; // slicer Y → scene -Z

  // Step 2: scene (Y-up) → robot frame (Z-up)
  // Subtract robot position, then apply inverse rotation of [-90deg, 0, 0] around X
  // Inverse: [x, y, z]_scene → [x, -z, y]_robot
  const dx = sceneX - robotPosition[0];
  const dy = sceneY - robotPosition[1];
  const dz = sceneZ - robotPosition[2];

  const robotX = dx;
  const robotY = -dz;
  const robotZ = dy;

  return [robotX, robotY, robotZ];
}
