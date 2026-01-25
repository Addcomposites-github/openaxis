"""
Demonstration of OpenAxis geometry capabilities.

This script shows how to:
1. Load STL files
2. Compute bounding boxes
3. Apply transformations
4. Save modified geometry
"""

import math
from pathlib import Path

from openaxis.core.geometry import (
    BoundingBox,
    GeometryLoader,
    TransformationUtilities,
)
from compas.geometry import Vector


def main():
    """Run geometry demonstration."""
    print("=" * 60)
    print("OpenAxis Geometry Demo")
    print("=" * 60)

    # Get the example file path
    example_dir = Path(__file__).parent
    stl_file = example_dir / "simple_cube.stl"

    # 1. Load STL file
    print(f"\n1. Loading STL file: {stl_file.name}")
    mesh = GeometryLoader.load(stl_file)
    print(f"   [OK] Loaded mesh with {mesh.number_of_vertices()} vertices")
    print(f"   [OK] Loaded mesh with {mesh.number_of_faces()} faces")

    # 2. Compute bounding box
    print("\n2. Computing bounding box")
    bbox = BoundingBox.from_mesh(mesh)
    dimensions = BoundingBox.get_dimensions(bbox)
    center = BoundingBox.get_center(bbox)

    print(f"   [OK] Bounding box dimensions: {dimensions[0]:.2f} x {dimensions[1]:.2f} x {dimensions[2]:.2f} mm")
    print(f"   [OK] Center point: ({center.x:.2f}, {center.y:.2f}, {center.z:.2f})")

    # 3. Apply transformations
    print("\n3. Applying transformations")

    # Translate
    print("   - Translating by (5, 0, 0)")
    translated = TransformationUtilities.translate(mesh, [5, 0, 0])
    bbox_translated = BoundingBox.from_mesh(translated)
    center_translated = BoundingBox.get_center(bbox_translated)
    print(f"     New center: ({center_translated.x:.2f}, {center_translated.y:.2f}, {center_translated.z:.2f})")

    # Rotate
    print("   - Rotating 45 degrees around Z-axis")
    rotated = TransformationUtilities.rotate(
        mesh,
        angle=math.pi / 4,  # 45 degrees
        axis=Vector(0, 0, 1)
    )
    print(f"     Rotated mesh has {rotated.number_of_vertices()} vertices")

    # Scale
    print("   - Scaling by factor 2.0")
    scaled = TransformationUtilities.scale(mesh, 2.0)
    bbox_scaled = BoundingBox.from_mesh(scaled)
    dims_scaled = BoundingBox.get_dimensions(bbox_scaled)
    print(f"     New dimensions: {dims_scaled[0]:.2f} x {dims_scaled[1]:.2f} x {dims_scaled[2]:.2f} mm")

    # 4. Save transformed geometry
    print("\n4. Saving transformed geometry")
    output_file = example_dir / "transformed_cube.stl"
    GeometryLoader.save(scaled, output_file)
    print(f"   [OK] Saved to: {output_file.name}")

    # 5. Verify by reloading
    print("\n5. Verifying saved file")
    reloaded = GeometryLoader.load(output_file)
    bbox_reloaded = BoundingBox.from_mesh(reloaded)
    dims_reloaded = BoundingBox.get_dimensions(bbox_reloaded)
    print(f"   [OK] Reloaded dimensions: {dims_reloaded[0]:.2f} x {dims_reloaded[1]:.2f} x {dims_reloaded[2]:.2f} mm")

    print("\n" + "=" * 60)
    print("[SUCCESS] Geometry demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
