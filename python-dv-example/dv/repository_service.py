"""Repository and branch workflow service layer."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import Config
from .devcontainer_service import DevcontainerService
from .project import Project


@dataclass
class CloneResult:
    """Result of cloning a repository."""

    project_dir: Path
    primary_branch_path: Path
    default_branch: str


@dataclass
class BranchAddResult:
    """Result of adding a branch directory."""

    branch_path: Path
    branch: str
    was_created: bool


class RepositoryService:
    """Service for repository and branch workflow operations."""

    def __init__(self, config: Config):
        """Initialize service with configuration.

        Args:
            config: Application configuration
        """
        self.config = config
        self.devcontainer_service = DevcontainerService(config)

    def _derive_project_name(self, url: str) -> str:
        """Extract project name from git URL.

        Args:
            url: Git repository URL

        Returns:
            Project name (basename without .git)
        """
        # Handle various URL formats
        # git@github.com:user/repo.git -> repo
        # https://github.com/user/repo.git -> repo
        # https://github.com/user/repo -> repo
        path = url.rstrip("/")
        if path.endswith(".git"):
            path = path[:-4]
        return Path(path).name

    def _get_default_branch(self, url: str) -> str:
        """Use git ls-remote to detect default branch before cloning.

        Args:
            url: Git repository URL

        Returns:
            Default branch name

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--symref", url, "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse output like: "ref: refs/heads/main	HEAD"
            for line in result.stdout.split("\n"):
                if line.startswith("ref:"):
                    # Extract branch name from refs/heads/branch
                    ref = line.split()[1]
                    if ref.startswith("refs/heads/"):
                        return ref.replace("refs/heads/", "")

        except subprocess.CalledProcessError:
            pass

        # Fallback to main
        return "main"

    def clone_as_regular(self, url: str, name: Optional[str] = None) -> CloneResult:
        """Clone repository as regular git clone with branch directory structure.

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
            name = self._derive_project_name(url)

        project_dir = Path.cwd() / name

        # Detect default branch
        default_branch = self._get_default_branch(url)

        # Create parent directory
        project_dir.mkdir(parents=True, exist_ok=True)

        # Clone into subdirectory named after default branch
        branch_dir = project_dir / default_branch
        subprocess.run(
            ["git", "clone", url, str(branch_dir)],
            check=True,
        )

        return CloneResult(
            project_dir=project_dir,
            primary_branch_path=branch_dir,
            default_branch=default_branch,
        )

    def add_branch_with_container(
        self,
        project: Project,
        branch: str,
        start_container: bool = True,
        use_external_dotfiles: bool = False,
        use_git_clone: bool = False,
    ) -> BranchAddResult:
        """Create branch directory and optionally start its container.

        Args:
            project: Project instance
            branch: Branch name for the directory
            start_container: Whether to start devcontainer (default: True)
            use_external_dotfiles: Whether to use external dotfiles (default: False)
            use_git_clone: Whether to use full git clone (default: False, uses local clone)

        Returns:
            BranchAddResult with path and branch info

        Raises:
            RuntimeError: If not in DV project
            ValueError: If branch directory already exists
            subprocess.CalledProcessError: If git or devcontainer commands fail
        """
        # Create branch directory using project method
        branch_path = project.add_branch_directory(branch, use_git_clone)

        # Start container if requested
        if start_container:
            self.devcontainer_service.up(branch_path, use_external_dotfiles)

        return BranchAddResult(
            branch_path=branch_path,
            branch=branch,
            was_created=True,
        )

    def remove_branch_with_container(
        self, project: Project, name: str, force: bool = False
    ) -> bool:
        """Remove branch directory and its container.

        Args:
            project: Project instance
            name: Branch directory name to remove
            force: If True, skip confirmation prompts

        Returns:
            True if successful, False if cancelled

        Raises:
            ValueError: If branch directory not found
        """
        # Delegate to project method (it handles container cleanup)
        return project.remove_branch_directory(name, force=force)
