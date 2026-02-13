"""Configuration management for dv."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class Config:
    """Application configuration."""

    # API Keys
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    prefer_opencode: bool = False

    # Git config
    git_user_name: Optional[str] = None
    git_user_email: Optional[str] = None

    # Dotfiles
    dotfiles_dir: Path = field(default_factory=lambda: Path.home() / "github" / "devpod-dotfile")
    dotfiles_repo: str = "https://github.com/PercyODI/devpod-dotfile"

    # Container images
    images: dict[str, str] = field(default_factory=lambda: {
        "node22": "mcr.microsoft.com/devcontainers/typescript-node:22-bookworm",
        "node": "mcr.microsoft.com/devcontainers/typescript-node:24-trixie",
        "python": "mcr.microsoft.com/devcontainers/python:1-3.12-bookworm",
        "java": "mcr.microsoft.com/devcontainers/java:1-21-bookworm",
        "universal": "mcr.microsoft.com/devcontainers/universal:2-linux",
        "base": "mcr.microsoft.com/devcontainers/base:1-bookworm",
    })

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            prefer_opencode=os.getenv("PREFER_OPENCODE", "false").lower() == "true",
            git_user_name=os.getenv("GIT_USER_NAME"),
            git_user_email=os.getenv("GIT_USER_EMAIL"),
            dotfiles_dir=Path(os.getenv("DOTFILES_DIR", Path.home() / "github" / "devpod-dotfile")),
            dotfiles_repo=os.getenv("DOTFILES_REPO", "https://github.com/PercyODI/devpod-dotfile"),
        )

    @classmethod
    def from_file(cls, path: Path) -> "Config":
        """Load configuration from YAML file."""
        if not path.exists():
            return cls.from_env()

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        # Merge with environment variables (env takes precedence)
        config = cls.from_env()

        # Override with file values if env not set
        if not config.anthropic_api_key and "anthropic_api_key" in data:
            config.anthropic_api_key = data["anthropic_api_key"]
        if not config.openai_api_key and "openai_api_key" in data:
            config.openai_api_key = data["openai_api_key"]
        if "images" in data:
            config.images.update(data["images"])

        return config

    def get_remote_env_args(self) -> list[str]:
        """Build list of --remote-env arguments for devcontainer CLI."""
        args = []

        if self.anthropic_api_key:
            args.extend(["--remote-env", f"ANTHROPIC_API_KEY={self.anthropic_api_key}"])
        if self.openai_api_key:
            args.extend(["--remote-env", f"OPENAI_API_KEY={self.openai_api_key}"])

        args.extend(["--remote-env", f"PREFER_OPENCODE={str(self.prefer_opencode).lower()}"])

        if self.git_user_name:
            args.extend([
                "--remote-env", f"GIT_AUTHOR_NAME={self.git_user_name}",
                "--remote-env", f"GIT_COMMITTER_NAME={self.git_user_name}",
            ])
        if self.git_user_email:
            args.extend([
                "--remote-env", f"GIT_AUTHOR_EMAIL={self.git_user_email}",
                "--remote-env", f"GIT_COMMITTER_EMAIL={self.git_user_email}",
            ])

        return args
