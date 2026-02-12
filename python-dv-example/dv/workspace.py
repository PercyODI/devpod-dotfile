"""Workspace and git worktree management."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .container import Container, ContainerStatus


@dataclass
class WorktreeInfo:
    """Information about a git worktree."""

    path: Path
    branch: str
    status: ContainerStatus

    @property
    def name(self) -> str:
        """Get worktree name (directory basename)."""
        return self.path.name


class Workspace:
    """Represents a workspace with git worktree support."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or Path.cwd()
        self.bare_repo = self._find_bare_repo()

    def _find_bare_repo(self) -> Optional[Path]:
        """Find the .bare directory in parent directories."""
        current = self.path.resolve()
        while current != current.parent:
            bare_path = current / ".bare"
            if bare_path.is_dir():
                return bare_path
            current = current.parent
        return None

    @property
    def root(self) -> Path:
        """Get the worktree root directory (parent of .bare)."""
        if self.bare_repo:
            return self.bare_repo.parent
        return self.path

    @property
    def is_worktree_project(self) -> bool:
        """Check if this is a worktree-enabled project."""
        return self.bare_repo is not None

    def is_valid_worktree(self, path: Path) -> bool:
        """Check if a directory is a valid git worktree."""
        if not path.is_dir():
            return False
        try:
            subprocess.run(
                ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def list_worktrees(self) -> list[WorktreeInfo]:
        """List all worktrees with their status."""
        if not self.bare_repo:
            return []

        try:
            result = subprocess.run(
                ["git", f"--git-dir={self.bare_repo}", "worktree", "list"],
                capture_output=True,
                text=True,
                check=True,
            )

            worktrees = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split()
                path = Path(parts[0])

                # Skip .bare directory itself
                if path == self.bare_repo or ".bare" in str(path):
                    continue

                # Extract branch name from [branch-name] format
                branch = "detached"
                if "[" in line and "]" in line:
                    branch = line[line.index("[") + 1:line.index("]")]

                container = Container(path)
                status = container.get_status()

                worktrees.append(WorktreeInfo(path=path, branch=branch, status=status))

            return worktrees

        except subprocess.CalledProcessError:
            return []

    def get_worktree(self, name: str) -> Optional[Path]:
        """Get worktree path by name."""
        candidate = self.root / name
        if self.is_valid_worktree(candidate):
            return candidate
        return None

    def get_current_worktree(self) -> Optional[WorktreeInfo]:
        """Get info about the current worktree."""
        if not self.is_worktree_project:
            return None

        try:
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            )
            branch = result.stdout.strip() or "detached"

            container = Container(self.path)
            status = container.get_status()

            return WorktreeInfo(path=self.path, branch=branch, status=status)

        except subprocess.CalledProcessError:
            return None

    def resolve_worktree(self, name: Optional[str] = None) -> Path:
        """
        Resolve which worktree to operate on.

        Simple logic:
        1. If name provided and valid → use it
        2. Otherwise → use current directory

        No magic, no interactive prompts in this function.
        """
        if name:
            worktree = self.get_worktree(name)
            if not worktree:
                raise ValueError(f"Worktree not found: {name}")
            return worktree

        # Use current directory
        return self.path

    def list_branches(self) -> list[str]:
        """List all available branches (local and remote)."""
        if not self.bare_repo:
            return []

        try:
            result = subprocess.run(
                ["git", f"--git-dir={self.bare_repo}", "branch", "-a"],
                capture_output=True,
                text=True,
                check=True,
            )

            branches = set()
            for line in result.stdout.split("\n"):
                line = line.strip().lstrip("* ")
                if not line or "HEAD" in line:
                    continue

                # Remove remotes/origin/ prefix
                if line.startswith("remotes/origin/"):
                    line = line.replace("remotes/origin/", "")

                branches.add(line)

            return sorted(branches)

        except subprocess.CalledProcessError:
            return []

    def add_worktree(self, branch: str) -> Path:
        """Create a new worktree for the given branch."""
        if not self.bare_repo:
            raise RuntimeError("Not in a worktree-enabled project")

        worktree_path = self.root / branch

        if worktree_path.exists():
            raise ValueError(f"Worktree already exists: {branch}")

        # Check if branch exists locally
        local_exists = subprocess.run(
            ["git", f"--git-dir={self.bare_repo}", "show-ref", "--verify", f"refs/heads/{branch}"],
            capture_output=True,
        ).returncode == 0

        remote_exists = subprocess.run(
            ["git", f"--git-dir={self.bare_repo}", "show-ref", "--verify", f"refs/remotes/origin/{branch}"],
            capture_output=True,
        ).returncode == 0

        # Create worktree
        cmd = ["git", f"--git-dir={self.bare_repo}", "worktree", "add", "--relative-paths", str(worktree_path)]

        if not local_exists and remote_exists:
            # Create tracking branch
            cmd.extend(["-b", branch, f"origin/{branch}"])
        elif not local_exists:
            # Create new branch
            cmd.extend(["-b", branch])
        else:
            # Use existing branch
            cmd.append(branch)

        subprocess.run(cmd, check=True)
        return worktree_path

    def remove_worktree(self, name: str) -> bool:
        """Remove a worktree and its container."""
        if not self.bare_repo:
            return False

        worktree_path = self.get_worktree(name)
        if not worktree_path:
            raise ValueError(f"Worktree not found: {name}")

        # Stop container first
        container = Container(worktree_path)
        container.stop()

        # Remove worktree
        try:
            subprocess.run(
                ["git", f"--git-dir={self.bare_repo}", "worktree", "remove", str(worktree_path), "--force"],
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False
