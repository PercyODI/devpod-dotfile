"""CLI interface for dv using Click."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import Config
from .container import Container
from .devcontainer_service import DevcontainerService
from .repository_service import RepositoryService
from .utils import (
    console,
    error,
    run_devcontainer,
    select_branch,
    select_branch_directory,
    success,
    warning,
)
from .project import Project

# Global context object
pass_config = click.make_pass_decorator(Config, ensure=True)


def _resolve_branch_with_selection(
    project: Project, branch: Optional[str], select: bool
) -> Path:
    """Helper to resolve branch directory with interactive selection support.

    Args:
        project: Project instance
        branch: Optional branch name
        select: Whether to use interactive selection

    Returns:
        Resolved branch directory path

    Raises:
        SystemExit: If branch not found or selection cancelled
    """
    if select:
        branch_dirs = project.list_branch_directories()
        if not branch_dirs:
            error("No branch directories found")
            sys.exit(1)
        selected = select_branch_directory(branch_dirs)
        if not selected:
            error("No branch directory selected")
            sys.exit(1)
        return selected.path
    else:
        if not branch:
            error("Branch argument is required")
            console.print("Usage: dv <command> <branch-name>")
            console.print("  or:  dv <command> --select")
            sys.exit(1)
        try:
            return project.resolve_branch(branch)
        except ValueError as e:
            error(str(e))
            sys.exit(1)


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit")
@click.pass_context
def main(ctx: click.Context, version: bool) -> None:
    """Devcontainer management tool for git branch directories."""
    # Load configuration
    config_file = Path.home() / ".config" / "dv" / "config.yml"
    ctx.obj = Config.from_file(config_file)

    if version:
        click.echo(f"dv version {__version__}")
        ctx.exit()

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(1)


@main.command()
@click.argument("branch", required=True)
@click.option("--dotfile", "-d", is_flag=True, help="Use external dotfiles from GitHub")
@click.option("--select", "-s", is_flag=True, help="Interactive branch selection")
@pass_config
def up(config: Config, branch: str, dotfile: bool, select: bool) -> None:
    """Start the devcontainer.

    By default uses local dotfiles. Use --dotfile for external GitHub repo.

    Examples:
        dv up main         # Start main branch
        dv up --select     # Interactive selection
        dv up main --dotfile    # Use external dotfiles
    """
    project = Project()
    service = DevcontainerService(config)

    # Resolve which branch to use
    workspace_path = _resolve_branch_with_selection(project, branch, select)

    console.print(f"Starting devcontainer in: [cyan]{workspace_path.name}[/cyan]")

    # Run devcontainer up
    try:
        service.up(workspace_path, use_external_dotfiles=dotfile)
        success(
            f"Devcontainer started with {'external' if dotfile else 'local'} dotfiles"
        )
    except subprocess.CalledProcessError as e:
        error(f"Failed to start devcontainer: {e}")
        sys.exit(1)


@main.command()
@click.argument("branch", required=True)
@click.option(
    "--shell", "-s", is_flag=True, help="Open interactive shell instead of dev command"
)
@click.option("--select", is_flag=True, help="Interactive branch selection")
@pass_config
def go(config: Config, branch: str, shell: bool, select: bool) -> None:
    """Enter the container and run dev command (or shell).

    Examples:
        dv go main         # Run dev in main branch
        dv go main --shell      # Open shell in main branch
        dv go --select     # Interactive selection
    """
    project = Project()
    service = DevcontainerService(config)

    # Resolve branch
    workspace_path = _resolve_branch_with_selection(project, branch, select)

    # Determine command to run
    if shell:
        command = ["zsh"]
    else:
        command = ["zsh", "-ic", "dev"]

    # Run interactively
    try:
        service.exec(workspace_path, command, interactive=True)
    except KeyboardInterrupt:
        pass


@main.command()
@click.argument("branch", required=True)
@click.option("--select", is_flag=True, help="Interactive branch selection")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@pass_config
def down(config: Config, branch: str, select: bool, force: bool) -> None:
    """Stop and remove the devcontainer.

    Examples:
        dv down main         # Stop main branch (with confirmation)
        dv down main --force # Stop without confirmation
        dv down --select     # Interactive selection
    """
    project = Project()
    service = DevcontainerService(config)

    # Resolve branch
    workspace_path = _resolve_branch_with_selection(project, branch, select)

    console.print(f"Stopping devcontainer in: [cyan]{workspace_path.name}[/cyan]")

    # Note: service.down will handle confirmation via Container.stop()
    container = Container(workspace_path)
    if container.stop(force=force):
        success("Devcontainer stopped and removed")
    else:
        warning("No devcontainer found")


@main.command()
@click.argument("branch", required=True)
@click.argument("command", nargs=-1, required=True)
@click.option("--select", is_flag=True, help="Interactive branch selection")
@pass_config
def exec(
    config: Config, branch: str, command: tuple[str, ...], select: bool
) -> None:
    """Execute a command in the devcontainer.

    Examples:
        dv exec main -- ls -la
        dv exec main -- npm test
        dv exec --select -- bash
    """
    project = Project()
    service = DevcontainerService(config)

    # Resolve branch
    workspace_path = _resolve_branch_with_selection(project, branch, select)

    service.exec(workspace_path, list(command), interactive=False)


@main.command()
@click.argument("branch", required=True)
@click.argument("image")
@pass_config
def template(config: Config, branch: str, image: str) -> None:
    """Create .devcontainer/devcontainer.json with managed image.

    Examples:
        dv template main node
        dv template feature-123 python
    """
    project = Project()

    if not project.is_dv_project:
        error("Not in a DV project")
        sys.exit(1)

    # Validate image
    if image not in config.images:
        error(f"Unknown image: {image}")
        console.print(f"\nAvailable images: {', '.join(sorted(config.images.keys()))}")
        sys.exit(1)

    # Get branch path
    try:
        branch_path = project.resolve_branch(branch)
    except ValueError as e:
        error(str(e))
        sys.exit(1)

    devcontainer_dir = branch_path / ".devcontainer"
    devcontainer_file = devcontainer_dir / "devcontainer.json"

    # Check if exists
    if devcontainer_file.exists():
        warning(f"{devcontainer_file} already exists")
        if not click.confirm("Overwrite?", default=False):
            console.print("Cancelled")
            return

    # Create directory
    devcontainer_dir.mkdir(exist_ok=True)

    # Write config
    project_name = branch_path.name
    config_data = {
        "name": project_name,
        "image": config.images[image],
    }

    with open(devcontainer_file, "w") as f:
        json.dump(config_data, f, indent=2)
        f.write("\n")

    success(f"Created {devcontainer_file}")
    console.print(f"\n  Name:  {project_name}")
    console.print(f"  Image: {config.images[image]}")
    console.print("\nNext steps:")
    console.print("  1. Review and customize .devcontainer/devcontainer.json")
    console.print("  2. Run 'dv up' to start the devcontainer")


@main.command()
@click.argument("url")
@click.argument("name", required=False)
@pass_config
def clone(config: Config, url: str, name: Optional[str]) -> None:
    """Clone a repository with DV branch directory structure.

    Examples:
        dv clone git@github.com:user/repo.git
        dv clone https://github.com/user/repo.git my-project
    """
    service = RepositoryService(config)

    console.print(f"Cloning {url}...")

    try:
        result = service.clone_as_regular(url, name)

        success(f"Repository cloned to {result.project_dir}")
        console.print(f"Default branch: [cyan]{result.default_branch}[/cyan]")

        console.print(f"\n[bold]Next steps:[/bold]")
        console.print(f"  cd {result.project_dir.name}")
        console.print(f"  dv up {result.default_branch}")

        console.print("\n[bold]To add more branches:[/bold]")
        console.print("  dv branch add <branch-name>")

    except subprocess.CalledProcessError as e:
        error(f"Failed to clone: {e}")
        sys.exit(1)


# Branch subcommands
@main.group()
def branch() -> None:
    """Manage git branch directories and their devcontainers."""
    pass


@branch.command("add")
@click.argument("branch_name", required=True)
@click.option("--no-start", is_flag=True, help="Don't automatically start devcontainer")
@click.option("--clone", is_flag=True, help="Use full git clone instead of local clone")
@pass_config
def branch_add(
    config: Config, branch_name: str, no_start: bool, clone: bool
) -> None:
    """Create a new branch directory and start its devcontainer.

    Examples:
        dv branch add feature-123          # Local clone (fast)
        dv branch add feature-456 --clone  # Full git clone
        dv branch add new-feature --no-start
    """
    project = Project()
    service = RepositoryService(config)

    if not project.is_dv_project:
        error("Not in a DV project")
        console.print("Run 'dv clone <url>' to set up a new project.")
        sys.exit(1)

    console.print(f"Creating branch directory for: [cyan]{branch_name}[/cyan]")

    try:
        result = service.add_branch_with_container(
            project=project,
            branch=branch_name,
            start_container=not no_start,
            use_external_dotfiles=False,
            use_git_clone=clone,
        )

        success(f"Branch directory created at: {result.branch_path}")

        if not no_start:
            success("Devcontainer started with local dotfiles")
        else:
            console.print("\nTo start the devcontainer, run:")
            console.print(f"  dv up {branch_name}")

    except (ValueError, RuntimeError, subprocess.CalledProcessError) as e:
        error(str(e))
        sys.exit(1)


@branch.command("list")
def branch_list() -> None:
    """List all branch directories with their devcontainer status."""
    project = Project()

    if not project.is_dv_project:
        error("Not in a DV project")
        sys.exit(1)

    branch_dirs = project.list_branch_directories()

    if not branch_dirs:
        console.print("No branch directories found")
        return

    console.print(f"\nBranch directories in [cyan]{project.path}[/cyan]:\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Status", width=12)
    table.add_column("Name", style="cyan")
    table.add_column("Branch", style="green")
    table.add_column("Path", style="dim")

    for bd in branch_dirs:
        status_str = (
            f"[{bd.status.color}]{bd.status.icon}[/{bd.status.color}] {bd.status.value}"
        )
        table.add_row(status_str, bd.name, bd.branch, str(bd.path))

    console.print(table)


@branch.command("remove")
@click.argument("branch_name", required=True)
@click.option("--select", is_flag=True, help="Interactive selection")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@pass_config
def branch_remove(config: Config, branch_name: str, select: bool, force: bool) -> None:
    """Remove a branch directory and its devcontainer.

    Examples:
        dv branch remove feature-123         # With confirmation
        dv branch remove feature-123 --force # Skip confirmation
        dv branch remove --select            # Interactive selection
    """
    project = Project()

    if not project.is_dv_project:
        error("Not in a DV project")
        sys.exit(1)

    # Interactive selection
    if select:
        branch_dirs = project.list_branch_directories()
        if not branch_dirs:
            error("No branch directories found")
            sys.exit(1)
        selected = select_branch_directory(branch_dirs)
        if not selected:
            error("No branch directory selected")
            sys.exit(1)
        branch_name = selected.name

    console.print(f"Removing branch directory: [cyan]{branch_name}[/cyan]")

    try:
        # First stop the container with confirmation
        branch_path = project.resolve_branch(branch_name)
        container = Container(branch_path)
        container.stop(force=force)

        # Then remove the directory with confirmation
        if project.remove_branch_directory(branch_name, force=force):
            success(f"Branch directory removed: {branch_name}")
        else:
            console.print("[yellow]Operation cancelled[/yellow]")
            sys.exit(0)
    except ValueError as e:
        error(str(e))
        sys.exit(1)


@main.command()
@click.argument("branch", required=True)
@pass_config
def status(config: Config, branch: str) -> None:
    """Show branch directory and devcontainer status.

    Examples:
        dv status main         # Show specific branch
    """
    project = Project()
    service = DevcontainerService(config)

    if not project.is_dv_project:
        console.print("Not in a DV project")
        console.print("\nRun 'dv clone <url>' to set up a new project.")
        return

    # Show specific branch
    try:
        path = project.resolve_branch(branch)
        status_val = service.get_status(path)

        # Get branch
        result = subprocess.run(
            ["git", "-C", str(path), "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=False,
        )
        branch_name = result.stdout.strip() or "unknown"

        console.print(f"Branch Directory: [cyan]{path.name}[/cyan]")
        console.print(f"  Path:      {path}")
        console.print(f"  Branch:    {branch_name}")
        console.print(
            f"  Container: [{status_val.color}]{status_val.value}[/{status_val.color}]"
        )

    except ValueError as e:
        error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
