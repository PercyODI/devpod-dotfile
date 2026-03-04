"""CLI interface for dv using Click."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from . import __version__
from .config import Config
from .container import Container, ContainerStatus
from .devcontainer_service import DevcontainerService
from .repository_service import RepositoryService
from .utils import (
    console,
    error,
    prompt_for_workspace_name,
    run_devcontainer,
    select_branch,
    select_branch_directory,
    select_or_enter_branch,
    select_workspace,
    success,
    warning,
)
from .project import Project

# Global context object
pass_config = click.make_pass_decorator(Config, ensure=True)


def _resolve_branch_with_selection(
    project: Project, branch: Optional[str], select: bool
) -> Path:
    """Helper to resolve workspace with interactive selection support.

    Note: 'branch' parameter is actually a workspace name for backwards compatibility.

    Args:
        project: Project instance
        branch: Optional workspace name
        select: Whether to use interactive selection (or auto-select if branch is None)

    Returns:
        Resolved workspace directory path

    Raises:
        SystemExit: If workspace not found or selection cancelled
    """
    # If no workspace provided or --select flag used, do interactive selection
    if branch is None or select:
        workspaces = project.list_workspaces()
        if not workspaces:
            error("No workspaces found")
            sys.exit(1)
        selected = select_workspace(workspaces)
        if not selected:
            error("No workspace selected")
            sys.exit(1)
        return selected.path
    else:
        # Workspace name provided, resolve it
        try:
            return project.resolve_workspace(branch)
        except ValueError as e:
            error(str(e))
            sys.exit(1)


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit")
@click.pass_context
def main(ctx: click.Context, version: bool) -> None:
    """Devcontainer management tool for git workspace directories."""
    # Load configuration
    ctx.obj = Config.from_env()

    if version:
        click.echo(f"dv version {__version__}")
        ctx.exit()

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(1)


@main.command()
@click.argument("workspace", required=False)
@click.option("--dotfile", "-d", is_flag=True, help="Use external dotfiles from GitHub")
@click.option("--select", "-s", is_flag=True, help="Force interactive workspace selection")
@pass_config
def up(config: Config, workspace: Optional[str], dotfile: bool, select: bool) -> None:
    """Start the devcontainer.

    By default uses local dotfiles. Use --dotfile for external GitHub repo.
    If no workspace is specified, interactive selection is used.

    Examples:
        dv up                # Interactive selection
        dv up main           # Start main workspace
        dv up main --dotfile # Use external dotfiles
    """
    project = Project()
    service = DevcontainerService(config)

    # Resolve which workspace to use
    workspace_path = _resolve_branch_with_selection(project, workspace, select)

    console.print(f"Starting devcontainer in: [cyan]{workspace_path.name}[/cyan]")

    # Run devcontainer up
    try:
        service.up(workspace_path, project.path, use_external_dotfiles=dotfile)
        success(
            f"Devcontainer started with {'external' if dotfile else 'local'} dotfiles"
        )
    except subprocess.CalledProcessError as e:
        error(f"Failed to start devcontainer: {e}")
        sys.exit(1)


@main.command()
@click.argument("workspace", required=False)
@click.option(
    "--shell", "-s", is_flag=True, help="Open interactive shell instead of dev command"
)
@click.option("--select", is_flag=True, help="Force interactive workspace selection")
@pass_config
def go(config: Config, workspace: Optional[str], shell: bool, select: bool) -> None:
    """Enter the container and run dev command (or shell).

    If no workspace is specified, interactive selection is used.

    Examples:
        dv go              # Interactive selection
        dv go main         # Run dev in main workspace
        dv go main --shell # Open shell in main workspace
    """
    project = Project()
    service = DevcontainerService(config)

    # Resolve workspace
    workspace_path = _resolve_branch_with_selection(project, workspace, select)

    # Check if container is running; offer to start it if not
    container = Container(workspace_path)
    if container.get_status() != ContainerStatus.RUNNING:
        console.print(
            f"[yellow]Container for [cyan]{workspace_path.name}[/cyan] is not running.[/yellow]"
        )
        if not Confirm.ask("Start it now?", default=True):
            error("Container is not running")
            sys.exit(1)
        try:
            service.up(workspace_path, project.path, use_external_dotfiles=False)
            success("Devcontainer started with local dotfiles")
        except subprocess.CalledProcessError as e:
            error(f"Failed to start devcontainer: {e}")
            sys.exit(1)

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
@click.argument("workspace", required=False)
@click.option("--select", is_flag=True, help="Force interactive workspace selection")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.option("--all", "all_workspaces", is_flag=True, help="Stop all containers for the current project")
@pass_config
def down(config: Config, workspace: Optional[str], select: bool, force: bool, all_workspaces: bool) -> None:
    """Stop and remove the devcontainer.

    If no workspace is specified, interactive selection is used.

    Examples:
        dv down               # Interactive selection
        dv down main          # Stop main workspace (with confirmation)
        dv down main --force  # Stop without confirmation
        dv down --all         # Stop all containers for the project
        dv down --all --force # Stop all without confirmation
    """
    project = Project()

    if all_workspaces:
        workspaces = project.list_workspaces()
        if not workspaces:
            warning("No workspaces found")
            return

        stopped = 0
        for ws in workspaces:
            container = Container(ws.path)
            console.print(f"Stopping devcontainer in: [cyan]{ws.name}[/cyan]")
            if container.stop(force=force):
                success(f"Devcontainer stopped and removed: {ws.name}")
                stopped += 1
            else:
                console.print(f"[dim]No container running for: {ws.name}[/dim]")

        if stopped:
            success(f"Stopped {stopped} container(s)")
        else:
            warning("No running containers found")
        return

    # Resolve workspace
    workspace_path = _resolve_branch_with_selection(project, workspace, select)

    console.print(f"Stopping devcontainer in: [cyan]{workspace_path.name}[/cyan]")

    # Note: service.down will handle confirmation via Container.stop()
    container = Container(workspace_path)
    if container.stop(force=force):
        success("Devcontainer stopped and removed")
    else:
        warning("No devcontainer found")


@main.command()
@click.argument("workspace", required=False)
@click.argument("command", nargs=-1, required=True)
@click.option("--select", is_flag=True, help="Force interactive workspace selection")
@pass_config
def exec(
    config: Config, workspace: Optional[str], command: tuple[str, ...], select: bool
) -> None:
    """Execute a command in the devcontainer.

    If no workspace is specified, interactive selection is used.

    Examples:
        dv exec -- ls -la        # Interactive selection
        dv exec main -- ls -la   # Execute in main workspace
        dv exec main -- npm test # Run tests
    """
    project = Project()
    service = DevcontainerService(config)

    # Resolve workspace
    workspace_path = _resolve_branch_with_selection(project, workspace, select)

    service.exec(workspace_path, list(command), interactive=False)


@main.command()
@click.argument("workspace", required=True)
@click.argument("image")
@pass_config
def template(config: Config, workspace: str, image: str) -> None:
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

    # Get workspace path
    try:
        workspace_path = project.resolve_workspace(workspace)
    except ValueError as e:
        error(str(e))
        sys.exit(1)

    devcontainer_dir = workspace_path / ".devcontainer"
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
    project_name = workspace_path.name
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
    """Clone a repository with DV workspace directory structure.

    Examples:
        dv clone git@github.com:user/repo.git
        dv clone https://github.com/user/repo.git my-project
    """
    service = RepositoryService(config)

    console.print(f"Cloning {url}...")

    try:
        result = service.clone_as_regular(url, name)

        success(f"Repository cloned to {result.project_dir}")
        console.print(f"Default workspace: [cyan]{result.default_branch}[/cyan]")

        console.print(f"\n[bold]Next steps:[/bold]")
        console.print(f"  cd {result.project_dir.name}")
        console.print(f"  dv up {result.default_branch}")

        console.print("\n[bold]To add more workspaces:[/bold]")
        console.print("  dv workspace add")

    except subprocess.CalledProcessError as e:
        error(f"Failed to clone: {e}")
        sys.exit(1)


# Workspace subcommands
@main.group()
def workspace() -> None:
    """Manage workspaces and their devcontainers."""
    pass


main.add_command(workspace, name="ws")


@workspace.command("add")
@click.option("--start", is_flag=True, help="Automatically start devcontainer after creation")
@click.option("--clone", is_flag=True, help="Use full git clone instead of copying primary workspace")
@click.option("--branch", "-b", help="Git branch name (skip wizard)")
@click.option("--name", "-n", help="Workspace name (skip wizard)")
@click.option("--local", "is_local", is_flag=True,
              help="Create a local workspace not tied to a remote branch (skipped by dv clean)")
@pass_config
def workspace_add(
    config: Config,
    start: bool,
    clone: bool,
    branch: Optional[str],
    name: Optional[str],
    is_local: bool,
) -> None:
    """Create a new workspace (interactive wizard).

    Examples:
        dv workspace add                              # Interactive wizard (copies primary)
        dv workspace add -b feature/sc-123 -n task1   # Skip wizard
        dv workspace add --start                      # Create and start
        dv workspace add --clone                      # Use full git clone
        dv workspace add --local -n scratch           # Local workspace (not cleaned up)
    """
    project = Project()
    service = RepositoryService(config)

    if not project.is_dv_project:
        error("Not in a DV project")
        console.print("Run 'dv clone <url>' to set up a new project.")
        sys.exit(1)

    if is_local:
        # Local workspace: no branch selection, copied from primary as-is
        git_branch = ""
        if name:
            workspace_name = name
        else:
            workspace_name = prompt_for_workspace_name("local")
        console.print(f"[bold]Workspace name:[/bold] [cyan]{workspace_name}[/cyan]")
        console.print(f"[dim]Local workspace (copied from primary, skipped by dv clean)[/dim]")
    else:
        # Step 1: Get git branch name (wizard or option)
        if branch:
            git_branch = branch
        else:
            git_branch = select_or_enter_branch(project)

        console.print(f"\n[bold]Git branch:[/bold] [cyan]{git_branch}[/cyan]")

        # Step 2: Get workspace name (wizard or option)
        if name:
            workspace_name = name
        else:
            default_name = project._generate_default_workspace_name(git_branch)
            workspace_name = prompt_for_workspace_name(default_name)

        console.print(f"[bold]Workspace name:[/bold] [cyan]{workspace_name}[/cyan]")

    # Create the workspace
    console.print(f"\n[dim]Creating workspace...[/dim]")

    try:
        result = service.add_branch_with_container(
            project=project,
            git_branch=git_branch,
            workspace_name=workspace_name,
            start_container=start,
            use_external_dotfiles=False,
            use_git_clone=clone,
            local=is_local,
        )

        success(f"Workspace created at: {result.branch_path}")
        if is_local:
            console.print(f"  Workspace:  [cyan]{workspace_name}[/cyan]")
            console.print(f"  Type:       [dim]local[/dim]")
        else:
            console.print(f"  Git branch: [green]{git_branch}[/green]")
            console.print(f"  Workspace:  [cyan]{workspace_name}[/cyan]")

        if start:
            success("Devcontainer started with local dotfiles")
        else:
            console.print("\nTo start the devcontainer, run:")
            console.print(f"  dv up {workspace_name}")

    except (ValueError, RuntimeError, subprocess.CalledProcessError) as e:
        error(str(e))
        sys.exit(1)


@workspace.command("list")
def workspace_list() -> None:
    """List all workspaces with their git branch mappings."""
    project = Project()

    if not project.is_dv_project:
        error("Not in a DV project")
        sys.exit(1)

    workspaces = project.list_workspaces()

    if not workspaces:
        console.print("No workspaces found")
        return

    console.print(f"\nWorkspaces in [cyan]{project.path}[/cyan]:\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Status", width=12)
    table.add_column("Workspace", style="cyan")
    table.add_column("Git Branch", style="green")
    table.add_column("Local", width=7)
    table.add_column("Path", style="dim")

    for ws in workspaces:
        status_str = (
            f"[{ws.status.color}]{ws.status.icon}[/{ws.status.color}] {ws.status.value}"
        )
        branch_str = ws.branch if not ws.local else "[dim]—[/dim]"
        local_str = "[yellow]yes[/yellow]" if ws.local else "[dim]—[/dim]"
        table.add_row(status_str, ws.name, branch_str, local_str, str(ws.path))

    console.print(table)


@workspace.command("remove")
@click.argument("workspace_name", required=False)
@click.option("--select", is_flag=True, help="Force interactive workspace selection")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@pass_config
def workspace_remove(config: Config, workspace_name: Optional[str], select: bool, force: bool) -> None:
    """Remove a workspace directory and its devcontainer.

    If no workspace is specified, interactive selection is used.

    Examples:
        dv workspace remove                     # Interactive selection
        dv workspace remove feature-123         # With confirmation
        dv workspace remove feature-123 --force # Skip confirmation
    """
    project = Project()

    if not project.is_dv_project:
        error("Not in a DV project")
        sys.exit(1)

    # Interactive selection if no workspace provided or --select used
    if workspace_name is None or select:
        workspaces = project.list_workspaces()
        if not workspaces:
            error("No workspaces found")
            sys.exit(1)
        selected = select_workspace(workspaces)
        if not selected:
            error("No workspace selected")
            sys.exit(1)
        workspace_name = selected.name

    console.print(f"Removing workspace directory: [cyan]{workspace_name}[/cyan]")

    try:
        # First stop the container with confirmation
        workspace_path = project.resolve_workspace(workspace_name)
        container = Container(workspace_path)
        container.stop(force=force)

        # Then remove the directory with confirmation
        if project.remove_branch_directory(workspace_name, force=force):
            success(f"Workspace directory removed: {workspace_name}")
        else:
            console.print("[yellow]Operation cancelled[/yellow]")
            sys.exit(0)
    except ValueError as e:
        error(str(e))
        sys.exit(1)


@main.command()
@click.argument("workspace", required=False)
@pass_config
def status(config: Config, workspace: Optional[str]) -> None:
    """Show workspace and devcontainer status.

    If no workspace is specified, shows status for all workspaces.

    Examples:
        dv status              # Show all workspaces
        dv status main         # Show specific workspace details
    """
    project = Project()
    service = DevcontainerService(config)

    if not project.is_dv_project:
        console.print("Not in a DV project")
        console.print("\nRun 'dv clone <url>' to set up a new project.")
        return

    if workspace is None:
        # Show all workspaces (same as workspace list)
        workspaces = project.list_workspaces()

        if not workspaces:
            console.print("No workspaces found")
            return

        console.print(f"\nWorkspaces in [cyan]{project.path}[/cyan]:\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Status", width=12)
        table.add_column("Workspace", style="cyan")
        table.add_column("Git Branch", style="green")
        table.add_column("Local", width=7)
        table.add_column("Path", style="dim")

        for ws in workspaces:
            status_str = (
                f"[{ws.status.color}]{ws.status.icon}[/{ws.status.color}] {ws.status.value}"
            )
            branch_str = ws.branch if not ws.local else "[dim]—[/dim]"
            local_str = "[yellow]yes[/yellow]" if ws.local else "[dim]—[/dim]"
            table.add_row(status_str, ws.name, branch_str, local_str, str(ws.path))

        console.print(table)
    else:
        # Show specific workspace details
        try:
            path = project.resolve_workspace(workspace)
            status_val = service.get_status(path)

            # Get branch
            result = subprocess.run(
                ["git", "-C", str(path), "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=False,
            )
            branch_name = result.stdout.strip() or "unknown"

            console.print(f"\nWorkspace: [cyan]{path.name}[/cyan]")
            console.print(f"  Path:      {path}")
            console.print(f"  Branch:    {branch_name}")
            console.print(
                f"  Container: [{status_val.color}]{status_val.value}[/{status_val.color}]"
            )

        except ValueError as e:
            error(str(e))
            sys.exit(1)


@main.command()
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.option("--dry-run", is_flag=True, help="Show what would be removed without removing")
def clean(force: bool, dry_run: bool) -> None:
    """Remove workspaces whose remote branches no longer exist.

    Fetches latest remote branch info, lists all stale workspaces, then asks
    for confirmation once before removing all of them. Workspaces created with
    --local are never removed.

    Examples:
        dv clean            # List stale workspaces, confirm once, then remove all
        dv clean --force    # Remove without confirmation
        dv clean --dry-run  # Preview only, no changes
    """
    project = Project()

    if not project.is_dv_project:
        error("Not in a DV project")
        sys.exit(1)

    console.print("[dim]Fetching remote branch info...[/dim]")
    try:
        stale = project.get_stale_workspaces()
    except RuntimeError as e:
        error(str(e))
        sys.exit(1)

    if not stale:
        success("No stale workspaces found")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Workspace", style="cyan")
    table.add_column("Branch (deleted from remote)", style="red")
    for ws_name, branch in stale:
        branch_display = branch if branch else "[dim]—[/dim]"
        table.add_row(ws_name, branch_display)
    console.print(table)

    if dry_run:
        console.print(f"[yellow]Dry run: {len(stale)} workspace(s) would be removed[/yellow]")
        return

    if not force:
        if not Confirm.ask(f"Remove these {len(stale)} workspace(s)?", default=False):
            console.print("[yellow]Cancelled[/yellow]")
            return

    for ws_name, _branch in stale:
        try:
            workspace_path = project.resolve_workspace(ws_name)
            container = Container(workspace_path)
            container.stop(force=True)
            project.remove_branch_directory(ws_name, force=True)
            success(f"Removed: {ws_name}")
        except ValueError as e:
            error(str(e))


@main.command()
@pass_config
def migrate(config: Config) -> None:
    """Migrate existing DV project to use project-config.json.

    Scans all git repositories in the current directory and creates
    a project-config.json mapping them (directory name → git branch).
    """
    from datetime import datetime

    project_dir = Path.cwd()
    config_path = project_dir / "project-config.json"

    if config_path.exists():
        error("project-config.json already exists")
        console.print("This project appears to be already migrated.")
        sys.exit(1)

    console.print("[bold]Scanning for git repositories...[/bold]\n")

    # Find all git repos in immediate subdirectories
    git_repos = []
    for item in project_dir.iterdir():
        if item.is_dir() and (item / ".git").is_dir():
            # Get current branch
            result = subprocess.run(
                ["git", "-C", str(item), "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=False,
            )
            branch = result.stdout.strip() or "unknown"
            git_repos.append((item.name, branch))

    if not git_repos:
        error("No git repositories found in current directory")
        sys.exit(1)

    # Show what will be migrated
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Workspace", style="cyan")
    table.add_column("Git Branch", style="green")

    for workspace_name, branch in git_repos:
        table.add_row(workspace_name, branch)

    console.print(table)
    console.print()

    if not Confirm.ask("Create project-config.json with these mappings?", default=True):
        console.print("Migration cancelled")
        return

    # Create config
    mappings = {
        workspace_name: {
            "git_branch": branch,
            "created_at": datetime.now().isoformat()
        }
        for workspace_name, branch in git_repos
    }

    config_data = {"workspaces": mappings}

    with open(config_path, 'w') as f:
        json.dump(config_data, f, indent=2)
        f.write('\n')

    success(f"Created {config_path}")
    console.print(f"Migrated {len(git_repos)} workspaces")


if __name__ == "__main__":
    main()
