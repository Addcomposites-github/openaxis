"""
Demonstration of OpenAxis robot capabilities.

This script shows how to:
1. Create robot configuration
2. Access robot properties
3. Validate joint configurations
4. (FK requires URDF file - shown in concept)
"""

import math

from openaxis.core.config import RobotConfig
from openaxis.core.robot import RobotInstance, KinematicsEngine


def main():
    """Run robot demonstration."""
    print("=" * 60)
    print("OpenAxis Robot Demo")
    print("=" * 60)

    # 1. Create robot configuration
    print("\n1. Creating robot configuration")
    config = RobotConfig(
        name="ABB IRB 6700-200/2.60",
        manufacturer="ABB",
        type="industrial_arm",
        urdf_path=None,  # Would normally point to URDF file
        base_frame="base_link",
        tool_frame="tool0",
        joint_limits={
            "joint_1": {"min": math.radians(-170), "max": math.radians(170)},
            "joint_2": {"min": math.radians(-65), "max": math.radians(85)},
            "joint_3": {"min": math.radians(-180), "max": math.radians(70)},
            "joint_4": {"min": math.radians(-300), "max": math.radians(300)},
            "joint_5": {"min": math.radians(-130), "max": math.radians(130)},
            "joint_6": {"min": math.radians(-360), "max": math.radians(360)},
        },
    )

    print(f"   [OK] Created configuration for: {config.name}")
    print(f"   [OK] Manufacturer: {config.manufacturer}")
    print(f"   [OK] Type: {config.type}")
    print(f"   [OK] Joint limits defined for {len(config.joint_limits)} joints")

    # 2. Show configuration validation
    print("\n2. Demonstrating configuration validation")

    # Note: Full robot instance would require a URDF file
    # Here we show the config structure

    print("   Joint limits (degrees):")
    for joint_name, limits in config.joint_limits.items():
        min_deg = math.degrees(limits["min"])
        max_deg = math.degrees(limits["max"])
        print(f"     {joint_name}: [{min_deg:6.1f}, {max_deg:6.1f}]")

    # 3. Show example joint configurations
    print("\n3. Example joint configurations")

    # Home configuration (all zeros)
    home_config = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    print(f"   Home position: {[f'{v:.2f}' for v in home_config]}")

    # Sample working configuration
    working_config = [
        math.radians(45),   # joint_1: 45 degrees
        math.radians(-30),  # joint_2: -30 degrees
        math.radians(60),   # joint_3: 60 degrees
        math.radians(0),    # joint_4: 0 degrees
        math.radians(90),   # joint_5: 90 degrees
        math.radians(0),    # joint_6: 0 degrees
    ]
    print(f"   Working position (rad): {[f'{v:.2f}' for v in working_config]}")
    print(f"   Working position (deg): {[f'{math.degrees(v):.1f}' for v in working_config]}")

    # 4. Configuration structure
    print("\n4. Configuration features")
    print(f"   - Base frame: {config.base_frame}")
    print(f"   - Tool frame: {config.tool_frame}")
    print(f"   - Communication settings: {config.communication}")

    # 5. Next steps
    print("\n5. Next steps for full robot functionality")
    print("   - Add URDF file for robot model")
    print("   - Enable forward kinematics computation")
    print("   - Integrate with MoveIt2 for inverse kinematics (Phase 2)")
    print("   - Add collision checking (Phase 2)")

    print("\n" + "=" * 60)
    print("[SUCCESS] Robot config demo completed successfully!")
    print("=" * 60)
    print("\nNote: Full robot functionality requires URDF file.")
    print("See docs/ROADMAP.md Phase 1.3 for URDF integration details.")


if __name__ == "__main__":
    main()
