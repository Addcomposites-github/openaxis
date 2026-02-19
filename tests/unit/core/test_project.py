"""
Unit tests for project management.
"""

import json
from pathlib import Path

import pytest

from openaxis.core.exceptions import OpenAxisError
from openaxis.core.project import Part, Project, ProjectMetadata


class TestProjectMetadata:
    """Tests for ProjectMetadata."""

    def test_create(self):
        """Test creating project metadata."""
        from datetime import datetime

        now = datetime.now()
        metadata = ProjectMetadata(
            id="test-id",
            name="Test Project",
            description="A test",
            created_at=now,
            modified_at=now,
        )
        assert metadata.name == "Test Project"
        assert metadata.version == "1.0"


class TestPart:
    """Tests for Part."""

    def test_create_minimal(self):
        """Test creating part with minimal fields."""
        part = Part(id="p1", name="Bracket")
        assert part.id == "p1"
        assert part.name == "Bracket"
        assert part.geometry_path is None

    def test_create_full(self, temp_dir):
        """Test creating part with all fields."""
        geom_path = temp_dir / "part.stl"
        part = Part(
            id="p1",
            name="Bracket",
            geometry_path=geom_path,
            process_config="waam_steel",
            metadata={"material": "steel"},
        )
        assert part.geometry_path == geom_path
        assert part.process_config == "waam_steel"
        assert part.metadata["material"] == "steel"


class TestProject:
    """Tests for Project."""

    def test_create(self, temp_dir):
        """Test creating a new project."""
        project_dir = temp_dir / "new_project"
        project = Project.create(
            name="Test Project",
            path=project_dir,
            description="A test project",
            author="Tester",
        )

        assert project.metadata.name == "Test Project"
        assert project.metadata.description == "A test project"
        assert project.metadata.author == "Tester"
        assert (project_dir / "project.json").exists()
        assert (project_dir / "parts").is_dir()
        assert (project_dir / "toolpaths").is_dir()

    def test_load(self, sample_project):
        """Test loading an existing project."""
        loaded = Project.load(sample_project.path)

        assert loaded.metadata.name == sample_project.metadata.name
        assert loaded.metadata.id == sample_project.metadata.id

    def test_load_not_found(self, temp_dir):
        """Test loading from non-existent path."""
        with pytest.raises(OpenAxisError):
            Project.load(temp_dir / "nonexistent")

    def test_save(self, sample_project):
        """Test saving project changes."""
        original_modified = sample_project.metadata.modified_at

        # Make a change
        sample_project.settings["test"] = "value"
        sample_project.save()

        # Reload and verify
        loaded = Project.load(sample_project.path)
        assert loaded.settings.get("test") == "value"
        assert loaded.metadata.modified_at >= original_modified

    def test_add_part(self, sample_project):
        """Test adding a part."""
        part = sample_project.add_part(
            name="Bracket",
            process_config="waam_steel",
        )

        assert part.name == "Bracket"
        assert part.id in sample_project.parts
        assert sample_project.parts[part.id].process_config == "waam_steel"

    def test_add_part_with_geometry(self, sample_project, temp_dir):
        """Test adding a part with geometry file."""
        geom_file = temp_dir / "bracket.stl"
        geom_file.write_text("dummy stl")

        part = sample_project.add_part(
            name="Bracket",
            geometry_path=geom_file,
        )

        assert part.geometry_path == geom_file

    def test_remove_part(self, sample_project):
        """Test removing a part."""
        part = sample_project.add_part(name="Temp Part")
        part_id = part.id

        sample_project.remove_part(part_id)

        assert part_id not in sample_project.parts

    def test_remove_part_not_found(self, sample_project):
        """Test removing non-existent part."""
        with pytest.raises(OpenAxisError):
            sample_project.remove_part("nonexistent")

    def test_get_part(self, sample_project):
        """Test getting a part by ID."""
        part = sample_project.add_part(name="Test Part")

        retrieved = sample_project.get_part(part.id)
        assert retrieved.name == "Test Part"

    def test_get_part_not_found(self, sample_project):
        """Test getting non-existent part."""
        with pytest.raises(OpenAxisError):
            sample_project.get_part("nonexistent")

    def test_set_robot(self, sample_project):
        """Test setting robot configuration."""
        sample_project.set_robot("abb_irb6700")
        assert sample_project.robot_config == "abb_irb6700"

    def test_directory_properties(self, sample_project):
        """Test directory path properties."""
        assert sample_project.parts_dir == sample_project.path / "parts"
        assert sample_project.toolpaths_dir == sample_project.path / "toolpaths"
        assert sample_project.simulation_dir == sample_project.path / "simulation"
        assert sample_project.output_dir == sample_project.path / "output"

    def test_persist_parts(self, sample_project):
        """Test that parts persist after save/load."""
        part = sample_project.add_part(
            name="Persistent Part",
            process_config="test_process",
        )
        sample_project.save()

        loaded = Project.load(sample_project.path)
        assert part.id in loaded.parts
        assert loaded.parts[part.id].name == "Persistent Part"
