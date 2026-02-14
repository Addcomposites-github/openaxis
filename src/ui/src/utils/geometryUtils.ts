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
