"""
Integrated demonstration: Slicing + Simulation Visualization

This demo shows the complete workflow:
1. Load geometry
2. Slice into toolpath
3. Visualize in PyBullet simulation
4. Animate toolpath execution
"""

import time
from pathlib import Path

import pybullet as p

from openaxis.core.geometry import GeometryLoader
from openaxis.simulation.environment import SimulationEnvironment, SimulationMode
from openaxis.slicing.planar_slicer import PlanarSlicer
from openaxis.slicing.toolpath import InfillPattern


def visualize_toolpath_in_simulation(toolpath, sim_env, animate=True):
    """
    Visualize a toolpath in the PyBullet simulation.

    Args:
        toolpath: Toolpath object to visualize
        sim_env: SimulationEnvironment instance
        animate: Whether to animate the toolpath execution
    """
    print(f"\nVisualizing toolpath with {len(toolpath.segments)} segments...")

    # Create visual lines for the toolpath
    line_ids = []

    for seg_idx, segment in enumerate(toolpath.segments):
        if len(segment.points) < 2:
            continue

        # Color based on segment type
        if segment.type.value == "perimeter":
            color = [0.2, 0.5, 1.0]  # Blue for perimeters
        elif segment.type.value == "infill":
            color = [1.0, 0.6, 0.2]  # Orange for infill
        else:
            color = [0.5, 0.5, 0.5]  # Gray for other

        # Draw lines between consecutive points
        for i in range(len(segment.points) - 1):
            p1 = segment.points[i]
            p2 = segment.points[i + 1]

            # Scale from mm to meters for visualization
            pos1 = [p1.x / 1000, p1.y / 1000, p1.z / 1000]
            pos2 = [p2.x / 1000, p2.y / 1000, p2.z / 1000]

            # Add debug line
            line_id = p.addUserDebugLine(
                pos1,
                pos2,
                lineColorRGB=color,
                lineWidth=2.0,
                lifeTime=0,  # Permanent
                physicsClientId=sim_env.client_id,
            )
            line_ids.append(line_id)

        # Animate if requested (show toolpath being built)
        if animate and seg_idx % 5 == 0:  # Update every 5 segments
            time.sleep(0.01)

    print(f"Created {len(line_ids)} debug lines")
    return line_ids


def add_toolhead_marker(sim_env, position, scale=0.002):
    """
    Add a small sphere to represent the toolhead/extruder.

    Args:
        sim_env: SimulationEnvironment instance
        position: [x, y, z] position in meters
        scale: Sphere radius in meters

    Returns:
        Body ID of the marker
    """
    visual_shape = p.createVisualShape(
        shapeType=p.GEOM_SPHERE,
        radius=scale,
        rgbaColor=[1.0, 0.0, 0.0, 1.0],  # Red marker
        physicsClientId=sim_env.client_id,
    )

    marker_id = p.createMultiBody(
        baseMass=0,
        baseVisualShapeIndex=visual_shape,
        basePosition=position,
        physicsClientId=sim_env.client_id,
    )

    return marker_id


def main():
    """Run the integrated slicing + simulation demo."""
    print("=" * 60)
    print("OpenAxis: Slicing + Simulation Demo")
    print("=" * 60)

    example_dir = Path(__file__).parent
    stl_file = example_dir / "simple_cube.stl"

    # Step 1: Load and slice geometry
    print("\n[1/4] Loading and slicing geometry...")
    mesh = GeometryLoader.load(stl_file)
    print(f"   Loaded mesh: {mesh.number_of_vertices()} vertices")

    slicer = PlanarSlicer(
        layer_height=2.0,  # 2mm layers for better visibility
        extrusion_width=1.0,
        wall_count=2,
        infill_density=0.15,
        infill_pattern=InfillPattern.LINES,
    )

    toolpath = slicer.slice(mesh)
    print(f"   Generated {toolpath.total_layers} layers")
    print(f"   Total segments: {len(toolpath.segments)}")
    print(f"   Total length: {toolpath.get_total_length():.1f} mm")

    # Step 2: Set up simulation environment
    print("\n[2/4] Setting up simulation environment...")
    print("   Mode: DIRECT (headless)")

    sim = SimulationEnvironment(mode=SimulationMode.DIRECT)
    sim.start()
    print("   Simulation started")

    # Add ground plane
    sim.add_ground_plane()
    print("   Ground plane added")

    # Load the part being manufactured
    part_id = sim.load_mesh(
        stl_file,
        position=(0, 0, 0),
        scale=0.001,  # Convert mm to meters
        color=(0.8, 0.8, 0.8, 0.3),  # Semi-transparent gray
    )
    print(f"   Part loaded (ID: {part_id})")

    # Step 3: Visualize toolpath
    print("\n[3/4] Visualizing toolpath...")
    line_ids = visualize_toolpath_in_simulation(
        toolpath, sim, animate=False  # Set to True for slower animation
    )

    # Add toolhead marker at start position
    if toolpath.segments and toolpath.segments[0].points:
        start_point = toolpath.segments[0].points[0]
        marker_id = add_toolhead_marker(
            sim, [start_point.x / 1000, start_point.y / 1000, start_point.z / 1000]
        )
        print(f"   Toolhead marker added (ID: {marker_id})")

    # Step 4: Run simulation
    print("\n[4/4] Running simulation...")
    print("   Stepping physics simulation...")

    for i in range(100):
        sim.step()

    print("   Simulation complete")

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print(f"Part: {stl_file.name}")
    print(f"Layers: {toolpath.total_layers} @ {toolpath.layer_height}mm")
    print(f"Segments: {len(toolpath.segments)}")
    print(f"Toolpath length: {toolpath.get_total_length():.1f} mm")
    print(f"Build time estimate: {toolpath.get_build_time_estimate():.1f} seconds")
    print(f"Simulation objects: {len(sim.get_loaded_objects())}")

    # Get bounds
    try:
        min_pt, max_pt = toolpath.get_bounds()
        print(
            f"\nBuild volume: {max_pt.x - min_pt.x:.1f} x {max_pt.y - min_pt.y:.1f} x {max_pt.z - min_pt.z:.1f} mm"
        )
    except ValueError:
        pass

    print("\n" + "=" * 60)
    print("[SUCCESS] Demo complete!")
    print("=" * 60)
    print("\nFeatures demonstrated:")
    print("  [OK] STL loading and slicing")
    print("  [OK] Toolpath generation (perimeters + infill)")
    print("  [OK] PyBullet simulation environment")
    print("  [OK] Toolpath visualization (debug lines)")
    print("  [OK] Multi-object scenes")
    print("\nNext steps:")
    print("  - Add robot arm to simulation")
    print("  - Animate toolpath execution in real-time")
    print("  - Implement collision detection")
    print("  - Add material deposition visualization")

    # Clean up
    sim.stop()


if __name__ == "__main__":
    main()
