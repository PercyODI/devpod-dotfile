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

    # Resolve which worktree to use
    if select:
        worktrees = ws.list_worktrees()
        if not worktrees:
            error("No worktrees found")
            sys.exit(1)
        selected = select_worktree(worktrees)
        if not selected:
            error("No worktree selected")
            sys.exit(1)
        workspace_path = selected.path
    else:
        try:
            workspace_path = ws.resolve_worktree(worktree)
        except ValueError as e:
            error(str(e))
            sys.exit(1)

    console.print(f"Starting devcontainer in: [cyan]{workspace_path.name}[/cyan]")

    # Build devcontainer up command
    cmd = [
        "up",
        "--workspace-folder", str(workspace_path),
        "--mount", "type=bind,source=/run/host-services/ssh-auth.sock,target=/ssh/agent",
        "--mount", f"type=bind,source={Path.home()}/.ssh/known_hosts,target=/ssh/known_hosts",
        "--mount-git-worktree-common-dir",
        "--update-remote-user-uid-default", "on",
        "--remove-existing-container",
    ]

    # Add remote env args
    cmd.extend(config.get_remote_env_args())

    if dotfile:
        # Use external dotfiles
        cmd.extend(["--dotfiles-repository", config.dotfiles_repo])
    else:
        # Mount local dotfiles
        cmd.extend(["--mount", f"type=bind,source={config.dotfiles_dir},target=/dotfiles"])

    # Run devcontainer up
    try:
        subprocess.run(["devcontainer"] + cmd, check=True)

        if not dotfile:
            # Run local dotfiles installation
            console.print("Running local dotfiles installation...")
            exec_cmd = [
                "exec",
                "--workspace-folder", str(workspace_path),
            ] + config.get_remote_env_args() + [
                "--", "bash", "-c", "cd /dotfiles && ./install.sh"
            ]
            subprocess.run(["devcontainer"] + exec_cmd, check=True)

        success(f"Devcontainer started with {'external' if dotfile else 'local'} dotfiles")

    except subprocess.CalledProcessError as e:
        error(f"Failed to start devcontainer: {e}")
        sys.exit(1)


@main.command()
@click.argument("worktree", required=False)
@click.option("--shell", "-s", is_flag=True, help="Open interactive shell instead of dev command")
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

    # Resolve worktree
    if select:
        worktrees = ws.list_worktrees()
        if not worktrees:
            error("No worktrees found")
            sys.exit(1)
        selected = select_worktree(worktrees)
        if not selected:
            error("No worktree selected")
            sys.exit(1)
        workspace_path = selected.path
    else:
        try:
            workspace_path = ws.resolve_worktree(worktree)
        except ValueError as e:
            error(str(e))
            sys.exit(1)

    # Build exec command
    cmd = [
        "exec",
        "--workspace-folder", str(workspace_path),
    ] + config.get_remote_env_args()

    if shell:
        cmd.extend(["--", "zsh"])
    else:
        cmd.extend(["--", "zsh", "-ic", "dev"])

    # Run interactively
    try:
        subprocess.run(["devcontainer"] + cmd, check=False)
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

    # Resolve worktree
    if select:
        worktrees = ws.list_worktrees()
        if not worktrees:
            error("No worktrees found")
            sys.exit(1)
        selected = select_worktree(worktrees)
        if not selected:
            error("No worktree selected")
            sys.exit(1)
        workspace_path = selected.path
    else:
        try:
            workspace_path = ws.resolve_worktree(worktree)
        except ValueError as e:
            error(str(e))
            sys.exit(1)

    container = Container(workspace_path)
    console.print(f"Stopping devcontainer in: [cyan]{workspace_path.name}[/cyan]")

    if container.stop():
        success("Devcontainer stopped and removed")
    else:
        warning("No devcontainer found")


@main.command()
@click.argument("worktree", required=False)
@click.argument("command", nargs=-1, required=True)
@click.option("--select", is_flag=True, help="Interactive worktree selection")
@pass_config
def exec(config: Config, worktree: Optional[str], command: tuple[str, ...], select: bool) -> None:
    """Execute a command in the devcontainer.

    Examples:
        dv exec -- ls -la
        dv exec main -- npm test
        dv exec --select -- bash
    """
    ws = Workspace()

    # Resolve worktree
    if select:
        worktrees = ws.list_worktrees()
        if not worktrees:
            error("No worktrees found")
            sys.exit(1)
        selected = select_worktree(worktrees)
        if not selected:
            error("No worktree selected")
            sys.exit(1)
        workspace_path = selected.path
    else:
        try:
            workspace_path = ws.resolve_worktree(worktree)
        except ValueError as e:
            error(str(e))
            sys.exit(1)

    # Build exec command
    cmd = [
        "exec",
        "--workspace-folder", str(workspace_path),
    ] + config.get_remote_env_args() + ["--"] + list(command)

    subprocess.run(["devcontainer"] + cmd, check=False)


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
    # Derive project name from URL if not provided
    if not name:
        name = Path(url).stem

    project_dir = Path.cwd() / name
    bare_repo = project_dir / ".bare"

    console.print(f"Cloning {url} as bare repository...")

    try:
        # Create project directory and clone
        project_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--bare", url, str(bare_repo)],
            check=True,
        )

        # Create .git file pointing to .bare
        (project_dir / ".git").write_text("gitdir: ./.bare\n")

        # Get default branch
        result = subprocess.run(
            ["git", "--git-dir", str(bare_repo), "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        default_branch = result.stdout.strip() or "main"

        success(f"Bare repository created at {bare_repo}")
        console.print(f"Creating worktree for branch: [cyan]{default_branch}[/cyan]")

        # Create worktree
        subprocess.run(
            ["git", "worktree", "add", "--relative-paths", default_branch, default_branch],
            cwd=project_dir,
            check=True,
        )

        success("Project cloned and worktree structure set up!")
        console.print(f"\n[bold]Next steps:[/bold]")
        console.print(f"  cd {name}/{default_branch}")
        console.print("\n[bold]Available commands:[/bold]")
        console.print("  [cyan]dv up[/cyan]              - Start the devcontainer")
        console.print("  [cyan]dv worktree add[/cyan]    - Create a new worktree for a branch")
        console.print("  [cyan]dv worktree list[/cyan]   - List all worktrees")
        console.print("  [cyan]dv exec[/cyan]            - Execute a command in the devcontainer")

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
def worktree_add(config: Config, branch: Optional[str], no_start: bool, select: bool) -> None:
    """Create a new worktree and start its devcontainer.

    Examples:
        dv worktree add feature-123
        dv worktree add --select
        dv worktree add new-feature --no-start
    """
    ws = Workspace()

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
        worktree_path = ws.add_worktree(branch)
        success(f"Worktree created at: {worktree_path}")

        if not no_start:
            console.print("Starting devcontainer...")
            # Change to worktree and run up
            up_ws = Workspace(worktree_path)
            workspace_path = up_ws.path

            cmd = [
                "up",
                "--workspace-folder", str(workspace_path),
                "--mount", "type=bind,source=/run/host-services/ssh-auth.sock,target=/ssh/agent",
                "--mount", f"type=bind,source={Path.home()}/.ssh/known_hosts,target=/ssh/known_hosts",
                "--mount-git-worktree-common-dir",
                "--update-remote-user-uid-default", "on",
                "--remove-existing-container",
            ]
            cmd.extend(config.get_remote_env_args())

            subprocess.run(["devcontainer"] + cmd, check=True)
            success("Devcontainer started")
        else:
            console.print("\nTo start the devcontainer, run:")
            console.print(f"  cd {worktree_path}")
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
        status_str = f"[{wt.status.color}]{wt.status.icon}[/{wt.status.color}] {wt.status.value}"
        table.add_row(status_str, wt.name, wt.branch, str(wt.path))

    console.print(table)


@worktree.command("remove")
@click.argument("branch", required=False)
@click.option("--select", is_flag=True, help="Interactive selection")
def worktree_remove(branch: Optional[str], select: bool) -> None:
    """Remove a worktree and its devcontainer.

    Examples:
        dv worktree remove feature-123
        dv worktree remove --select
    """
    ws = Workspace()

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
        if ws.remove_worktree(branch):
            success(f"Worktree removed: {branch}")
        else:
            error("Failed to remove worktree")
            sys.exit(1)
    except ValueError as e:
        error(str(e))
        sys.exit(1)


@main.command()
@click.argument("worktree", required=False)
def status(worktree: Optional[str]) -> None:
    """Show worktree and devcontainer status.

    Examples:
        dv status              # Show current worktree + list others
        dv status main         # Show specific worktree
    """
    ws = Workspace()

    if not ws.is_worktree_project:
        console.print("Not in a worktree-enabled project")
        console.print("\nRun 'dv clone <url>' to set up a new project with worktrees.")
        return

    # Specific worktree requested
    if worktree:
        try:
            path = ws.resolve_worktree(worktree)
            container = Container(path)
            status_val = container.get_status()

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
            console.print(f"  Container: [{status_val.color}]{status_val.value}[/{status_val.color}]")

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
        console.print(f"  Container: [{current.status.color}]{current.status.value}[/{current.status.color}]")
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
