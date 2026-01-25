"""
Command-line interface for OpenAxis.

Provides commands for project management, toolpath generation,
simulation, and robot control.
"""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from openaxis import __version__
from openaxis.core.config import ConfigManager
from openaxis.core.project import Project

console = Console()


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--config-dir",
    type=click.Path(exists=True, path_type=Path),
    default="config",
    help="Configuration directory",
)
@click.pass_context
def main(ctx: click.Context, config_dir: Path) -> None:
    """OpenAxis - Open-Source Robotic Hybrid Manufacturing Platform."""
    ctx.ensure_object(dict)
    ctx.obj["config_dir"] = config_dir


# =============================================================================
# Project Commands
# =============================================================================


@main.group()
def project() -> None:
    """Project management commands."""
    pass


@project.command("create")
@click.argument("name")
@click.argument("path", type=click.Path(path_type=Path))
@click.option("--description", "-d", default="", help="Project description")
@click.option("--author", "-a", default="", help="Project author")
def project_create(name: str, path: Path, description: str, author: str) -> None:
    """Create a new project."""
    try:
        project = Project.create(name, path, description=description, author=author)
        console.print(f"[green]✓[/green] Created project '{name}' at {path}")
        console.print(f"  ID: {project.metadata.id}")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to create project: {e}")
        raise SystemExit(1)


@project.command("info")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def project_info(path: Path) -> None:
    """Show project information."""
    try:
        project = Project.load(path)

        table = Table(title=f"Project: {project.metadata.name}")
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        table.add_row("ID", project.metadata.id)
        table.add_row("Name", project.metadata.name)
        table.add_row("Description", project.metadata.description or "(none)")
        table.add_row("Author", project.metadata.author or "(none)")
        table.add_row("Created", project.metadata.created_at.isoformat())
        table.add_row("Modified", project.metadata.modified_at.isoformat())
        table.add_row("Robot Config", project.robot_config or "(none)")
        table.add_row("Parts", str(len(project.parts)))

        console.print(table)

        if project.parts:
            parts_table = Table(title="Parts")
            parts_table.add_column("ID")
            parts_table.add_column("Name")
            parts_table.add_column("Process")
            parts_table.add_column("Has Geometry")
            parts_table.add_column("Has Toolpath")

            for part_id, part in project.parts.items():
                parts_table.add_row(
                    part_id,
                    part.name,
                    part.process_config or "-",
                    "✓" if part.geometry_path else "-",
                    "✓" if part.toolpath_path else "-",
                )

            console.print(parts_table)

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to load project: {e}")
        raise SystemExit(1)


# =============================================================================
# Configuration Commands
# =============================================================================


@main.group()
def config() -> None:
    """Configuration management commands."""
    pass


@config.command("list-robots")
@click.pass_context
def config_list_robots(ctx: click.Context) -> None:
    """List available robot configurations."""
    try:
        config_mgr = ConfigManager(ctx.obj["config_dir"])
        robots = config_mgr.list_robots()

        if not robots:
            console.print("[yellow]No robot configurations found.[/yellow]")
            return

        table = Table(title="Available Robots")
        table.add_column("Name", style="cyan")
        table.add_column("Manufacturer")
        table.add_column("Type")

        for name in robots:
            robot = config_mgr.get_robot(name)
            table.add_row(name, robot.manufacturer, robot.type)

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to list robots: {e}")
        raise SystemExit(1)


@config.command("list-processes")
@click.pass_context
def config_list_processes(ctx: click.Context) -> None:
    """List available process configurations."""
    try:
        config_mgr = ConfigManager(ctx.obj["config_dir"])
        processes = config_mgr.list_processes()

        if not processes:
            console.print("[yellow]No process configurations found.[/yellow]")
            return

        table = Table(title="Available Processes")
        table.add_column("Name", style="cyan")
        table.add_column("Type")

        for name in processes:
            process = config_mgr.get_process(name)
            table.add_row(name, process.type)

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to list processes: {e}")
        raise SystemExit(1)


# =============================================================================
# Slicing Commands (placeholder for Phase 1)
# =============================================================================


@main.group()
def slice() -> None:
    """Toolpath generation commands."""
    pass


@slice.command("generate")
@click.argument("project_path", type=click.Path(exists=True, path_type=Path))
@click.argument("part_id")
@click.option("--process", "-p", help="Override process configuration")
def slice_generate(project_path: Path, part_id: str, process: Optional[str]) -> None:
    """Generate toolpath for a part."""
    console.print("[yellow]⚠[/yellow] Slicing not yet implemented (Phase 1)")
    console.print("  This will generate toolpaths using ORNL Slicer 2")


# =============================================================================
# Simulation Commands (placeholder for Phase 1)
# =============================================================================


@main.group()
def sim() -> None:
    """Simulation commands."""
    pass


@sim.command("run")
@click.argument("project_path", type=click.Path(exists=True, path_type=Path))
@click.argument("part_id")
def sim_run(project_path: Path, part_id: str) -> None:
    """Run simulation for a part."""
    console.print("[yellow]⚠[/yellow] Simulation not yet implemented (Phase 1)")
    console.print("  This will run pybullet_industrial simulation")


if __name__ == "__main__":
    main()
