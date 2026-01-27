"""
Basic simulation test - verifies PyBullet environment setup.

This is a simple test to ensure the simulation environment
can be initialized and basic objects can be loaded.
"""

import time
from pathlib import Path

from openaxis.simulation.environment import SimulationEnvironment, SimulationMode


def main():
    """Run basic simulation test."""
    print("=" * 60)
    print("OpenAxis Basic Simulation Test")
    print("=" * 60)

    # Test 1: Headless mode (no GUI)
    print("\n1. Testing headless (DIRECT) mode")
    try:
        with SimulationEnvironment(mode=SimulationMode.DIRECT) as sim:
            print("   [OK] Environment created in DIRECT mode")

            # Add ground plane
            plane_id = sim.add_ground_plane()
            print(f"   [OK] Ground plane loaded (ID: {plane_id})")

            # Run a few simulation steps
            for i in range(10):
                sim.step()
            print("   [OK] Simulation stepped 10 times")

            # Check loaded objects
            objects = sim.get_loaded_objects()
            print(f"   [OK] Loaded objects: {len(objects)}")

        print("   [OK] Environment cleaned up successfully")

    except Exception as e:
        print(f"   [ERROR] Headless mode failed: {e}")
        return False

    # Test 2: Load a mesh
    print("\n2. Testing mesh loading")
    example_dir = Path(__file__).parent
    stl_file = example_dir / "simple_cube.stl"

    if not stl_file.exists():
        print(f"   [SKIP] Test mesh not found: {stl_file}")
    else:
        try:
            with SimulationEnvironment(mode=SimulationMode.DIRECT) as sim:
                # Load mesh
                mesh_id = sim.load_mesh(
                    stl_file,
                    position=(0, 0, 10),  # 10mm above ground
                    color=(0.3, 0.7, 1.0, 1.0),  # Blue
                )
                print(f"   [OK] Mesh loaded (ID: {mesh_id})")

                # Check it was registered
                objects = sim.get_loaded_objects()
                assert mesh_id in objects
                print(f"   [OK] Mesh registered in environment")

        except Exception as e:
            print(f"   [ERROR] Mesh loading failed: {e}")
            return False

    # Test 3: GUI mode (optional - requires display)
    print("\n3. Testing GUI mode")
    print("   [SKIP] GUI mode requires display - skipping for automated tests")
    print("   [INFO] To test GUI mode manually, run simulation demos interactively")

    print("\n" + "=" * 60)
    print("[SUCCESS] Basic simulation tests completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("  - Load robot URDF models")
    print("  - Simulate toolpath execution")
    print("  - Add collision detection")

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
