# dv - Devcontainer Management Tool (Python Edition)

A Python tool for managing devcontainers with git branch directories.

## Features

- **Clean Architecture**: Separation of concerns (config, workspace, container, CLI)
- **Type Safety**: Full Python type hints
- **Rich Output**: Beautiful terminal output with colors and tables
- **Testable**: Structured for easy unit testing
- **Extensible**: Easy to add new features or container images
- **Interactive Selection**: fzf integration with fallback to simple selection
- **Configuration**: YAML config file support
- **Simple Mental Model**: Each branch = a directory

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

### Project Structure

After cloning with `dv`, your project looks like this:

```
project-name/           # Parent directory (run dv commands here)
├── main/               # Regular git clone
│   └── .git/
├── feature-123/        # Another branch directory
│   └── .git/
└── feature-456/
    └── .git/
```

### Basic Commands

```bash
# Clone repository
dv clone git@github.com:user/repo.git

# Change to project directory
cd project-name

# Start devcontainer for main branch
dv up main

# Enter container and run dev command
dv go main

# Enter container with shell
dv go main --shell

# Stop devcontainer
dv down main

# Execute arbitrary command
dv exec main -- npm test

# Interactive selection
dv up --select
dv go --select
```

### Branch Directory Management

```bash
# Add new branch directory (local clone - fast)
dv branch add feature-branch

# Add with full git clone
dv branch add feature-branch --clone

# Add without starting container
dv branch add feature-branch --no-start

# List branch directories with status
dv branch list

# Remove branch directory
dv branch remove feature-123

# Interactive selection
dv branch remove --select

# Show status
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

## Key Design Decisions

### 1. **Simple Directory Structure**
```
project-name/
├── main/          # Each branch is a separate git clone
├── feature-1/
└── feature-2/
```

No special `.bare` repository. Each branch directory is a regular git clone.

### 2. **Explicit Branch Arguments**
```bash
# Always explicit - no magic
dv up main

# Or interactive selection
dv up --select
```

Branch argument is required. Commands must be run from parent directory.

### 3. **Fast Local Clones**
```bash
# Default: git clone --local (fast, uses hardlinks)
dv branch add feature-123

# Optional: full clone from remote
dv branch add feature-123 --clone
```

### 4. **Structured Data**
```python
@dataclass
class BranchInfo:
    path: Path
    branch: str
    status: ContainerStatus
```

No parallel arrays that can get out of sync.

### 5. **Proper Error Handling**
```python
try:
    branch_path = project.add_branch_directory(branch)
    success(f"Branch directory created at: {branch_path}")
except ValueError as e:
    error(str(e))
    sys.exit(1)
```

Granular error handling with helpful messages.

## Development

### Project Structure

```
dv/
├── cli.py                    # Click commands (all user-facing commands)
├── project.py                # Project and branch directory operations
├── container.py              # Docker/devcontainer operations
├── config.py                 # Configuration management
├── repository_service.py     # Clone and branch workflows
├── devcontainer_service.py   # Devcontainer lifecycle
└── utils.py                  # Helper functions
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

## Why This Architecture?

### Advantages of Branch Directories

1. **Simpler mental model** - Each branch = a directory
2. **No special git setup** - Just regular clones
3. **More transparent** - Easy to understand what's happening
4. **Flexible** - Can manipulate directories directly
5. **Beginner friendly** - Easy to understand and use

### Why Python?

1. **Better abstractions** - Classes, dataclasses, enums
2. **Type safety** - Catch bugs before runtime
3. **Testing** - pytest, mocking, coverage
4. **Libraries** - Click, Rich, PyYAML
5. **Maintainability** - Easier for teams to understand
6. **Extensibility** - Plugins, custom commands

## Workflow Examples

### Starting a new project

```bash
# Clone repository
dv clone git@github.com:user/repo.git

# Navigate to project
cd repo

# Start main branch
dv up main

# Work in container
dv go main
```

### Working on multiple features

```bash
# Add branch directories
dv branch add feature-auth
dv branch add feature-ui

# Start both containers
dv up feature-auth
dv up feature-ui

# Switch between them
dv go feature-auth
dv go feature-ui

# View all branches
dv branch list
```

### Cleaning up

```bash
# Stop container
dv down feature-auth

# Remove branch directory (also stops container)
dv branch remove feature-auth
```

## License

MIT
