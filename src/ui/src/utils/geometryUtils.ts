import * as THREE from 'three';

/**
 * Calculate bounding box of geometry
 */
export function calculateBounds(geometry: THREE.BufferGeometry): THREE.Box3 {
  geometry.computeBoundingBox();
  return geometry.boundingBox || new THREE.Box3();
}

/**
 * Get Z-offset needed to place geometry on build plate
 * Returns the offset to add to position.z to make min Z = 0
 */
export function getPlateOffset(geometry: THREE.BufferGeometry): number {
  const bounds = calculateBounds(geometry);
  const minZ = bounds.min.z;
  return -minZ;  // Offset to bring bottom to Z=0
}

/**
 * Center geometry on XY plane and place on build plate at Z=0
 */
export function centerOnPlate(
  geometry: THREE.BufferGeometry,
  plateSize: { x: number; y: number }
): { x: number; y: number; z: number } {
  const bounds = calculateBounds(geometry);
  const center = bounds.getCenter(new THREE.Vector3());

  return {
    x: -center.x,  // Offset to center X
    y: -center.y,  // Offset to center Y
    z: getPlateOffset(geometry)  // Offset to place on plate
  };
}

/**
 * Check if geometry fits on build plate
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

  // Check X bounds
  if (bounds.min.x < -plateSize.x / 2 || bounds.max.x > plateSize.x / 2) {
    errors.push(`Part exceeds build plate X dimension (${plateSize.x}mm)`);
  }

  // Check Y bounds
  if (bounds.min.y < -plateSize.y / 2 || bounds.max.y > plateSize.y / 2) {
    errors.push(`Part exceeds build plate Y dimension (${plateSize.y}mm)`);
  }

  // Check Z bounds
  if (bounds.min.z < 0) {
    errors.push('Part extends below build plate');
  }
  if (bounds.max.z > maxHeight) {
    errors.push(`Part exceeds maximum build height (${maxHeight}mm)`);
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Get geometry dimensions
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
 * Check if part is on build plate (Z position near 0)
 */
export function isOnPlate(
  geometry: THREE.BufferGeometry,
  position: THREE.Vector3,
  tolerance: number = 1.0  // mm
): boolean {
  const bounds = calculateBounds(geometry).clone();
  bounds.translate(position);
  return Math.abs(bounds.min.z) < tolerance;
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
