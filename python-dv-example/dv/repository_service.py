"""Repository and worktree workflow service layer."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import Config
from .devcontainer_service import DevcontainerService
from .workspace import Workspace


@dataclass
class CloneResult:
    """Result of cloning a repository."""

    project_dir: Path
    bare_repo: Path
    default_branch: str
    worktree_path: Path


@dataclass
class WorktreeAddResult:
    """Result of adding a worktree."""

    worktree_path: Path
    branch: str
    was_created: bool


class RepositoryService:
    """Service for repository and worktree workflow operations."""

    def __init__(self, config: Config):
        """Initialize service with configuration.

        Args:
            config: Application configuration
        """
        self.config = config
        self.devcontainer_service = DevcontainerService(config)

    def clone_as_bare(self, url: str, name: Optional[str] = None) -> CloneResult:
        """Clone repository as bare repo with worktree structure.

        Args:
            url: Git repository URL
            name: Project name (defaults to repository name from URL)

        Returns:
            CloneResult with paths and default branch info

        Raises:
            subprocess.CalledProcessError: If git commands fail
        """
        # Derive project name from URL if not provided
        if not name:
            name = Path(url).stem

        project_dir = Path.cwd() / name
        bare_repo = project_dir / ".bare"

        # Create project directory and clone as bare
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

        # Create worktree for default branch
        subprocess.run(
            [
                "git",
                "worktree",
                "add",
                "--relative-paths",
                default_branch,
                default_branch,
            ],
            cwd=project_dir,
            check=True,
        )

        worktree_path = project_dir / default_branch

        return CloneResult(
            project_dir=project_dir,
            bare_repo=bare_repo,
            default_branch=default_branch,
            worktree_path=worktree_path,
        )

    def add_worktree_with_container(
        self,
        workspace: Workspace,
        branch: str,
        start_container: bool = True,
        use_external_dotfiles: bool = False,
    ) -> WorktreeAddResult:
        """Create worktree and optionally start its container.

        Args:
            workspace: Workspace instance
            branch: Branch name for the worktree
            start_container: Whether to start devcontainer (default: True)
            use_external_dotfiles: Whether to use external dotfiles (default: False)

        Returns:
            WorktreeAddResult with path and branch info

        Raises:
            RuntimeError: If not in worktree-enabled project
            ValueError: If worktree already exists
            subprocess.CalledProcessError: If git or devcontainer commands fail
        """
        # Create worktree using workspace method
        worktree_path = workspace.add_worktree(branch)

        # Start container if requested
        if start_container:
            self.devcontainer_service.up(worktree_path, use_external_dotfiles)

        return WorktreeAddResult(
            worktree_path=worktree_path,
            branch=branch,
            was_created=True,
        )

    def remove_worktree_with_container(
        self, workspace: Workspace, name: str
    ) -> bool:
        """Remove worktree and its container.

        Args:
            workspace: Workspace instance
            name: Worktree name to remove

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If worktree not found
        """
        # Delegate to workspace method (it handles container cleanup)
        return workspace.remove_worktree(name)
