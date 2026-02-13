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
    select_worktree,
    success,
    warning,
)
from .workspace import Workspace

# Global context object
pass_config = click.make_pass_decorator(Config, ensure=True)


def _resolve_worktree_with_selection(
    workspace: Workspace, worktree: Optional[str], select: bool
) -> Path:
    """Helper to resolve worktree with interactive selection support.

    Args:
        workspace: Workspace instance
        worktree: Optional worktree name
        select: Whether to use interactive selection

    Returns:
        Resolved worktree path

    Raises:
        SystemExit: If worktree not found or selection cancelled
    """
    if select:
        worktrees = workspace.list_worktrees()
        if not worktrees:
            error("No worktrees found")
            sys.exit(1)
        selected = select_worktree(worktrees)
        if not selected:
            error("No worktree selected")
            sys.exit(1)
        return selected.path
    else:
        try:
            return workspace.resolve_worktree(worktree)
        except ValueError as e:
            error(str(e))
            sys.exit(1)


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit")
@click.pass_context
def main(ctx: click.Context, version: bool) -> None:
    """Devcontainer management tool for git worktrees."""
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
@click.argument("worktree", required=False)
@click.option("--dotfile", "-d", is_flag=True, help="Use external dotfiles from GitHub")
@click.option("--select", "-s", is_flag=True, help="Interactive worktree selection")
@pass_config
def up(config: Config, worktree: Optional[str], dotfile: bool, select: bool) -> None:
    """Start the devcontainer.

    By default uses local dotfiles. Use --dotfile for external GitHub repo.

    Examples:
        dv up              # Start in current directory
        dv up main         # Start main worktree
        dv up --select     # Interactive selection
        dv up --dotfile    # Use external dotfiles
    """
    ws = Workspace()
    service = DevcontainerService(config)

    # Resolve which worktree to use
    workspace_path = _resolve_worktree_with_selection(ws, worktree, select)

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
@click.argument("worktree", required=False)
@click.option(
    "--shell", "-s", is_flag=True, help="Open interactive shell instead of dev command"
)
@click.option("--select", is_flag=True, help="Interactive worktree selection")
@pass_config
def go(config: Config, worktree: Optional[str], shell: bool, select: bool) -> None:
    """Enter the container and run dev command (or shell).

    Examples:
        dv go              # Run dev command in current worktree
        dv go main         # Run dev in main worktree
        dv go --shell      # Open shell in current worktree
        dv go --select     # Interactive selection
    """
    ws = Workspace()
    service = DevcontainerService(config)

    # Resolve worktree
    workspace_path = _resolve_worktree_with_selection(ws, worktree, select)

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
@click.argument("worktree", required=False)
@click.option("--select", is_flag=True, help="Interactive worktree selection")
@pass_config
def down(config: Config, worktree: Optional[str], select: bool) -> None:
    """Stop and remove the devcontainer.

    Examples:
        dv down              # Stop current worktree
        dv down main         # Stop main worktree
        dv down --select     # Interactive selection
    """
    ws = Workspace()
    service = DevcontainerService(config)

    # Resolve worktree
    workspace_path = _resolve_worktree_with_selection(ws, worktree, select)

    console.print(f"Stopping devcontainer in: [cyan]{workspace_path.name}[/cyan]")

    if service.down(workspace_path):
        success("Devcontainer stopped and removed")
    else:
        warning("No devcontainer found")


@main.command()
@click.argument("worktree", required=False)
@click.argument("command", nargs=-1, required=True)
@click.option("--select", is_flag=True, help="Interactive worktree selection")
@pass_config
def exec(
    config: Config, worktree: Optional[str], command: tuple[str, ...], select: bool
) -> None:
    """Execute a command in the devcontainer.

    Examples:
        dv exec -- ls -la
        dv exec main -- npm test
        dv exec --select -- bash
    """
    ws = Workspace()
    service = DevcontainerService(config)

    # Resolve worktree
    workspace_path = _resolve_worktree_with_selection(ws, worktree, select)

    service.exec(workspace_path, list(command), interactive=False)


@main.command()
@click.argument("worktree")
@click.argument("image")
@pass_config
def template(config: Config, worktree: str, image: str) -> None:
    """Create .devcontainer/devcontainer.json with managed image.

    Examples:
        dv template main node
        dv template feature-123 python
    """
    ws = Workspace()

    if not ws.is_worktree_project:
        error("Not in a worktree-enabled project")
        sys.exit(1)

    # Validate image
    if image not in config.images:
        error(f"Unknown image: {image}")
        console.print(f"\nAvailable images: {', '.join(sorted(config.images.keys()))}")
        sys.exit(1)

    # Get worktree path
    try:
        worktree_path = ws.resolve_worktree(worktree)
    except ValueError as e:
        error(str(e))
        sys.exit(1)

    devcontainer_dir = worktree_path / ".devcontainer"
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
    project_name = worktree_path.name
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
    """Clone a repository as a bare repo with worktree structure.

    Examples:
        dv clone git@github.com:user/repo.git
        dv clone https://github.com/user/repo.git my-project
    """
    service = RepositoryService(config)

    console.print(f"Cloning {url} as bare repository...")

    try:
        result = service.clone_as_bare(url, name)

        success(f"Bare repository created at {result.bare_repo}")
        console.print(f"Creating worktree for branch: [cyan]{result.default_branch}[/cyan]")
        success("Project cloned and worktree structure set up!")

        console.print(f"\n[bold]Next steps:[/bold]")
        console.print(f"  cd {result.project_dir.name}/{result.default_branch}")
        console.print("\n[bold]Available commands:[/bold]")
        console.print("  [cyan]dv up[/cyan]              - Start the devcontainer")
        console.print(
            "  [cyan]dv worktree add[/cyan]    - Create a new worktree for a branch"
        )
        console.print("  [cyan]dv worktree list[/cyan]   - List all worktrees")
        console.print(
            "  [cyan]dv exec[/cyan]            - Execute a command in the devcontainer"
        )

    except subprocess.CalledProcessError as e:
        error(f"Failed to clone: {e}")
        sys.exit(1)


# Worktree subcommands
@main.group()
def worktree() -> None:
    """Manage git worktrees and their devcontainers."""
    pass


@worktree.command("add")
@click.argument("branch", required=False)
@click.option("--no-start", is_flag=True, help="Don't automatically start devcontainer")
@click.option("--select", is_flag=True, help="Interactive branch selection")
@pass_config
def worktree_add(
    config: Config, branch: Optional[str], no_start: bool, select: bool
) -> None:
    """Create a new worktree and start its devcontainer.

    Examples:
        dv worktree add feature-123
        dv worktree add --select
        dv worktree add new-feature --no-start
    """
    ws = Workspace()
    service = RepositoryService(config)

    if not ws.is_worktree_project:
        error("Not in a worktree-enabled project")
        console.print("Run 'dv clone <url>' to set up a new project.")
        sys.exit(1)

    # Interactive branch selection
    if select or not branch:
        branches = ws.list_branches()
        if not branches:
            error("No branches found")
            sys.exit(1)
        branch = select_branch(branches, "Select branch for new worktree")
        if not branch:
            error("No branch selected")
            sys.exit(1)

    console.print(f"Creating worktree for branch: [cyan]{branch}[/cyan]")

    try:
        result = service.add_worktree_with_container(
            workspace=ws,
            branch=branch,
            start_container=not no_start,
            use_external_dotfiles=False,
        )

        success(f"Worktree created at: {result.worktree_path}")

        if not no_start:
            success("Devcontainer started with local dotfiles")
        else:
            console.print("\nTo start the devcontainer, run:")
            console.print(f"  cd {result.worktree_path}")
            console.print("  dv up")

    except (ValueError, RuntimeError, subprocess.CalledProcessError) as e:
        error(str(e))
        sys.exit(1)


@worktree.command("list")
def worktree_list() -> None:
    """List all worktrees with their devcontainer status."""
    ws = Workspace()

    if not ws.is_worktree_project:
        error("Not in a worktree-enabled project")
        sys.exit(1)

    worktrees = ws.list_worktrees()

    if not worktrees:
        console.print("No worktrees found")
        return

    console.print(f"\nWorktrees in [cyan]{ws.root}[/cyan]:\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Status", width=12)
    table.add_column("Name", style="cyan")
    table.add_column("Branch", style="green")
    table.add_column("Path", style="dim")

    for wt in worktrees:
        status_str = (
            f"[{wt.status.color}]{wt.status.icon}[/{wt.status.color}] {wt.status.value}"
        )
        table.add_row(status_str, wt.name, wt.branch, str(wt.path))

    console.print(table)


@worktree.command("remove")
@click.argument("branch", required=False)
@click.option("--select", is_flag=True, help="Interactive selection")
@pass_config
def worktree_remove(config: Config, branch: Optional[str], select: bool) -> None:
    """Remove a worktree and its devcontainer.

    Examples:
        dv worktree remove feature-123
        dv worktree remove --select
    """
    ws = Workspace()
    service = RepositoryService(config)

    if not ws.is_worktree_project:
        error("Not in a worktree-enabled project")
        sys.exit(1)

    # Interactive selection
    if select or not branch:
        worktrees = ws.list_worktrees()
        if not worktrees:
            error("No worktrees found")
            sys.exit(1)
        selected = select_worktree(worktrees)
        if not selected:
            error("No worktree selected")
            sys.exit(1)
        branch = selected.name

    console.print(f"Removing worktree: [cyan]{branch}[/cyan]")

    try:
        if service.remove_worktree_with_container(ws, branch):
            success(f"Worktree removed: {branch}")
        else:
            error("Failed to remove worktree")
            sys.exit(1)
    except ValueError as e:
        error(str(e))
        sys.exit(1)


@main.command()
@click.argument("worktree", required=False)
@pass_config
def status(config: Config, worktree: Optional[str]) -> None:
    """Show worktree and devcontainer status.

    Examples:
        dv status              # Show current worktree + list others
        dv status main         # Show specific worktree
    """
    ws = Workspace()
    service = DevcontainerService(config)

    if not ws.is_worktree_project:
        console.print("Not in a worktree-enabled project")
        console.print("\nRun 'dv clone <url>' to set up a new project with worktrees.")
        return

    # Specific worktree requested
    if worktree:
        try:
            path = ws.resolve_worktree(worktree)
            status_val = service.get_status(path)

            # Get branch
            result = subprocess.run(
                ["git", "-C", str(path), "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=False,
            )
            branch = result.stdout.strip() or "unknown"

            console.print(f"Worktree: [cyan]{path.name}[/cyan]")
            console.print(f"  Path:      {path}")
            console.print(f"  Branch:    {branch}")
            console.print(
                f"  Container: [{status_val.color}]{status_val.value}[/{status_val.color}]"
            )

        except ValueError as e:
            error(str(e))
            sys.exit(1)
        return

    # Show current + list others
    current = ws.get_current_worktree()
    if current:
        console.print("[bold]Current Worktree:[/bold]")
        console.print(f"  Path:      {current.path}")
        console.print(f"  Branch:    {current.branch}")
        console.print(
            f"  Container: [{current.status.color}]{current.status.value}[/{current.status.color}]"
        )
        console.print()

    # List other worktrees
    all_worktrees = ws.list_worktrees()
    other_worktrees = [wt for wt in all_worktrees if wt.path != ws.path]

    if other_worktrees:
        console.print("[bold]Other Worktrees:[/bold]")
        for wt in other_worktrees:
            icon = f"[{wt.status.color}]{wt.status.icon}[/{wt.status.color}]"
            console.print(f"  {icon} {wt.name} ({wt.branch})")


if __name__ == "__main__":
    main()
