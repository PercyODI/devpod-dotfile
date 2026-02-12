"""Utility functions for dv."""

import subprocess
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from .config import Config
from .workspace import WorktreeInfo

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


def select_worktree(worktrees: list[WorktreeInfo]) -> Optional[WorktreeInfo]:
    """Interactive worktree selection using rich."""
    if not worktrees:
        return None

    if len(worktrees) == 1:
        return worktrees[0]

    # Check if fzf is available
    if has_fzf():
        return _select_with_fzf(worktrees)

    # Fallback to simple numbered selection
    console.print("\n[bold]Select worktree:[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Status", width=8)
    table.add_column("Name", style="cyan")
    table.add_column("Branch", style="green")

    for idx, wt in enumerate(worktrees, 1):
        status_str = f"[{wt.status.color}]{wt.status.icon}[/{wt.status.color}] {wt.status.value}"
        table.add_row(str(idx), status_str, wt.name, wt.branch)

    console.print(table)

    while True:
        choice = Prompt.ask("Enter number", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(worktrees):
                return worktrees[idx]
            console.print(f"[red]Invalid choice. Enter 1-{len(worktrees)}[/red]")
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


def _select_with_fzf(worktrees: list[WorktreeInfo]) -> Optional[WorktreeInfo]:
    """Select worktree using fzf."""
    # Format lines for fzf
    lines = []
    for wt in worktrees:
        lines.append(f"{wt.status.icon} {wt.name} ({wt.branch})")

    try:
        result = subprocess.run(
            ["fzf", "--ansi", "--prompt=Select worktree: ", "--height=40%", "--reverse"],
            input="\n".join(lines),
            capture_output=True,
            text=True,
            check=True,
        )
        selected = result.stdout.strip()

        # Find matching worktree
        for idx, line in enumerate(lines):
            if line == selected:
                return worktrees[idx]

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
