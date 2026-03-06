"""Devcontainer lifecycle service layer."""

import json
import platform
import re
import subprocess
from pathlib import Path
from typing import Optional

from .config import Config
from .container import Container, ContainerStatus
from .utils import console


def _volume_name(project_path: Path) -> str:
    """Derive a Docker-safe volume name suffix from the project directory name."""
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "-", project_path.name)
    return sanitized


class DevcontainerService:
    """Service for managing devcontainer lifecycle operations."""

    def __init__(self, config: Config):
        """Initialize service with configuration.

        Args:
            config: Application configuration
        """
        self.config = config

    def build_up_command(
        self, workspace_path: Path, project_path: Path, use_external_dotfiles: bool = False
    ) -> list[str]:
        """Build devcontainer up command with all required arguments.

        Args:
            workspace_path: Path to the workspace folder
            project_path: Path to the project root (contains all workspaces)
            use_external_dotfiles: Whether to use external dotfiles (True) or local (False)

        Returns:
            Complete command list for devcontainer up
        """
        if not self.config.ssh_auth_sock:
            if platform.system() == "Windows":
                raise RuntimeError(
                    "dv must be run from within WSL2 on Windows, not from PowerShell or cmd.\n"
                    "Install WSL2: https://learn.microsoft.com/en-us/windows/wsl/install\n"
                    "Once in WSL2, run: eval $(ssh-agent) && ssh-add ~/.ssh/id_ed25519"
                )
            raise RuntimeError(
                "No SSH agent socket found (SSH_AUTH_SOCK is not set).\n"
                "Start ssh-agent and add your key:\n"
                "  eval $(ssh-agent)\n"
                "  ssh-add ~/.ssh/id_ed25519"
            )

        apt_packages = [
            "git",
            "curl",
            "ca-certificates",
            "unzip",
            "zsh",
            "ripgrep",
            "fd-find",
            "fzf",
            "jq",
            "build-essential",
            "openssh-client",
            "tmux",
        ]
        additional_features = json.dumps(
            {
                "ghcr.io/devcontainers-extra/features/apt-packages:1": {
                    "packages": ",".join(apt_packages),
                },
                "ghcr.io/devcontainers-extra/features/opencode:1": {},
                "ghcr.io/stu-bell/devcontainer-features/claude-code:0": {},
                "ghcr.io/thediveo/devcontainer-features/lazygit:0": {},
                "ghcr.io/duduribeiro/devcontainer-features/neovim:1": {
                    "version": "stable",
                },
            }
        )

        cmd = [
            "devcontainer",
            "up",
            "--workspace-folder",
            str(workspace_path),
            "--mount",
            f"type=bind,source={self.config.ssh_auth_sock},target=/ssh/agent",
            "--mount",
            f"type=volume,source=dv-nvim-{_volume_name(project_path)},target=/nvim-data",
            "--update-remote-user-uid-default",
            "on",
            "--remove-existing-container",
            "--additional-features",
            additional_features,
        ]

        known_hosts = Path.home() / ".ssh" / "known_hosts"
        if known_hosts.exists():
            cmd.extend([
                "--mount",
                f"type=bind,source={known_hosts},target=/ssh/known_hosts",
            ])

        # Add remote env args
        cmd.extend(self.config.get_remote_env_args())

        if use_external_dotfiles:
            # Use external dotfiles
            cmd.extend(["--dotfiles-repository", self.config.dotfiles_repo])
        else:
            # Mount local dotfiles
            cmd.extend(
                [
                    "--mount",
                    f"type=bind,source={self.config.dotfiles_dir},target=/dotfiles",
                ]
            )

        return cmd

    def build_exec_command(self, workspace_path: Path, command: list[str]) -> list[str]:
        """Build devcontainer exec command.

        Args:
            workspace_path: Path to the workspace folder
            command: Command to execute in container

        Returns:
            Complete command list for devcontainer exec
        """
        cmd = [
            "devcontainer",
            "exec",
            "--workspace-folder",
            str(workspace_path),
        ]
        cmd.extend(self.config.get_remote_env_args())
        cmd.append("--")
        cmd.extend(command)

        return cmd

    def up(self, workspace_path: Path, project_path: Path, use_external_dotfiles: bool = False) -> None:
        """Start devcontainer with full dotfile setup.

        Args:
            workspace_path: Path to the workspace folder
            project_path: Path to the project root (contains all workspaces)
            use_external_dotfiles: Whether to use external dotfiles (True) or local (False)

        Raises:
            subprocess.CalledProcessError: If devcontainer command fails
        """
        # Build and run devcontainer up command
        cmd = self.build_up_command(workspace_path, project_path, use_external_dotfiles)
        subprocess.run(cmd, check=True)

        # If using local dotfiles, run installation script
        if not use_external_dotfiles:
            console.print("Running local dotfiles installation...")
            exec_cmd = self.build_exec_command(
                workspace_path, ["bash", "-c", "cd /dotfiles && ./install.sh"]
            )
            subprocess.run(exec_cmd, check=True)

    def exec(
        self, workspace_path: Path, command: list[str], interactive: bool = False
    ) -> subprocess.CompletedProcess:
        """Execute command in devcontainer.

        Args:
            workspace_path: Path to the workspace folder
            command: Command to execute
            interactive: Whether to run interactively (default: False)

        Returns:
            CompletedProcess result
        """
        cmd = self.build_exec_command(workspace_path, command)
        return subprocess.run(cmd, check=not interactive)

    def down(self, workspace_path: Path) -> bool:
        """Stop and remove devcontainer.

        Args:
            workspace_path: Path to the workspace folder

        Returns:
            True if container was stopped, False if no container found
        """
        container = Container(workspace_path)
        return container.stop()

    def get_status(self, workspace_path: Path) -> ContainerStatus:
        """Get devcontainer status.

        Args:
            workspace_path: Path to the workspace folder

        Returns:
            Container status
        """
        container = Container(workspace_path)
        return container.get_status()
