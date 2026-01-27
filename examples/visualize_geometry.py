"""
Simple 3D visualization of loaded geometry using matplotlib.

This provides a basic preview until the full GUI is built in Phase 3.
"""

import math
from pathlib import Path

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from openaxis.core.geometry import (
    BoundingBox,
    GeometryConverter,
    GeometryLoader,
    TransformationUtilities,
)
from compas.geometry import Vector


def plot_mesh(ax, mesh, title="Mesh", alpha=0.7, color='cyan', edge_color='black'):
    """
    Plot a COMPAS mesh on a 3D matplotlib axes.

    Args:
        ax: Matplotlib 3D axes
        mesh: COMPAS Mesh object
        title: Plot title
        alpha: Transparency (0-1)
        color: Face color
        edge_color: Edge color
    """
    # Convert to trimesh for easier plotting
    tmesh = GeometryConverter.compas_to_trimesh(mesh)

    # Create polygon collection from faces
    vertices = tmesh.vertices
    faces = tmesh.faces

    # Create 3D polygon collection
    poly = [[vertices[face[0]], vertices[face[1]], vertices[face[2]]]
            for face in faces]

    collection = Poly3DCollection(poly, alpha=alpha, facecolor=color,
                                 edgecolor=edge_color, linewidths=0.5)
    ax.add_collection3d(collection)

    # Set plot limits based on bounding box
    bbox = BoundingBox.from_mesh(mesh)
    center = BoundingBox.get_center(bbox)
    dims = BoundingBox.get_dimensions(bbox)
    max_dim = max(dims) * 0.6

    ax.set_xlim([center.x - max_dim, center.x + max_dim])
    ax.set_ylim([center.y - max_dim, center.y + max_dim])
    ax.set_zlim([center.z - max_dim, center.z + max_dim])

    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.set_zlabel('Z (mm)')
    ax.set_title(title)


def main():
    """Visualize geometry transformations."""
    print("=" * 60)
    print("OpenAxis 3D Geometry Visualization")
    print("=" * 60)

    # Load the cube
    example_dir = Path(__file__).parent
    stl_file = example_dir / "simple_cube.stl"

    print(f"\nLoading: {stl_file.name}")
    mesh = GeometryLoader.load(stl_file)
    print(f"Loaded mesh with {mesh.number_of_vertices()} vertices")

    # Create transformations
    print("\nCreating transformations...")
    translated = TransformationUtilities.translate(mesh, [15, 0, 0])
    rotated = TransformationUtilities.rotate(mesh, math.pi/4, Vector(0, 0, 1))
    scaled = TransformationUtilities.scale(mesh, 1.5)

    # Create visualization
    print("Generating visualization...")
    fig = plt.figure(figsize=(14, 10))
    fig.suptitle('OpenAxis Geometry Transformations', fontsize=16, fontweight='bold')

    # Original
    ax1 = fig.add_subplot(2, 2, 1, projection='3d')
    plot_mesh(ax1, mesh, "Original Cube\n(10x10x10 mm)", color='lightblue')

    # Translated
    ax2 = fig.add_subplot(2, 2, 2, projection='3d')
    plot_mesh(ax2, translated, "Translated\n(+15mm in X)", color='lightgreen')

    # Rotated
    ax3 = fig.add_subplot(2, 2, 3, projection='3d')
    plot_mesh(ax3, rotated, "Rotated\n(45° around Z)", color='salmon')

    # Scaled
    ax4 = fig.add_subplot(2, 2, 4, projection='3d')
    plot_mesh(ax4, scaled, "Scaled\n(1.5x uniform)", color='plum')

    plt.tight_layout()

    # Save to file
    output_file = example_dir / "geometry_visualization.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
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
