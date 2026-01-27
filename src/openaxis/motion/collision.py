"""
Collision detection for motion planning.

This module provides collision checking using PyBullet's physics engine.
"""

from typing import Dict, List, Optional

import pybullet as p
from compas_robots import Configuration, RobotModel

from openaxis.simulation.environment import SimulationEnvironment


class CollisionChecker:
    """
    Collision detection using PyBullet.

    Wraps PyBullet's collision detection API to check for:
    - Self-collision (robot links colliding with each other)
    - Environment collision (robot colliding with obstacles)
    """

    def __init__(self, simulation_env: SimulationEnvironment):
        """
        Initialize collision checker.

        Args:
            simulation_env: Active simulation environment
        """
        self.sim_env = simulation_env
        self.robot_id: Optional[int] = None
        self.link_name_to_index: Dict[str, int] = {}

    def load_robot(self, urdf_path: str, base_position=(0, 0, 0)) -> int:
        """
        Load robot into the collision checking environment.

        Args:
            urdf_path: Path to robot URDF file
            base_position: Robot base position

        Returns:
            Robot body ID
        """
        if not self.sim_env.is_running:
            raise RuntimeError("Simulation environment not running")

        self.robot_id = self.sim_env.load_urdf(
            urdf_path, base_position=base_position, fixed_base=True
        )

        # Build link name to index mapping
        num_joints = p.getNumJoints(self.robot_id, physicsClientId=self.sim_env.client_id)
        for i in range(num_joints):
            joint_info = p.getJointInfo(self.robot_id, i, physicsClientId=self.sim_env.client_id)
            link_name = joint_info[12].decode("utf-8")  # Link name
            self.link_name_to_index[link_name] = i

        return self.robot_id

    def set_configuration(self, configuration: Configuration) -> None:
        """
        Set robot to a specific configuration.

        Args:
            configuration: Joint configuration to set
        """
        if self.robot_id is None:
            raise RuntimeError("Robot not loaded")

        # Set joint positions
        for joint_name, joint_value in zip(
            configuration.joint_names, configuration.joint_values
        ):
            # Find joint index
            if joint_name in self.link_name_to_index:
                joint_index = self.link_name_to_index[joint_name]
                p.resetJointState(
                    self.robot_id,
                    joint_index,
                    joint_value,
                    physicsClientId=self.sim_env.client_id,
                )

    def check_self_collision(self) -> bool:
        """
        Check if robot is in self-collision.

        Returns:
            True if collision detected, False otherwise
        """
        if self.robot_id is None:
            raise RuntimeError("Robot not loaded")

        # Perform collision detection
        p.performCollisionDetection(physicsClientId=self.sim_env.client_id)

        # Check for contacts between robot links
        num_joints = p.getNumJoints(self.robot_id, physicsClientId=self.sim_env.client_id)

        for i in range(-1, num_joints):  # -1 for base link
            for j in range(i + 1, num_joints):
                contacts = p.getContactPoints(
                    bodyA=self.robot_id,
                    bodyB=self.robot_id,
                    linkIndexA=i,
                    linkIndexB=j,
                    physicsClientId=self.sim_env.client_id,
                )

                if len(contacts) > 0:
                    return True  # Collision detected

        return False  # No collision

    def check_environment_collision(
        self, exclude_bodies: Optional[List[int]] = None
    ) -> bool:
        """
        Check if robot collides with environment objects.

        Args:
            exclude_bodies: List of body IDs to exclude from checking

        Returns:
            True if collision detected, False otherwise
        """
        if self.robot_id is None:
            raise RuntimeError("Robot not loaded")

        if exclude_bodies is None:
            exclude_bodies = []

        # Perform collision detection
        p.performCollisionDetection(physicsClientId=self.sim_env.client_id)

        # Get all bodies in the environment
        num_bodies = p.getNumBodies(physicsClientId=self.sim_env.client_id)

        for body_id in range(num_bodies):
            # Skip robot itself and excluded bodies
            if body_id == self.robot_id or body_id in exclude_bodies:
                continue

            # Check for contacts with this body
            contacts = p.getContactPoints(
                bodyA=self.robot_id,
                bodyB=body_id,
                physicsClientId=self.sim_env.client_id,
            )

            if len(contacts) > 0:
                return True  # Collision detected

        return False  # No collision

    def check_collision(
        self, configuration: Configuration, exclude_bodies: Optional[List[int]] = None
    ) -> bool:
        """
        Check if a configuration is in collision.

        Args:
            configuration: Configuration to check
            exclude_bodies: Bodies to exclude from environment collision checking

        Returns:
            True if collision detected, False otherwise
        """
        # Set robot to configuration
        self.set_configuration(configuration)

        # Check self-collision
        if self.check_self_collision():
            return True

        # Check environment collision
        if self.check_environment_collision(exclude_bodies):
            return True

        return False

    def is_path_collision_free(
        self,
        configurations: List[Configuration],
        exclude_bodies: Optional[List[int]] = None,
    ) -> bool:
        """
        Check if an entire path is collision-free.

        Args:
            configurations: Path to check
            exclude_bodies: Bodies to exclude from checking

        Returns:
            True if path is collision-free, False otherwise
        """
        for config in configurations:
            if self.check_collision(config, exclude_bodies):
                return False
        return True

    def get_collision_points(self) -> List[tuple]:
        """
        Get all current collision contact points.

        Returns:
            List of contact point tuples (bodyA, bodyB, linkA, linkB, position)
        """
        if self.robot_id is None:
            raise RuntimeError("Robot not loaded")

        p.performCollisionDetection(physicsClientId=self.sim_env.client_id)

        all_contacts = []
        num_bodies = p.getNumBodies(physicsClientId=self.sim_env.client_id)

        for body_id in range(num_bodies):
            contacts = p.getContactPoints(
                bodyA=self.robot_id,
                bodyB=body_id,
                physicsClientId=self.sim_env.client_id,
            )

            for contact in contacts:
                all_contacts.append(
                    (
                        contact[1],  # bodyA
                        contact[2],  # bodyB
                        contact[3],  # linkA
                        contact[4],  # linkB
                        contact[5],  # positionOnA
                    )
                )

        return all_contacts
