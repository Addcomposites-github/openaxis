"""
Project management for OpenAxis.

Handles project creation, loading, saving, and organization.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from openaxis.core.config import ProcessConfig, RobotConfig
from openaxis.core.exceptions import OpenAxisError


@dataclass
class ProjectMetadata:
    """Project metadata."""

    id: str
    name: str
    description: str
    created_at: datetime
    modified_at: datetime
    version: str = "1.0"
    author: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class Part:
    """A part to be manufactured."""

    id: str
    name: str
    geometry_path: Path | None = None
    process_config: str | None = None  # Reference to process config name
    toolpath_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Project:
    """
    OpenAxis manufacturing project.

    A project contains all information needed to manufacture parts:
    - Robot cell configuration
    - Parts to manufacture
    - Process configurations
    - Generated toolpaths
    - Simulation results

    Example:
        >>> project = Project.create("my_project", Path("projects/my_project"))
        >>> project.add_part("bracket", Path("models/bracket.stl"))
        >>> project.save()
    """

    path: Path
    metadata: ProjectMetadata
    robot_config: str | None = None  # Reference to robot config name
    parts: dict[str, Part] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        name: str,
        path: Path,
        description: str = "",
        author: str = "",
    ) -> "Project":
        """
        Create a new project.

        Args:
            name: Project name
            path: Directory to store project files
            description: Project description
            author: Project author

        Returns:
            New Project instance
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        metadata = ProjectMetadata(
            id=str(uuid4()),
            name=name,
            description=description,
            created_at=now,
            modified_at=now,
            author=author,
        )

        project = cls(path=path, metadata=metadata)

        # Create standard directories
        (path / "parts").mkdir(exist_ok=True)
        (path / "toolpaths").mkdir(exist_ok=True)
        (path / "simulation").mkdir(exist_ok=True)
        (path / "output").mkdir(exist_ok=True)

        project.save()
        return project

    @classmethod
    def load(cls, path: Path) -> "Project":
        """
        Load an existing project.

        Args:
            path: Project directory

        Returns:
            Loaded Project instance

        Raises:
            OpenAxisError: If project file not found or invalid
        """
        path = Path(path)
        project_file = path / "project.json"

        if not project_file.exists():
            raise OpenAxisError(
                f"Project file not found: {project_file}",
                details={"path": str(path)},
            )

        try:
            with open(project_file) as f:
                data = json.load(f)

            metadata = ProjectMetadata(
                id=data["id"],
                name=data["name"],
                description=data.get("description", ""),
                created_at=datetime.fromisoformat(data["created_at"]),
                modified_at=datetime.fromisoformat(data["modified_at"]),
                version=data.get("version", "1.0"),
                author=data.get("author", ""),
                tags=data.get("tags", []),
            )

            parts = {}
            for part_id, part_data in data.get("parts", {}).items():
                parts[part_id] = Part(
                    id=part_id,
                    name=part_data["name"],
                    geometry_path=Path(part_data["geometry_path"])
                    if part_data.get("geometry_path")
                    else None,
                    process_config=part_data.get("process_config"),
                    toolpath_path=Path(part_data["toolpath_path"])
                    if part_data.get("toolpath_path")
                    else None,
                    metadata=part_data.get("metadata", {}),
                )

            return cls(
                path=path,
                metadata=metadata,
                robot_config=data.get("robot_config"),
                parts=parts,
                settings=data.get("settings", {}),
            )

        except (json.JSONDecodeError, KeyError) as e:
            raise OpenAxisError(
                f"Invalid project file: {project_file}",
                details={"error": str(e)},
            )

    def save(self) -> None:
        """Save project to disk."""
        self.metadata.modified_at = datetime.now()

        data = {
            "id": self.metadata.id,
            "name": self.metadata.name,
            "description": self.metadata.description,
            "created_at": self.metadata.created_at.isoformat(),
            "modified_at": self.metadata.modified_at.isoformat(),
            "version": self.metadata.version,
            "author": self.metadata.author,
            "tags": self.metadata.tags,
            "robot_config": self.robot_config,
            "parts": {
                part_id: {
                    "name": part.name,
                    "geometry_path": str(part.geometry_path)
                    if part.geometry_path
                    else None,
                    "process_config": part.process_config,
                    "toolpath_path": str(part.toolpath_path)
                    if part.toolpath_path
                    else None,
                    "metadata": part.metadata,
                }
                for part_id, part in self.parts.items()
            },
            "settings": self.settings,
        }

        project_file = self.path / "project.json"
        with open(project_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_part(
        self,
        name: str,
        geometry_path: Path | None = None,
        process_config: str | None = None,
    ) -> Part:
        """
        Add a new part to the project.

        Args:
            name: Part name
            geometry_path: Path to geometry file (STL, STEP, etc.)
            process_config: Name of process configuration to use

        Returns:
            Created Part instance
        """
        part_id = str(uuid4())[:8]
        part = Part(
            id=part_id,
            name=name,
            geometry_path=Path(geometry_path) if geometry_path else None,
            process_config=process_config,
        )
        self.parts[part_id] = part
        return part

    def remove_part(self, part_id: str) -> None:
        """
        Remove a part from the project.

        Args:
            part_id: Part ID to remove

        Raises:
            OpenAxisError: If part not found
        """
        if part_id not in self.parts:
            raise OpenAxisError(
                f"Part not found: {part_id}",
                details={"available": list(self.parts.keys())},
            )
        del self.parts[part_id]

    def get_part(self, part_id: str) -> Part:
        """
        Get a part by ID.

        Args:
            part_id: Part ID

        Returns:
            Part instance

        Raises:
            OpenAxisError: If part not found
        """
        if part_id not in self.parts:
            raise OpenAxisError(
                f"Part not found: {part_id}",
                details={"available": list(self.parts.keys())},
            )
        return self.parts[part_id]

    def set_robot(self, robot_config: str) -> None:
        """
        Set the robot configuration for this project.

        Args:
            robot_config: Name of robot configuration
        """
        self.robot_config = robot_config

    @property
    def parts_dir(self) -> Path:
        """Get the parts directory path."""
        return self.path / "parts"

    @property
    def toolpaths_dir(self) -> Path:
        """Get the toolpaths directory path."""
        return self.path / "toolpaths"

    @property
    def simulation_dir(self) -> Path:
        """Get the simulation directory path."""
        return self.path / "simulation"

    @property
    def output_dir(self) -> Path:
        """Get the output directory path."""
        return self.path / "output"
