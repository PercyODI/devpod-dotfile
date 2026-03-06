"""Utility functions for dv."""

import subprocess
import sys
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from .config import Config
from .project import BranchInfo

if TYPE_CHECKING:
    from .project import Project

console = Console()
error_console = Console(stderr=True)


def run_devcontainer(
    command: list[str],
    workspace: Path,
    config: Config,
    check: bool = True,
    interactive: bool = False,
) -> subprocess.CompletedProcess:
    """Run a devcontainer CLI command."""
    cmd = ["devcontainer"] + command + ["--workspace-folder", str(workspace)]

    # Add remote environment args if applicable
    if command[0] in ("up", "exec"):
        cmd.extend(config.get_remote_env_args())

    if interactive:
        # Run with stdio connected for interactive commands
        return subprocess.run(cmd, check=check)
    else:
        return subprocess.run(cmd, check=check, capture_output=True, text=True)


def select_branch_directory(branch_dirs: list[BranchInfo]) -> Optional[BranchInfo]:
    """Interactive branch directory selection using rich."""
    if not branch_dirs:
        return None

    if len(branch_dirs) == 1:
        return branch_dirs[0]

    # Check if fzf is available
    if has_fzf():
        return _select_with_fzf(branch_dirs)

    # Fallback to simple numbered selection
    console.print("\n[bold]Select branch directory:[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Status", width=8)
    table.add_column("Name", style="cyan")
    table.add_column("Branch", style="green")

    for idx, bd in enumerate(branch_dirs, 1):
        status_str = f"[{bd.status.color}]{bd.status.icon}[/{bd.status.color}] {bd.status.value}"
        table.add_row(str(idx), status_str, bd.name, bd.branch)

    console.print(table)

    while True:
        choice = Prompt.ask("Enter number", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(branch_dirs):
                return branch_dirs[idx]
            console.print(f"[red]Invalid choice. Enter 1-{len(branch_dirs)}[/red]")
        except ValueError:
            console.print("[red]Invalid input. Enter a number.[/red]")


def select_branch(branches: list[str], prompt: str = "Select branch") -> Optional[str]:
    """Interactive branch selection."""
    if not branches:
        return None

    if has_fzf():
        return _select_with_fzf_simple(branches, prompt)

    # Fallback to simple selection
    console.print(f"\n[bold]{prompt}:[/bold]")
    for idx, branch in enumerate(branches, 1):
        console.print(f"  {idx}. {branch}")

    while True:
        choice = Prompt.ask("Enter number", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(branches):
                return branches[idx]
            console.print(f"[red]Invalid choice. Enter 1-{len(branches)}[/red]")
        except ValueError:
            console.print("[red]Invalid input. Enter a number.[/red]")


def has_fzf() -> bool:
    """Check if fzf is available."""
    return subprocess.run(["which", "fzf"], capture_output=True).returncode == 0


def _select_with_fzf(branch_dirs: list[BranchInfo]) -> Optional[BranchInfo]:
    """Select branch directory using fzf."""
    # Format lines for fzf
    lines = []
    for bd in branch_dirs:
        lines.append(f"{bd.status.icon} {bd.name} ({bd.branch})")

    try:
        result = subprocess.run(
            ["fzf", "--ansi", "--prompt=Select branch directory: ", "--height=40%", "--reverse"],
            input="\n".join(lines),
            capture_output=True,
            text=True,
            check=True,
        )
        selected = result.stdout.strip()

        # Find matching branch directory
        for idx, line in enumerate(lines):
            if line == selected:
                return branch_dirs[idx]

    except subprocess.CalledProcessError:
        return None

    return None


def _select_with_fzf_simple(items: list[str], prompt: str) -> Optional[str]:
    """Select from a simple list using fzf."""
    try:
        result = subprocess.run(
            ["fzf", "--prompt", f"{prompt}: ", "--height=40%", "--reverse"],
            input="\n".join(items),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def error(message: str) -> None:
    """Print error message and exit."""
    error_console.print(f"[red]Error:[/red] {message}")


def success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]✓[/green] {message}")


def warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]Warning:[/yellow] {message}")


def select_workspace(workspaces: list[BranchInfo]) -> Optional[BranchInfo]:
    """Interactive workspace selection using rich (alias for select_branch_directory)."""
    return select_branch_directory(workspaces)


def list_remote_branches(project: "Project") -> list[str]:
    """List all remote branches for the project.

    Args:
        project: Project instance

    Returns:
        List of remote branch names
    """
    primary_branch = project.get_primary_branch()
    primary_path = project.path / primary_branch / project.path.name

    # Fetch latest
    subprocess.run(
        ["git", "-C", str(primary_path), "fetch", "origin"],
        capture_output=True,
        check=False,
    )

    result = subprocess.run(
        ["git", "-C", str(primary_path), "branch", "-r"],
        capture_output=True,
        text=True,
        check=True,
    )

    branches = []
    for line in result.stdout.split("\n"):
        line = line.strip()
        if not line or "HEAD" in line:
            continue

        # Remove origin/ prefix
        if line.startswith("origin/"):
            line = line.replace("origin/", "")

        branches.append(line)

    return sorted(branches)


def select_or_enter_branch(project: "Project") -> str:
    """Interactive wizard to select or enter a branch name.

    Returns:
        Selected or entered branch name
    """
    console.print("\n[bold]Select or enter a branch:[/bold]")
    console.print("  1. Select from remote branches")
    console.print("  2. Enter branch name manually")

    choice = Prompt.ask("Enter choice", choices=["1", "2"], default="1")

    if choice == "1":
        # List remote branches
        console.print("\n[dim]Fetching remote branches...[/dim]")
        branches = list_remote_branches(project)

        if not branches:
            error("No remote branches found")
            sys.exit(1)

        # Use fzf if available, otherwise simple selection
        if has_fzf():
            return _select_branch_with_fzf(branches)
        else:
            return _select_branch_simple(branches)
    else:
        # Manual entry
        branch_name = Prompt.ask("\nEnter branch name")
        if not branch_name:
            error("Branch name cannot be empty")
            sys.exit(1)
        return branch_name


def _select_branch_with_fzf(branches: list[str]) -> str:
    """Select branch using fzf."""
    try:
        result = subprocess.run(
            ["fzf", "--height", "50%", "--reverse", "--prompt", "Branch: "],
            input="\n".join(branches),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        error("Selection cancelled")
        sys.exit(1)


def _select_branch_simple(branches: list[str]) -> str:
    """Select branch with simple numbered list."""
    console.print("\n[bold]Available branches:[/bold]")

    for idx, branch in enumerate(branches, 1):
        console.print(f"  {idx}. [cyan]{branch}[/cyan]")

    while True:
        choice = Prompt.ask("Enter number", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(branches):
                return branches[idx]
            console.print(f"[red]Invalid choice. Enter 1-{len(branches)}[/red]")
        except ValueError:
            console.print("[red]Invalid input. Enter a number.[/red]")


def prompt_for_workspace_name(default_name: str) -> str:
    """Prompt user for workspace name.

    Args:
        default_name: Default name to suggest

    Returns:
        User-entered or default workspace name
    """
    console.print(f"\n[bold]Workspace name:[/bold]")
    console.print(f"  Default: [cyan]{default_name}[/cyan]")

    workspace_name = Prompt.ask(
        "Enter workspace name (or press Enter for default)",
        default=default_name
    )

    return workspace_name
