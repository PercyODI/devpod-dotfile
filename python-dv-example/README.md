# dv - Devcontainer Management Tool (Python Edition)

A Python rewrite of the `dv` bash script for managing devcontainers with git worktrees.

## Features

- **Clean Architecture**: Separation of concerns (config, workspace, container, CLI)
- **Type Safety**: Full Python type hints
- **Rich Output**: Beautiful terminal output with colors and tables
- **Testable**: Structured for easy unit testing
- **Extensible**: Easy to add new features or container images
- **Interactive Selection**: fzf integration with fallback to simple selection
- **Configuration**: YAML config file support

## Installation

### Option 1: Install from source (recommended for development)

```bash
cd python-dv-example
pip install -e .
```

The `-e` flag installs in "editable" mode, so changes to the code take effect immediately.

### Option 2: Install as user package

```bash
cd python-dv-example
pip install --user .
```

### Option 3: Install with pipx (isolated environment)

```bash
pipx install ./python-dv-example
```

After installation, the `dv` command will be available in your terminal.

## Usage

The CLI interface is identical to the bash version, with some improvements:

### Basic Commands

```bash
# Start devcontainer (current directory)
dv up

# Start specific worktree
dv up main

# Interactive worktree selection
dv up --select

# Enter container and run dev command
dv go

# Enter container with shell
dv go --shell

# Stop devcontainer
dv down

# Execute arbitrary command
dv exec -- npm test
```

### Worktree Management

```bash
# Clone as bare repo
dv clone git@github.com:user/repo.git

# Add new worktree
dv worktree add feature-branch

# Interactive branch selection
dv worktree add --select

# List worktrees with status
dv worktree list

# Remove worktree
dv worktree remove feature-branch
dv worktree remove --select

# Show status
dv status
dv status main
```

### Templates

```bash
# Create .devcontainer/devcontainer.json
dv template main node
dv template feature-123 python
```

## Configuration

Create `~/.config/dv/config.yml`:

```yaml
# API Keys (optional, can use environment variables)
anthropic_api_key: sk-...
openai_api_key: sk-...

# Git config
git_user_name: "Your Name"
git_user_email: "you@example.com"

# Dotfiles
dotfiles_dir: ~/github/devpod-dotfile
dotfiles_repo: https://github.com/PercyODI/devpod-dotfile

# Custom container images
images:
  node: mcr.microsoft.com/devcontainers/typescript-node:24-trixie
  python: mcr.microsoft.com/devcontainers/python:1-3.12-bookworm
  custom: your-custom-image:latest
```

Environment variables still work and take precedence over the config file.

## Improvements Over Bash Version

### 1. **Simpler Worktree Resolution**
```bash
# Explicit - no magic
dv up main

# Interactive - opt-in with --select
dv up --select

# Current directory - default
cd project/main && dv up
```

No complex auto-detection with 4 different code paths.

### 2. **Structured Data**
```python
@dataclass
class WorktreeInfo:
    path: Path
    branch: str
    status: ContainerStatus
```

No parallel arrays that can get out of sync.

### 3. **Proper Error Handling**
```python
try:
    worktree_path = ws.add_worktree(branch)
    success(f"Worktree created at: {worktree_path}")
except ValueError as e:
    error(str(e))
    sys.exit(1)
```

No `set -e` that kills the entire script.

### 4. **Testable**
```python
def test_workspace_resolution():
    ws = Workspace(Path("/test/project"))
    path = ws.resolve_worktree("main")
    assert path == Path("/test/project/main")
```

Easy to write unit tests.

### 5. **Configuration Management**
YAML config file + environment variables with clear precedence rules.

### 6. **Rich Output**
Beautiful tables, colors, and status indicators using the `rich` library.

## Development

### Project Structure

```
dv/
├── cli.py          # Click commands (all user-facing commands)
├── workspace.py    # Git worktree operations
├── container.py    # Docker/devcontainer operations
├── config.py       # Configuration management
└── utils.py        # Helper functions
```

### Running Tests

```bash
pip install -e '.[dev]'
pytest
```

### Type Checking

```bash
mypy dv/
```

### Code Formatting

```bash
black dv/
```

## Comparison to Bash Version

| Aspect | Bash | Python |
|--------|------|--------|
| Lines of code | ~1200 | ~800 (more readable) |
| Error handling | `set -e` (blunt) | Try/except (granular) |
| Data structures | Parallel arrays | Dataclasses |
| Testing | Difficult | Easy |
| Configuration | Env vars only | YAML + env vars |
| Output | Manual color codes | Rich library |
| Argument parsing | Manual | Click (auto-generated help) |
| Worktree resolution | 4 code paths | 1 code path + opt-in |

## Why Python?

1. **Better abstractions** - Classes, dataclasses, enums
2. **Type safety** - Catch bugs before runtime
3. **Testing** - pytest, mocking, coverage
4. **Libraries** - Click, Rich, PyYAML
5. **Maintainability** - Easier for teams to understand
6. **Extensibility** - Plugins, custom commands

## Migration from Bash

The Python version is a drop-in replacement:

```bash
# Uninstall bash version (if installed)
rm ~/.local/bin/dv  # or wherever you installed it

# Install Python version
cd python-dv-example
pip install --user .

# Use it the same way
dv up
dv go
dv status
```

## License

MIT
