# Quick Start Guide

## Installation (30 seconds)

```bash
cd python-dv-example
./install.sh
```

That's it! The `dv` command is now available.

## Your First Devcontainer

```bash
# Clone a repo with worktree support
dv clone git@github.com:yourusername/yourrepo.git

# It automatically:
# 1. Creates a bare repo in yourrepo/.bare
# 2. Creates a worktree for the default branch
# 3. Starts the devcontainer

# Enter the container
dv go

# Done! You're now in a running devcontainer
```

## Working with Multiple Branches

```bash
# Create a worktree for a feature branch
dv worktree add feature-123

# It automatically:
# 1. Creates the worktree directory
# 2. Checks out the branch
# 3. Starts a devcontainer for that branch

# Switch between branches (each in their own container)
dv go main              # Enter main worktree
dv go feature-123       # Enter feature-123 worktree

# List all worktrees with their status
dv worktree list

# Output:
# ┌────────────┬─────────────┬─────────────┬──────────────────────┐
# │ Status     │ Name        │ Branch      │ Path                 │
# ├────────────┼─────────────┼─────────────┼──────────────────────┤
# │ ● running  │ main        │ main        │ /path/to/project/... │
# │ ● stopped  │ feature-123 │ feature-123 │ /path/to/project/... │
# └────────────┴─────────────┴─────────────┴──────────────────────┘
```

## Key Differences from Bash Version

### 1. Simpler Worktree Resolution

**Bash version** had complex auto-detection:
```bash
# Would try to guess which worktree you meant
dv up  # Could be current dir, could prompt, could auto-detect parent
```

**Python version** is explicit:
```bash
dv up              # Always uses current directory
dv up main         # Explicit worktree name
dv up --select     # Opt-in interactive selection
```

### 2. Interactive Selection is Opt-in

```bash
# Bash: Would sometimes prompt, sometimes not (confusing)
dv go

# Python: Only prompts when you ask
dv go              # Uses current directory (no prompt)
dv go --select     # Interactive prompt
```

### 3. Better Error Messages

```bash
# Bash
Error: Worktree not found

# Python
Error: Worktree not found: feature-xyz

Available worktrees:
  main
  feature-123
  bugfix-456
```

### 4. Configuration File

Create `~/.config/dv/config.yml`:

```yaml
# Add custom container images
images:
  rust: rust:1.70
  go: golang:1.21

# Set defaults
dotfiles_dir: ~/my-dotfiles
git_user_name: "Your Name"
```

No more exporting environment variables every time.

## Common Workflows

### Workflow 1: Start New Feature

```bash
# In any worktree directory
dv worktree add feature-new-ui --select  # Pick branch interactively

# Container starts automatically
# Just run:
dv go feature-new-ui
```

### Workflow 2: Quick Context Switch

```bash
# Working on main
dv go main

# Need to check something in another branch
# Exit (Ctrl+D)
dv go feature-123  # Instantly in different container
```

### Workflow 3: Custom Container Image

```bash
# Create devcontainer config
dv template feature-123 python

# Edit if needed
vim feature-123/.devcontainer/devcontainer.json

# Start it
dv up feature-123
```

### Workflow 4: Clean Up Old Branches

```bash
# List all worktrees
dv worktree list

# Remove one
dv worktree remove old-feature

# Or interactive
dv worktree remove --select
```

## Tips

### Use Current Directory (Simplest)

```bash
cd ~/projects/myrepo/main
dv up         # Starts main
dv go         # Enters main

cd ../feature-123
dv up         # Starts feature-123
dv go         # Enters feature-123
```

### Use Explicit Names (Clearest)

```bash
# From anywhere in the project
dv up main
dv go feature-123
dv down old-branch
```

### Use --select (Most Flexible)

```bash
# Pick from a list
dv up --select
dv go --select
dv down --select
```

## Troubleshooting

### Command not found

```bash
# Add to ~/.bashrc or ~/.zshrc:
export PATH="$HOME/.local/bin:$PATH"

# Then reload:
source ~/.bashrc
```

### Config not loading

```bash
# Check config location:
ls ~/.config/dv/config.yml

# Copy example:
cp example-config.yml ~/.config/dv/config.yml
```

### Container won't start

```bash
# Check status
dv status

# View docker logs
docker logs $(docker ps -aq --filter "label=devcontainer.local_folder=$(pwd)")

# Try recreating
dv down
dv up
```

## Next Steps

- Read `COMPARISON.md` to understand the improvements
- Check `README.md` for full documentation
- Customize `~/.config/dv/config.yml` for your workflow
- Add custom container images to the config

## Getting Help

```bash
dv --help              # Main help
dv up --help           # Command-specific help
dv worktree --help     # Subcommand help
```

Every command has detailed help text with examples!
