"""
Demonstration of OpenAxis slicing capabilities.

This script shows how to:
1. Load geometry
2. Slice into layers
3. Generate toolpath
4. Export G-code
"""

from pathlib import Path

from openaxis.core.geometry import GeometryLoader
from openaxis.slicing.planar_slicer import PlanarSlicer
from openaxis.slicing.gcode import GCodeGenerator, GCodeConfig, GCodeFlavor
from openaxis.slicing.toolpath import InfillPattern


def main():
    """Run slicing demonstration."""
    print("=" * 60)
    print("OpenAxis Slicing Demo")
    print("=" * 60)

    # Get the example file path
    example_dir = Path(__file__).parent
    stl_file = example_dir / "simple_cube.stl"
    output_gcode = example_dir / "cube_toolpath.gcode"

    # 1. Load geometry
    print(f"\n1. Loading STL file: {stl_file.name}")
    mesh = GeometryLoader.load(stl_file)
    print(f"   [OK] Loaded mesh with {mesh.number_of_vertices()} vertices")
    print(f"   [OK] Loaded mesh with {mesh.number_of_faces()} faces")

    # 2. Configure slicer
    print("\n2. Configuring slicer")
    slicer = PlanarSlicer(
        layer_height=0.5,  # 0.5mm layers
        extrusion_width=0.8,  # 0.8mm bead width
        wall_count=2,  # 2 perimeter walls
        infill_density=0.2,  # 20% infill
        infill_pattern=InfillPattern.LINES,  # Simple line infill
    )
    print(f"   [OK] Layer height: {slicer.layer_height} mm")
    print(f"   [OK] Extrusion width: {slicer.extrusion_width} mm")
    print(f"   [OK] Wall count: {slicer.wall_count}")
    print(f"   [OK] Infill density: {slicer.infill_density * 100}%")

    # 3. Slice the mesh
    print("\n3. Slicing mesh into layers")
    toolpath = slicer.slice(mesh)
    print(f"   [OK] Generated {toolpath.total_layers} layers")
    print(f"   [OK] Created {len(toolpath.segments)} toolpath segments")
    print(f"   [OK] Total toolpath length: {toolpath.get_total_length():.2f} mm")
    print(f"   [OK] Estimated print time: {toolpath.get_build_time_estimate():.1f} seconds")

    # 4. Show toolpath statistics
    print("\n4. Toolpath statistics")
    perimeter_segs = toolpath.get_segments_by_type(
        toolpath.segments[0].type.__class__.PERIMETER
    )
    print(f"   [OK] Perimeter segments: {len(perimeter_segs)}")

    # Show layer breakdown
    print(f"\n   Layer breakdown:")
    for layer_idx in range(min(5, toolpath.total_layers)):  # Show first 5 layers
        layer_segs = toolpath.get_segments_by_layer(layer_idx)
        layer_length = sum(seg.get_length() for seg in layer_segs)
        print(f"     Layer {layer_idx}: {len(layer_segs)} segments, {layer_length:.2f} mm")

    # 5. Generate G-code
    print("\n5. Generating G-code")
    gcode_config = GCodeConfig(
        flavor=GCodeFlavor.GENERIC,
        use_relative_extrusion=True,
        feedrate_multiplier=1.0,
        extrusion_multiplier=1.0,
    )
    generator = GCodeGenerator(gcode_config)
    gcode = generator.generate(toolpath, output_gcode)

    print(f"   [OK] Generated {len(gcode.splitlines())} lines of G-code")
    print(f"   [OK] Saved to: {output_gcode.name}")

    # 6. Show G-code preview
    print("\n6. G-code preview (first 20 lines)")
    print("   " + "-" * 56)
    for i, line in enumerate(gcode.splitlines()[:20]):
        print(f"   {line}")
    print("   " + "-" * 56)
    print(f"   ... ({len(gcode.splitlines()) - 20} more lines)")

    # 7. Bounds information
    print("\n7. Toolpath bounds")
    try:
        min_pt, max_pt = toolpath.get_bounds()
        print(f"   [OK] Min: ({min_pt.x:.2f}, {min_pt.y:.2f}, {min_pt.z:.2f})")
        print(f"   [OK] Max: ({max_pt.x:.2f}, {max_pt.y:.2f}, {max_pt.z:.2f})")
        print(f"   [OK] Build volume: {max_pt.x - min_pt.x:.2f} x {max_pt.y - min_pt.y:.2f} x {max_pt.z - min_pt.z:.2f} mm")
    except ValueError as e:
        print(f"   [INFO] Could not calculate bounds: {e}")

    print("\n" + "=" * 60)
    print("[SUCCESS] Slicing demo completed successfully!")
    print("=" * 60)
    print(f"\nGenerated files:")
    print(f"  - {output_gcode}")
    print(f"\nNext steps:")
    print(f"  - Visualize toolpath in a G-code viewer")
    print(f"  - Simulate with pybullet (Phase 1.5)")
    print(f"  - Send to robot controller (Phase 2)")


if __name__ == "__main__":
    main()
