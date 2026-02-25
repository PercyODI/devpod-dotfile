"""Project and git branch directory management."""

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.prompt import Confirm

from .container import Container, ContainerStatus


@dataclass
class WorkspaceMetadata:
    """Metadata for a workspace in project-config.json."""

    git_branch: str
    created_at: str


@dataclass
class BranchInfo:
    """Information about a branch directory."""

    path: Path
    branch: str
    status: ContainerStatus

    @property
    def name(self) -> str:
        """Get workspace directory name (outer workspace dir, parent of the git repo)."""
        return self.path.parent.name


class Project:
    """Represents a DV project with branch directories."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or Path.cwd()
        self._validate_location()

    def _get_config_path(self) -> Path:
        """Return path to project-config.json."""
        return self.path / "project-config.json"

    def _load_config(self) -> dict[str, WorkspaceMetadata]:
        """Load project-config.json and return workspace mappings.

        Returns:
            Dictionary mapping workspace names to metadata
        """
        config_path = self._get_config_path()
        if not config_path.exists():
            return {}

        with open(config_path, 'r') as f:
            data = json.load(f)

        return {
            workspace_name: WorkspaceMetadata(**meta)
            for workspace_name, meta in data.get('workspaces', {}).items()
        }

    def _save_config(self, mappings: dict[str, WorkspaceMetadata]) -> None:
        """Save workspace mappings to project-config.json.

        Args:
            mappings: Dictionary mapping workspace names to metadata
        """
        config_path = self._get_config_path()

        data = {
            'workspaces': {
                workspace_name: {
                    'git_branch': meta.git_branch,
                    'created_at': meta.created_at
                }
                for workspace_name, meta in mappings.items()
            }
        }

        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')

    @staticmethod
    def _validate_branch_name(branch_name: str) -> None:
        """Validate git branch name.

        Args:
            branch_name: Branch name to validate

        Raises:
            ValueError: If branch name contains invalid characters
        """
        if not branch_name:
            raise ValueError("Branch name cannot be empty")

        # Allow slashes for git branch names
        # Only check for dangerous patterns
        if '..' in branch_name:
            raise ValueError(
                f"Invalid branch name '{branch_name}': cannot contain '..'"
            )

    @staticmethod
    def _validate_workspace_name(workspace_name: str) -> None:
        """Validate workspace name (more restrictive than branch names).

        Args:
            workspace_name: Workspace name to validate

        Raises:
            ValueError: If workspace name contains invalid characters
        """
        if not workspace_name:
            raise ValueError("Workspace name cannot be empty")

        # Check for path traversal attempts
        if '/' in workspace_name or '\\' in workspace_name:
            raise ValueError(
                f"Invalid workspace name '{workspace_name}': cannot contain path separators"
            )

        if '..' in workspace_name:
            raise ValueError(
                f"Invalid workspace name '{workspace_name}': cannot contain '..'"
            )

        if workspace_name.startswith('.'):
            raise ValueError(
                f"Invalid workspace name '{workspace_name}': cannot start with '.'"
            )

    def _validate_location(self) -> None:
        """Validate that commands are run from parent directory.

        Raises:
            RuntimeError: If inside workspace subdirectory
        """
        # Check if we're inside a workspace subdirectory
        if (self.path / ".git").is_dir():
            # We're in a git repository - check if parent has other workspaces
            parent = self.path.parent
            if parent.exists():
                workspaces = self._find_workspaces(parent)
                if len(workspaces) > 1:
                    raise RuntimeError(
                        f"You appear to be inside a workspace directory: {self.path.name}\n"
                        f"DV commands must be run from the parent directory: {parent}\n"
                        f"Run: cd {parent}"
                    )

    def _find_workspaces(self, search_path: Optional[Path] = None) -> list[Path]:
        """Scan workspace subdirectories listed in project-config.json.

        Args:
            search_path: Directory to search in (defaults to self.path)

        Returns:
            List of paths to workspace directories
        """
        search_path = search_path or self.path

        # Load config to get valid workspace names
        # Need to temporarily set path if using search_path
        if search_path != self.path:
            original_path = self.path
            self.path = search_path
            mappings = self._load_config()
            self.path = original_path
        else:
            mappings = self._load_config()

        repo_name = search_path.name  # project dir name = repo name
        workspaces = []
        for workspace_name in mappings.keys():
            workspace_path = search_path / workspace_name
            if workspace_path.is_dir() and self._is_valid_git_repo(workspace_path / repo_name):
                workspaces.append(workspace_path / repo_name)

        return sorted(workspaces, key=lambda p: p.parent.name)

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
        """Check if this is a DV project (has project-config.json)."""
        return self._get_config_path().exists()

    def list_workspaces(self) -> list[BranchInfo]:
        """List all workspaces with their status and git branch mapping.

        Returns:
            List of BranchInfo for each workspace
        """
        workspaces = self._find_workspaces()
        mappings = self._load_config()
        results = []

        for workspace_path in workspaces:
            workspace_name = workspace_path.parent.name  # outer workspace dir name

            # Get git branch from config (required)
            if workspace_name in mappings:
                git_branch = mappings[workspace_name].git_branch
            else:
                # This shouldn't happen if config is in sync
                git_branch = "unknown"

            # Get container status
            container = Container(workspace_path)
            status = container.get_status()

            results.append(BranchInfo(
                path=workspace_path,
                branch=git_branch,  # Now shows actual git branch name
                status=status
            ))

        return results

    def list_branch_directories(self) -> list[BranchInfo]:
        """Deprecated: Use list_workspaces() instead."""
        return self.list_workspaces()

    def resolve_workspace(self, workspace_name: str) -> Path:
        """Map workspace name to workspace path.

        Args:
            workspace_name: Workspace name (not git branch name)

        Returns:
            Path to workspace directory

        Raises:
            ValueError: If workspace not found in config or invalid
        """
        # Validate workspace name
        self._validate_workspace_name(workspace_name)

        # Check if workspace exists in config
        mappings = self._load_config()
        if workspace_name not in mappings:
            raise ValueError(
                f"Workspace '{workspace_name}' not found in project config.\n"
                f"Run 'dv workspace list' to see available workspaces."
            )

        candidate = self.path / workspace_name / self.path.name  # inner git repo path

        # Security check: ensure resolved path doesn't escape project directory
        try:
            candidate_resolved = candidate.resolve()
            project_resolved = self.path.resolve()

            if not candidate_resolved.is_relative_to(project_resolved):
                raise ValueError(
                    f"Invalid workspace path: {workspace_name} (path traversal detected)"
                )
        except (ValueError, OSError):
            raise ValueError(f"Invalid workspace: {workspace_name}")

        if self._is_valid_git_repo(candidate):
            return candidate

        raise ValueError(
            f"Workspace '{workspace_name}' exists in config but is not a valid git repository"
        )

    def resolve_branch(self, name: str) -> Path:
        """Deprecated: Use resolve_workspace() instead."""
        return self.resolve_workspace(name)

    def get_primary_branch(self) -> str:
        """Find primary workspace name.

        Returns:
            Workspace name of primary branch (main, master, or first alphabetically)

        Raises:
            RuntimeError: If no workspaces exist
        """
        mappings = self._load_config()
        if not mappings:
            raise RuntimeError("No workspaces found")

        # Look for workspace mapped to 'main' or 'master' branch
        for workspace_name, meta in mappings.items():
            if meta.git_branch in ("main", "master"):
                return workspace_name

        # Fall back to first alphabetically
        return sorted(mappings.keys())[0]

    def _generate_default_workspace_name(self, git_branch: str) -> str:
        """Generate default workspace name from git branch name.

        Args:
            git_branch: Git branch name (e.g., 'feature/sc-18234/update-file')

        Returns:
            Sanitized workspace name with timestamp
            (e.g., 'feature-sc-18234-update-file-20260213143022')
        """
        # Replace slashes with hyphens
        sanitized = git_branch.replace('/', '-').replace('\\', '-')

        # Remove any other problematic characters
        sanitized = ''.join(c if c.isalnum() or c in '-_' else '-' for c in sanitized)

        # Add timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

        return f"{sanitized}-{timestamp}"

    def _get_remote_url(self) -> str:
        """Get origin URL from primary branch's .git/config.

        Returns:
            Remote origin URL

        Raises:
            RuntimeError: If no primary branch or no remote URL found
        """
        primary_branch = self.get_primary_branch()
        primary_path = self.path / primary_branch / self.path.name

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

    def add_workspace(
        self,
        git_branch: str,
        workspace_name: str,
        use_git_clone: bool = False
    ) -> Path:
        """Add a new workspace with config mapping.

        Args:
            git_branch: Git branch name (can contain slashes)
            workspace_name: Workspace name to create (filesystem safe)
            use_git_clone: If True, use full git clone; if False, copy primary workspace

        Returns:
            Path to new workspace directory

        Raises:
            ValueError: If workspace already exists or invalid names
            RuntimeError: If fetch from remote fails
        """
        # Validate both names
        self._validate_branch_name(git_branch)
        self._validate_workspace_name(workspace_name)

        workspace_dir = self.path / workspace_name

        # Security check
        try:
            workspace_dir_resolved = workspace_dir.resolve()
            project_resolved = self.path.resolve()

            if not workspace_dir_resolved.is_relative_to(project_resolved):
                raise ValueError(
                    f"Invalid workspace path: {workspace_name} (path traversal detected)"
                )
        except (ValueError, OSError):
            raise ValueError(f"Invalid workspace name: {workspace_name}")

        if workspace_dir.exists():
            raise ValueError(f"Workspace already exists: {workspace_name}")

        # Check if workspace name already in config
        mappings = self._load_config()
        if workspace_name in mappings:
            raise ValueError(
                f"Workspace '{workspace_name}' already exists in config"
            )

        # Get remote URL and primary branch
        remote_url = self._get_remote_url()
        primary_branch = self.get_primary_branch()
        primary_path = self.path / primary_branch / self.path.name

        # Fetch to get latest remote branches
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
            ["git", "-C", str(primary_path), "ls-remote", "origin", f"refs/heads/{git_branch}"],
            capture_output=True,
            text=True,
        )
        branch_exists_on_remote = bool(result.stdout.strip())

        # Create outer workspace dir; clone/copy into inner repo dir
        workspace_dir.mkdir()
        inner_path = workspace_dir / self.path.name

        if use_git_clone:
            # Full git clone from remote into inner dir
            subprocess.run(
                ["git", "clone", remote_url, str(inner_path)],
                check=True,
            )
        else:
            # Copy the primary workspace repo dir (includes .git with all state)
            shutil.copytree(primary_path, inner_path, symlinks=True)

        # Switch to the branch
        if branch_exists_on_remote:
            subprocess.run(
                ["git", "-C", str(inner_path), "switch", git_branch],
                check=True,
            )
        else:
            subprocess.run(
                ["git", "-C", str(inner_path), "switch", "-c", git_branch],
                check=True,
            )

        # Update config with new mapping
        mappings[workspace_name] = WorkspaceMetadata(
            git_branch=git_branch,
            created_at=datetime.now().isoformat()
        )
        self._save_config(mappings)

        return inner_path

    def add_branch_directory(self, branch_name: str, use_git_clone: bool = False) -> Path:
        """Deprecated: Use add_workspace() instead.

        For backwards compatibility, workspace_name = branch_name.
        """
        return self.add_workspace(
            git_branch=branch_name,
            workspace_name=branch_name,
            use_git_clone=use_git_clone
        )

    def remove_branch_directory(self, workspace_name: str, force: bool = False) -> bool:
        """Remove a workspace directory and its container.

        Args:
            workspace_name: Name of workspace directory to remove
            force: If True, skip confirmation prompt

        Returns:
            True if successful, False if cancelled

        Raises:
            ValueError: If directory doesn't exist or invalid workspace name
        """
        # Validate workspace name first
        self._validate_workspace_name(workspace_name)

        workspace_dir = self.path / workspace_name

        # Security check: ensure path doesn't escape project directory
        try:
            workspace_dir_resolved = workspace_dir.resolve()
            project_resolved = self.path.resolve()

            if not workspace_dir_resolved.is_relative_to(project_resolved):
                raise ValueError(
                    f"Invalid workspace path: {workspace_name} (path traversal detected)"
                )
        except (ValueError, OSError):
            raise ValueError(f"Invalid workspace name: {workspace_name}")

        if not workspace_dir.exists():
            raise ValueError(f"Workspace directory not found: {workspace_name}")

        # Show what will be deleted and ask for confirmation
        if not force:
            from rich.console import Console
            console = Console()
            console.print(f"\n[bold red]⚠️  DESTRUCTIVE ACTION[/bold red]")
            console.print(f"About to execute:")
            console.print(f"  [dim]$ rm -rf {workspace_dir}[/dim]")
            console.print(f"  [yellow]All files and git history in this directory will be permanently lost.[/yellow]")

            if not Confirm.ask("Are you sure you want to continue?", default=False):
                console.print("[yellow]Operation cancelled[/yellow]")
                return False

        # Stop container first
        container = Container(workspace_dir)
        stopped = container.stop()

        if stopped:
            from rich.console import Console
            console = Console()
            console.print(f"  Stopped and removed container")

        # Remove directory
        shutil.rmtree(workspace_dir)

        # Remove from config
        mappings = self._load_config()
        if workspace_name in mappings:
            del mappings[workspace_name]
            self._save_config(mappings)

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
            primary_path = self.path / primary_branch / self.path.name

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
