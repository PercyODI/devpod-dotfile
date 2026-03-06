# devpod-dotfile

A Dotfile repo specifically for devpod environments

## Host System Requirements

### Setup

Clone this repository to a known location on your host system:

```bash
git clone https://github.com/PercyODI/devpod-dotfile.git ~/github/devpod-dotfile
```

### Installed Applications

- Docker Desktop
- [Dev Container Cli](https://github.com/devcontainers/cli)
- [direnv](https://direnv.net/)
  - https://www.papermtn.co.uk/secrets-management-managing-environment-variables-with-direnv/
- Modern terminal (Wezterm, kitty, warp, iterm2, etc)
- Python 3.9+

### Windows (WSL2)

Native Windows (PowerShell, cmd, Git Bash) is **not supported**. `dv` must be run from within WSL2.

1. Install WSL2: https://learn.microsoft.com/en-us/windows/wsl/install
2. Inside WSL2, follow the standard Linux setup steps below.

**SSH agent in WSL2:** The SSH agent does not start automatically in WSL2. Add to your `~/.bashrc` or `~/.zshrc`:

```bash
if [ -z "$SSH_AUTH_SOCK" ]; then
  eval $(ssh-agent -s) > /dev/null
fi
```

Optionally, to bridge the Windows SSH agent into WSL2, see [npiperelay](https://github.com/jstarks/npiperelay).

### SSH Keys

In order to use git via ssh, you must have SSH keys added to the agent on the host. For example:

```bash
ssh-add ~/.ssh/github_id_ed25519
```

On **WSL2**, start the agent first if needed:

```bash
eval $(ssh-agent)
ssh-add ~/.ssh/id_ed25519
```

### Environment Variables

`dv` is configured entirely through environment variables. Use [direnv](https://direnv.net/) with a `~/.envrc` file on your host system to manage them.

| Variable            | Default                                       | Description                              |
|---------------------|-----------------------------------------------|------------------------------------------|
| `ANTHROPIC_API_KEY` | (none)                                        | Anthropic API key for Claude Code        |
| `OPENAI_API_KEY`    | (none)                                        | OpenAI API key                           |
| `PREFER_OPENCODE`   | `false`                                       | Use Opencode instead of Claude Code      |
| `GIT_USER_NAME`     | (none)                                        | Git author/committer name                |
| `GIT_USER_EMAIL`    | (none)                                        | Git author/committer email               |
| `DOTFILES_DIR`      | `~/github/devpod-dotfile`                     | Path to local dotfiles on the host       |
| `DOTFILES_REPO`     | `https://github.com/PercyODI/devpod-dotfile`  | URL for external dotfiles repo           |

Example `~/.envrc`:

```bash
source_up
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export GIT_USER_NAME="Your Name"
export GIT_USER_EMAIL="you@example.com"
```

After editing `~/.envrc`, run `direnv allow` to activate the new values.

### AI Assistant Selection

The dev container includes both Claude Code and Opencode AI assistants. By default, the `dev` command launches Claude Code. To use Opencode instead, set the `PREFER_OPENCODE` environment variable to `true` in your `~/.envrc` file:

```bash
export PREFER_OPENCODE=true
```

When you run the `dev` command, it will automatically launch the preferred AI assistant in the tmux pane.

## Installing the `dv` Tool

The `dv` command is a Python tool for managing devcontainers with git branch directories.

### Quick Install

```bash
cd ~/github/devpod-dotfile/host/dv-tool
./install.sh
```

The install script will:
1. Verify Python 3.9+ is available
2. Install `dv` to `~/.local/bin` via pip
3. Warn you if `~/.local/bin` is not in your PATH

### PATH Setup

If `~/.local/bin` is not already in your PATH, add the following to your `.bashrc` or `.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then reload your shell:

```bash
source ~/.bashrc  # or source ~/.zshrc
```

### Manual Install Options

```bash
# Editable install (changes take effect immediately — good for development)
cd ~/github/devpod-dotfile/host/dv-tool
pip install -e .

# Isolated environment with pipx
pipx install ~/github/devpod-dotfile/host/dv-tool
```

## Working with Git Branch Directories

The `dv` command uses a simple directory-per-branch structure — no special bare repository setup required.

### Project Structure

```
project-name/
├── main/               # Regular git clone (main branch)
│   └── .git/
├── feature-123/        # Another branch directory
│   └── .git/
└── bugfix-456/
    └── .git/
```

### Quick Start

1. **Clone a repository:**
   ```bash
   dv clone git@github.com:user/repo.git
   # Creates:
   #   repo/
   #     main/           # Default branch clone (with devcontainer)
   ```

2. **Add a branch directory:**
   ```bash
   cd repo
   dv branch add feature-branch
   # Creates a local clone and starts the devcontainer
   ```

3. **Enter a container:**
   ```bash
   dv go main
   # Or enter with a shell instead of the dev command:
   dv go main --shell
   ```

4. **View all branches:**
   ```bash
   dv branch list
   # Shows all branch directories with container status
   ```

5. **Check current status:**
   ```bash
   dv status main
   ```

## The `dv` Command

### Basic Commands

```bash
dv up [branch]         # Start devcontainer
dv up --select         # Start devcontainer (interactive selection)
dv go [branch]         # Enter container and run dev
dv go [branch] --shell # Open interactive shell
dv down [branch]       # Stop and remove container
dv exec [branch] -- <command>  # Run command in container
```

### Branch Directory Commands

```bash
dv branch add <branch>          # Create branch directory (fast local clone)
dv branch add <branch> --clone  # Create with full git clone from remote
dv branch add <branch> --no-start  # Create without starting container
dv branch list                  # List all branch directories with status
dv branch remove <branch>       # Remove branch directory and stop container
dv branch remove --select       # Interactive selection
```

### Other Commands

```bash
dv clone <url> [name]           # Clone repository as branch directory project
dv status [branch]              # Show branch/container status
dv template <branch> <image>    # Create .devcontainer/devcontainer.json
```

The `dv template` command accepts these built-in image aliases:

| Alias       | Image URI                                                       |
|-------------|-----------------------------------------------------------------|
| `node22`    | `mcr.microsoft.com/devcontainers/typescript-node:22-bookworm`  |
| `node`      | `mcr.microsoft.com/devcontainers/typescript-node:24-trixie`    |
| `python`    | `mcr.microsoft.com/devcontainers/python:1-3.12-bookworm`       |
| `java`      | `mcr.microsoft.com/devcontainers/java:1-21-bookworm`           |
| `universal` | `mcr.microsoft.com/devcontainers/universal:2-linux`            |
| `base`      | `mcr.microsoft.com/devcontainers/base:1-bookworm`              |

To use a custom image, specify the full URI directly in `.devcontainer/devcontainer.json`.

### Aliases

- `dv branch` = `dv br`
- `dv status` = `dv st`

## Workflow Examples

### Starting a new project

```bash
dv clone git@github.com:user/repo.git
cd repo
dv up main
dv go main
```

### Working on multiple features

```bash
cd repo
dv branch add feature-auth
dv branch add feature-ui

dv up feature-auth
dv up feature-ui

dv go feature-auth   # switch between them
dv go feature-ui

dv branch list       # view all branches
```

### Cleaning up

```bash
dv down feature-auth                # stop container
dv branch remove feature-auth       # remove branch directory (also stops container)
```

## Troubleshooting

### Command not found

```bash
# Add to ~/.bashrc or ~/.zshrc:
export PATH="$HOME/.local/bin:$PATH"

# Then reload:
source ~/.bashrc
```

### Container won't start

```bash
dv status

# View docker logs
docker logs $(docker ps -aq --filter "label=devcontainer.local_folder=$(pwd)")

# Try recreating
dv down
dv up
```

### Getting help

```bash
dv --help              # Main help
dv up --help           # Command-specific help
dv branch --help       # Subcommand help
```
