"""
3D visualization of sliced toolpaths using matplotlib.

This provides a visual preview of the generated toolpaths showing
perimeters, infill, and layer structure.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from openaxis.core.geometry import GeometryLoader
from openaxis.slicing.planar_slicer import PlanarSlicer
from openaxis.slicing.toolpath import InfillPattern, ToolpathType


def plot_toolpath(ax, toolpath, title="Toolpath"):
    """
    Plot a toolpath on a 3D matplotlib axes.

    Args:
        ax: Matplotlib 3D axes
        toolpath: Toolpath object
        title: Plot title
    """
    # Color map for different segment types
    colors = {
        ToolpathType.PERIMETER: "blue",
        ToolpathType.INFILL: "orange",
        ToolpathType.SUPPORT: "green",
        ToolpathType.TRAVEL: "red",
    }

    # Plot each segment
    for segment in toolpath.segments:
        if not segment.points or len(segment.points) < 2:
            continue

        # Extract coordinates
        xs = [p.x for p in segment.points]
        ys = [p.y for p in segment.points]
        zs = [p.z for p in segment.points]

        # Get color for segment type
        color = colors.get(segment.type, "gray")

        # Plot line
        ax.plot(xs, ys, zs, color=color, linewidth=1.0, alpha=0.8)

    # Set equal aspect ratio
    try:
        min_pt, max_pt = toolpath.get_bounds()
        center = [
            (min_pt.x + max_pt.x) / 2,
            (min_pt.y + max_pt.y) / 2,
            (min_pt.z + max_pt.z) / 2,
        ]
        max_range = max(
            max_pt.x - min_pt.x, max_pt.y - min_pt.y, max_pt.z - min_pt.z
        )
        max_range = max_range / 2 * 1.1  # Add 10% margin

        ax.set_xlim([center[0] - max_range, center[0] + max_range])
        ax.set_ylim([center[1] - max_range, center[1] + max_range])
        ax.set_zlim([center[2] - max_range, center[2] + max_range])
    except ValueError:
        pass

    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_zlabel("Z (mm)")
    ax.set_title(title)

    # Add legend
    from matplotlib.lines import Line2D

    legend_elements = [
        Line2D([0], [0], color="blue", linewidth=2, label="Perimeter"),
        Line2D([0], [0], color="orange", linewidth=2, label="Infill"),
    ]
    ax.legend(handles=legend_elements, loc="upper right")


def main():
    """Visualize toolpath generation."""
    print("=" * 60)
    print("OpenAxis Toolpath Visualization")
    print("=" * 60)

    # Load the cube
    example_dir = Path(__file__).parent
    stl_file = example_dir / "simple_cube.stl"

    print(f"\nLoading: {stl_file.name}")
    mesh = GeometryLoader.load(stl_file)
    print(f"Loaded mesh with {mesh.number_of_vertices()} vertices")

    # Create slicer
    print("\nConfiguring slicer...")
    slicer = PlanarSlicer(
        layer_height=0.5,
        extrusion_width=0.8,
        wall_count=2,
        infill_density=0.2,
        infill_pattern=InfillPattern.LINES,
    )

    # Slice the mesh
    print("Slicing mesh...")
    toolpath = slicer.slice(mesh)
    print(f"Generated {toolpath.total_layers} layers with {len(toolpath.segments)} segments")

    # Create visualization
    print("Generating visualization...")
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle(
        "OpenAxis Toolpath Visualization", fontsize=16, fontweight="bold"
    )

    # Full toolpath
    ax1 = fig.add_subplot(2, 2, 1, projection="3d")
    plot_toolpath(
        ax1,
        toolpath,
        f"Complete Toolpath\n({toolpath.total_layers} layers, {len(toolpath.segments)} segments)",
    )

    # First layer only
    ax2 = fig.add_subplot(2, 2, 2, projection="3d")
    from openaxis.slicing.toolpath import Toolpath

    first_layer = Toolpath(layer_height=toolpath.layer_height)
    for seg in toolpath.get_segments_by_layer(0):
        first_layer.add_segment(seg)
    plot_toolpath(ax2, first_layer, "Layer 0\n(First Layer)")

    # Middle layer
    ax3 = fig.add_subplot(2, 2, 3, projection="3d")
    mid_layer_idx = toolpath.total_layers // 2
    mid_layer = Toolpath(layer_height=toolpath.layer_height)
    for seg in toolpath.get_segments_by_layer(mid_layer_idx):
        mid_layer.add_segment(seg)
    plot_toolpath(ax3, mid_layer, f"Layer {mid_layer_idx}\n(Middle Layer)")

    # Last layer
    ax4 = fig.add_subplot(2, 2, 4, projection="3d")
    last_layer_idx = toolpath.total_layers - 1
    last_layer = Toolpath(layer_height=toolpath.layer_height)
    for seg in toolpath.get_segments_by_layer(last_layer_idx):
        last_layer.add_segment(seg)
    plot_toolpath(ax4, last_layer, f"Layer {last_layer_idx}\n(Top Layer)")

    plt.tight_layout()

    # Save to file
    output_file = example_dir / "toolpath_visualization.png"
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    print(f"\n[OK] Saved visualization to: {output_file}")

    # Show interactive window
    print("\n[INFO] Displaying interactive 3D view...")
    print("       - Rotate: Click and drag")
    print("       - Zoom: Right-click and drag (or scroll)")
    print("       - Close window to exit")
    plt.show()

    print("\n" + "=" * 60)
    print("[SUCCESS] Visualization complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print("\n[ERROR] Matplotlib not installed!")
        print("Install with: pip install matplotlib")
        print(f"\nDetails: {e}")
