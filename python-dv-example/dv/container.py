"""Container management operations."""

import subprocess
from enum import Enum
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Confirm

console = Console()


class ContainerStatus(Enum):
    """Container status states."""

    RUNNING = "running"
    STOPPED = "stopped"
    NONE = "none"

    def __str__(self) -> str:
        return self.value

    @property
    def icon(self) -> str:
        """Get status icon."""
        return {
            ContainerStatus.RUNNING: "●",
            ContainerStatus.STOPPED: "●",
            ContainerStatus.NONE: "○",
        }[self]

    @property
    def color(self) -> str:
        """Get color for rich console."""
        return {
            ContainerStatus.RUNNING: "green",
            ContainerStatus.STOPPED: "yellow",
            ContainerStatus.NONE: "red",
        }[self]


class Container:
    """Devcontainer operations."""

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path

    def get_status(self) -> ContainerStatus:
        """Get container status for this workspace."""
        container_id = self._get_container_id()
        if not container_id:
            return ContainerStatus.NONE

        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", container_id],
                capture_output=True,
                text=True,
                check=False,
            )
            status = result.stdout.strip()
            if status == "running":
                return ContainerStatus.RUNNING
            elif status:
                return ContainerStatus.STOPPED
        except Exception:
            pass

        return ContainerStatus.NONE

    def _get_container_id(self) -> Optional[str]:
        """Get container ID for this workspace."""
        try:
            result = subprocess.run(
                [
                    "docker", "ps", "-aq",
                    "--filter", f"label=devcontainer.local_folder={self.workspace_path}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            container_id = result.stdout.strip()
            return container_id if container_id else None
        except subprocess.CalledProcessError:
            return None

    def stop(self, force: bool = False) -> bool:
        """Stop and remove the container.

        Args:
            force: If True, skip confirmation prompt

        Returns:
            True if container was stopped, False if no container or cancelled
        """
        container_id = self._get_container_id()
        if not container_id:
            return False

        # Show commands and ask for confirmation
        if not force:
            console.print(f"\n[bold yellow]⚠️  DESTRUCTIVE ACTION[/bold yellow]")
            console.print(f"About to execute:")
            console.print(f"  [dim]$ docker stop {container_id}[/dim]")
            console.print(f"  [dim]$ docker rm {container_id}[/dim]")
            console.print(f"  Workspace: [cyan]{self.workspace_path}[/cyan]")

            if not Confirm.ask("Stop and remove this container?", default=True):
                console.print("[yellow]Operation cancelled[/yellow]")
                return False

        try:
            subprocess.run(["docker", "stop", container_id], check=True, capture_output=True)
            subprocess.run(["docker", "rm", container_id], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
