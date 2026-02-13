"""Project and git branch directory management."""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.prompt import Confirm

from .container import Container, ContainerStatus


@dataclass
class BranchInfo:
    """Information about a branch directory."""

    path: Path
    branch: str
    status: ContainerStatus

    @property
    def name(self) -> str:
        """Get branch directory name (directory basename)."""
        return self.path.name


class Project:
    """Represents a DV project with branch directories."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or Path.cwd()
        self._validate_location()

    @staticmethod
    def _validate_branch_name(branch_name: str) -> None:
        """Validate branch name to prevent path traversal attacks.

        Args:
            branch_name: Branch name to validate

        Raises:
            ValueError: If branch name contains invalid characters
        """
        if not branch_name:
            raise ValueError("Branch name cannot be empty")

        # Check for path traversal attempts
        if '/' in branch_name or '\\' in branch_name:
            raise ValueError(
                f"Invalid branch name '{branch_name}': cannot contain path separators"
            )

        if '..' in branch_name:
            raise ValueError(
                f"Invalid branch name '{branch_name}': cannot contain '..'"
            )

        # Check for other problematic characters
        if branch_name.startswith('.'):
            raise ValueError(
                f"Invalid branch name '{branch_name}': cannot start with '.'"
            )

    def _validate_location(self) -> None:
        """Validate that commands are run from parent directory.

        Raises:
            RuntimeError: If inside branch subdirectory
        """
        # Check if we're inside a branch subdirectory
        if (self.path / ".git").is_dir():
            # We're in a git repository - check if parent has other branch dirs
            parent = self.path.parent
            if parent.exists():
                branch_dirs = self._find_branch_directories(parent)
                if len(branch_dirs) > 1:
                    raise RuntimeError(
                        f"You appear to be inside a branch directory: {self.path.name}\n"
                        f"DV commands must be run from the parent directory: {parent}\n"
                        f"Run: cd {parent}"
                    )

    def _find_branch_directories(self, search_path: Optional[Path] = None) -> list[Path]:
        """Scan immediate subdirectories for valid git repos.

        Args:
            search_path: Directory to search in (defaults to self.path)

        Returns:
            List of paths to branch directories
        """
        search_path = search_path or self.path
        branch_dirs = []

        if not search_path.is_dir():
            return branch_dirs

        for item in search_path.iterdir():
            if item.is_dir() and self._is_valid_git_repo(item):
                branch_dirs.append(item)

        return sorted(branch_dirs, key=lambda p: p.name)

    def _is_valid_git_repo(self, path: Path) -> bool:
        """Validate using git rev-parse --git-dir.

        Args:
            path: Path to check

        Returns:
            True if path is a valid git repository
        """
        try:
            subprocess.run(
                ["git", "-C", str(path), "rev-parse", "--git-dir"],
                capture_output=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    @property
    def is_dv_project(self) -> bool:
        """Check if this is a DV project (has branch directories)."""
        return len(self._find_branch_directories()) > 0

    def list_branch_directories(self) -> list[BranchInfo]:
        """List all branch directories with their status.

        Returns:
            List of BranchInfo for each branch directory
        """
        branch_dirs = self._find_branch_directories()
        results = []

        for branch_dir in branch_dirs:
            # Get current branch
            try:
                result = subprocess.run(
                    ["git", "-C", str(branch_dir), "branch", "--show-current"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                branch = result.stdout.strip() or "detached"
            except subprocess.CalledProcessError:
                branch = "unknown"

            # Get container status
            container = Container(branch_dir)
            status = container.get_status()

            results.append(BranchInfo(path=branch_dir, branch=branch, status=status))

        return results

    def resolve_branch(self, name: str) -> Path:
        """Map branch name to directory path.

        Args:
            name: Branch directory name

        Returns:
            Path to branch directory

        Raises:
            ValueError: If branch directory not found or invalid
        """
        # Validate branch name first
        self._validate_branch_name(name)

        candidate = self.path / name

        # Security check: ensure resolved path doesn't escape project directory
        try:
            candidate_resolved = candidate.resolve()
            project_resolved = self.path.resolve()

            if not candidate_resolved.is_relative_to(project_resolved):
                raise ValueError(
                    f"Invalid branch directory path: {name} (path traversal detected)"
                )
        except (ValueError, OSError) as e:
            raise ValueError(f"Invalid branch directory: {name}")

        if self._is_valid_git_repo(candidate):
            return candidate
        raise ValueError(f"Branch directory not found: {name}")

    def get_primary_branch(self) -> str:
        """Find main or master directory.

        Returns:
            Name of primary branch (main, master, or first alphabetically)

        Raises:
            RuntimeError: If no branch directories exist
        """
        branch_dirs = self._find_branch_directories()
        if not branch_dirs:
            raise RuntimeError("No branch directories found")

        # Prefer main or master
        for branch_dir in branch_dirs:
            if branch_dir.name in ("main", "master"):
                return branch_dir.name

        # Fall back to first alphabetically
        return branch_dirs[0].name

    def _get_remote_url(self) -> str:
        """Get origin URL from primary branch's .git/config.

        Returns:
            Remote origin URL

        Raises:
            RuntimeError: If no primary branch or no remote URL found
        """
        primary_branch = self.get_primary_branch()
        primary_path = self.path / primary_branch

        try:
            result = subprocess.run(
                ["git", "-C", str(primary_path), "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            raise RuntimeError(f"Could not get remote URL from {primary_branch}")

    def add_branch_directory(self, branch_name: str, use_git_clone: bool = False) -> Path:
        """Add a new branch directory.

        Args:
            branch_name: Name of branch to create directory for
            use_git_clone: If True, use full git clone; if False, use local clone

        Returns:
            Path to new branch directory

        Raises:
            ValueError: If directory already exists or invalid branch name
            RuntimeError: If branch doesn't exist remotely
        """
        # Validate branch name first
        self._validate_branch_name(branch_name)

        branch_dir = self.path / branch_name

        # Security check: ensure path doesn't escape project directory
        try:
            branch_dir_resolved = branch_dir.resolve()
            project_resolved = self.path.resolve()

            if not branch_dir_resolved.is_relative_to(project_resolved):
                raise ValueError(
                    f"Invalid branch directory path: {branch_name} (path traversal detected)"
                )
        except (ValueError, OSError):
            raise ValueError(f"Invalid branch name: {branch_name}")

        if branch_dir.exists():
            raise ValueError(f"Branch directory already exists: {branch_name}")

        # Get remote URL and primary branch
        remote_url = self._get_remote_url()
        primary_branch = self.get_primary_branch()
        primary_path = self.path / primary_branch

        # Fetch in primary branch first to ensure branch exists remotely
        try:
            subprocess.run(
                ["git", "-C", str(primary_path), "fetch", "origin"],
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            raise RuntimeError("Failed to fetch from remote")

        # Check if branch exists remotely
        result = subprocess.run(
            ["git", "-C", str(primary_path), "ls-remote", "--heads", "origin", branch_name],
            capture_output=True,
            text=True,
        )
        if not result.stdout.strip():
            raise RuntimeError(
                f"Branch '{branch_name}' does not exist on remote.\n"
                f"Create it first with: cd {primary_branch} && git checkout -b {branch_name} && git push -u origin {branch_name}"
            )

        if use_git_clone:
            # Full git clone from remote
            subprocess.run(
                ["git", "clone", remote_url, "--branch", branch_name, str(branch_dir)],
                check=True,
            )
        else:
            # Local clone (fast)
            subprocess.run(
                ["git", "clone", "--local", str(primary_path), str(branch_dir)],
                check=True,
            )
            # Checkout target branch
            subprocess.run(
                ["git", "-C", str(branch_dir), "checkout", branch_name],
                check=True,
            )

        return branch_dir

    def remove_branch_directory(self, branch_name: str, force: bool = False) -> bool:
        """Remove a branch directory and its container.

        Args:
            branch_name: Name of branch directory to remove
            force: If True, skip confirmation prompt

        Returns:
            True if successful, False if cancelled

        Raises:
            ValueError: If directory doesn't exist or invalid branch name
        """
        # Validate branch name first
        self._validate_branch_name(branch_name)

        branch_dir = self.path / branch_name

        # Security check: ensure path doesn't escape project directory
        try:
            branch_dir_resolved = branch_dir.resolve()
            project_resolved = self.path.resolve()

            if not branch_dir_resolved.is_relative_to(project_resolved):
                raise ValueError(
                    f"Invalid branch directory path: {branch_name} (path traversal detected)"
                )
        except (ValueError, OSError):
            raise ValueError(f"Invalid branch name: {branch_name}")

        if not branch_dir.exists():
            raise ValueError(f"Branch directory not found: {branch_name}")

        # Show what will be deleted and ask for confirmation
        if not force:
            from rich.console import Console
            console = Console()
            console.print(f"\n[bold red]⚠️  DESTRUCTIVE ACTION[/bold red]")
            console.print(f"About to execute:")
            console.print(f"  [dim]$ rm -rf {branch_dir}[/dim]")
            console.print(f"  [yellow]All files and git history in this directory will be permanently lost.[/yellow]")

            if not Confirm.ask("Are you sure you want to continue?", default=False):
                console.print("[yellow]Operation cancelled[/yellow]")
                return False

        # Stop container first
        container = Container(branch_dir)
        stopped = container.stop()

        if stopped:
            from rich.console import Console
            console = Console()
            console.print(f"  Stopped and removed container")

        # Remove directory
        shutil.rmtree(branch_dir)
        return True

    def list_branches(self) -> list[str]:
        """List all available branches from remote.

        Returns:
            List of branch names from remote
        """
        if not self.is_dv_project:
            return []

        try:
            primary_branch = self.get_primary_branch()
            primary_path = self.path / primary_branch

            result = subprocess.run(
                ["git", "-C", str(primary_path), "branch", "-r"],
                capture_output=True,
                text=True,
                check=True,
            )

            branches = set()
            for line in result.stdout.split("\n"):
                line = line.strip()
                if not line or "HEAD" in line:
                    continue

                # Remove origin/ prefix
                if line.startswith("origin/"):
                    line = line.replace("origin/", "")

                branches.add(line)

            return sorted(branches)

        except (subprocess.CalledProcessError, RuntimeError):
            return []
