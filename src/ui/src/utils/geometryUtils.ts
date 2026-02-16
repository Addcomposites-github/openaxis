import * as THREE from 'three';

/**
 * Calculate bounding box of geometry
 */
export function calculateBounds(geometry: THREE.BufferGeometry): THREE.Box3 {
  geometry.computeBoundingBox();
  return geometry.boundingBox || new THREE.Box3();
}

/**
 * Convert Z-up geometry (manufacturing convention) to Y-up (Three.js convention).
 * Applies rotateX(-PI/2) which maps: X→X, Y→-Z, Z→Y
 * After this, Y is up and the geometry is in Three.js convention.
 * NOTE: This mutates the geometry in place.
 */
export function convertZUpToYUp(geometry: THREE.BufferGeometry): void {
  geometry.rotateX(-Math.PI / 2);
}

/**
 * Get Y-offset needed to place geometry on build plate (Y-up convention).
 * Returns the offset to add to position.y to make min Y = 0.
 */
export function getPlateOffset(geometry: THREE.BufferGeometry): number {
  const bounds = calculateBounds(geometry);
  // In Y-up, the bottom of the part is min.y
  return -bounds.min.y;
}

/**
 * Center geometry on XZ plane (horizontal) and place bottom at Y=0 (on build plate).
 * Assumes geometry is ALREADY in Y-up convention (call convertZUpToYUp first if needed).
 * This modifies the geometry in place by translating vertices.
 *
 * All values are in millimeters (geometry vertices are mm).
 */
export function centerOnPlate(
  geometry: THREE.BufferGeometry,
  _plateSize: { x: number; y: number }
): { x: number; y: number; z: number } {
  // First convert from Z-up (STL/manufacturing) to Y-up (Three.js)
  convertZUpToYUp(geometry);

  const bounds = calculateBounds(geometry);
  const center = bounds.getCenter(new THREE.Vector3());

  // Center horizontally (XZ) and lift bottom to Y=0
  const offsetX = -center.x;
  const offsetZ = -center.z;
  const offsetY = -bounds.min.y; // Lift bottom of part to Y=0 (plate surface)

  // Apply translation to geometry vertices
  geometry.translate(offsetX, offsetY, offsetZ);

  // Recompute bounds after translation
  geometry.computeBoundingBox();

  // Return zero position since geometry is now centered and on plate
  return {
    x: 0,
    y: 0,
    z: 0
  };
}

/**
 * Check if geometry fits on build plate.
 * Geometry is in Y-up convention (after centerOnPlate).
 * plateSize is in mm: { x: widthX, y: depthZ }
 * In Y-up: X is width, Y is height, Z is depth
 */
export function checkBuildVolume(
  geometry: THREE.BufferGeometry,
  position: THREE.Vector3,
  plateSize: { x: number; y: number },
  maxHeight: number = 1000
): { valid: boolean; errors: string[] } {
  const bounds = calculateBounds(geometry).clone();
  bounds.translate(position);

  const errors: string[] = [];

  // Check X bounds (width)
  if (bounds.min.x < -plateSize.x / 2 || bounds.max.x > plateSize.x / 2) {
    errors.push(`Part exceeds build plate X dimension (${plateSize.x}mm)`);
  }

  // Check Z bounds (depth — was Y in manufacturing Z-up, now Z in Y-up)
  if (bounds.min.z < -plateSize.y / 2 || bounds.max.z > plateSize.y / 2) {
    errors.push(`Part exceeds build plate depth (${plateSize.y}mm)`);
  }

  // Check Y bounds (height — was Z in manufacturing, now Y in Y-up)
  if (bounds.min.y < -1) { // small tolerance
    errors.push('Part extends below build plate');
  }
  if (bounds.max.y > maxHeight) {
    errors.push(`Part exceeds maximum build height (${maxHeight}mm)`);
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Get geometry dimensions (after Y-up conversion)
 */
export function getDimensions(geometry: THREE.BufferGeometry): THREE.Vector3 {
  const bounds = calculateBounds(geometry);
  return bounds.getSize(new THREE.Vector3());
}

/**
 * Get geometry center point
 */
export function getCenter(geometry: THREE.BufferGeometry): THREE.Vector3 {
  const bounds = calculateBounds(geometry);
  return bounds.getCenter(new THREE.Vector3());
}

/**
 * Check if part is on build plate (Y position near 0 in Y-up convention)
 */
export function isOnPlate(
  geometry: THREE.BufferGeometry,
  position: THREE.Vector3,
  tolerance: number = 1.0  // mm
): boolean {
  const bounds = calculateBounds(geometry).clone();
  bounds.translate(position);
  return Math.abs(bounds.min.y) < tolerance;
}

/**
 * Get readable dimension string
 */
export function formatDimensions(dimensions: THREE.Vector3): string {
  return `${dimensions.x.toFixed(1)} × ${dimensions.y.toFixed(1)} × ${dimensions.z.toFixed(1)} mm`;
}

/**
 * Calculate volume of geometry (approximate using bounding box)
 */
export function calculateVolume(geometry: THREE.BufferGeometry): number {
  const dimensions = getDimensions(geometry);
  return dimensions.x * dimensions.y * dimensions.z;
}

/**
 * Compute the Y-offset needed to place a rotated part on the build plate.
 *
 * At import time, `centerOnPlate()` translates the geometry so that:
 *   - XZ center is at origin
 *   - Bottom is at Y = 0 (plate surface)
 *
 * So the local AABB is: min = [-dx/2, 0, -dz/2], max = [dx/2, dy, dz/2].
 *
 * When the part is rotated by Euler angles (rx, ry, rz), the axis-aligned
 * bounding box changes.  We use Three.js `Box3` + a rotation matrix to
 * compute the new AABB and return the Y-offset that places the bottom at Y=0.
 *
 * @param dimensions  Part dimensions {x, y, z} in mm (from import bounds)
 * @param rotation    Euler rotation {x, y, z} in radians
 * @returns  Y-offset (mm) so the bottom of the rotated part sits at Y=0
 */
export function computePlateOffsetAfterRotation(
  dimensions: { x: number; y: number; z: number },
  rotation: { x: number; y: number; z: number },
): number {
  const dx = dimensions.x;
  const dy = dimensions.y;
  const dz = dimensions.z;

  // The original AABB before rotation (centred XZ, bottom at Y=0)
  const box = new THREE.Box3(
    new THREE.Vector3(-dx / 2, 0, -dz / 2),
    new THREE.Vector3(dx / 2, dy, dz / 2),
  );

  // Build a rotation matrix from the Euler angles
  const euler = new THREE.Euler(rotation.x, rotation.y, rotation.z, 'XYZ');
  const mat = new THREE.Matrix4().makeRotationFromEuler(euler);

  // Three.js Box3 doesn't have applyMatrix4, so we manually transform
  // all 8 corners of the box and compute the new AABB.
  const corners = [
    new THREE.Vector3(box.min.x, box.min.y, box.min.z),
    new THREE.Vector3(box.min.x, box.min.y, box.max.z),
    new THREE.Vector3(box.min.x, box.max.y, box.min.z),
    new THREE.Vector3(box.min.x, box.max.y, box.max.z),
    new THREE.Vector3(box.max.x, box.min.y, box.min.z),
    new THREE.Vector3(box.max.x, box.min.y, box.max.z),
    new THREE.Vector3(box.max.x, box.max.y, box.min.z),
    new THREE.Vector3(box.max.x, box.max.y, box.max.z),
  ];

  let minY = Infinity;
  for (const corner of corners) {
    corner.applyMatrix4(mat);
    if (corner.y < minY) minY = corner.y;
  }

  // The offset to lift the bottom back to Y = 0
  return -minY;
}
