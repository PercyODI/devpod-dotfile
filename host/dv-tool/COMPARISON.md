# Bash vs Python Implementation Comparison

## Side-by-Side Code Examples

### 1. Worktree Resolution

**Bash (71 lines, complex):**
```bash
resolve_target_worktree() {
  local bare_repo=$(find_bare_repo)

  if [[ -z "$bare_repo" ]]; then
    echo "$(pwd)"
    return 0
  fi

  local worktree_root=$(get_worktree_root)
  local first_arg="$1"

  # Check if first arg is a worktree name (not a flag)
  if [[ -n "$first_arg" ]] && [[ ! "$first_arg" =~ ^- ]]; then
    local candidate="$worktree_root/$first_arg"
    if is_git_worktree "$candidate"; then
      shift
      RESOLVED_ARGS=("$@")  # 🚨 Global state mutation
      echo "$candidate"
      return 0
    fi
  fi

  # Auto-detect from current directory (20 more lines)...
  # Interactive selection fallback (15 more lines)...
}
```

**Python (12 lines, simple):**
```python
def resolve_worktree(self, name: Optional[str] = None) -> Path:
    """Resolve which worktree to operate on."""
    if name:
        worktree = self.get_worktree(name)
        if not worktree:
            raise ValueError(f"Worktree not found: {name}")
        return worktree

    # Use current directory
    return self.path
```

**Key improvements:**
- No global state mutation
- No auto-detection magic
- Explicit error handling
- Interactive selection is opt-in via `--select` flag

---

### 2. Container Status

**Bash (19 lines with duplicated logic):**
```bash
get_container_status() {
  local workspace_path="$1"
  local container_id=$(docker ps -aq \
    --filter "label=devcontainer.local_folder=${workspace_path}")

  if [[ -z "$container_id" ]]; then
    echo "none"
    return
  fi

  local status=$(docker inspect -f '{{.State.Status}}' "$container_id" 2>/dev/null)
  if [[ "$status" == "running" ]]; then
    echo "running"
  elif [[ -n "$status" ]]; then
    echo "stopped"
  else
    echo "none"
  fi
}
```

**Python (26 lines with type safety):**
```python
class ContainerStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    NONE = "none"

    @property
    def color(self) -> str:
        return {
            ContainerStatus.RUNNING: "green",
            ContainerStatus.STOPPED: "yellow",
            ContainerStatus.NONE: "red",
        }[self]

class Container:
    def get_status(self) -> ContainerStatus:
        container_id = self._get_container_id()
        if not container_id:
            return ContainerStatus.NONE

        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", container_id],
            capture_output=True, text=True, check=False,
        )
        status = result.stdout.strip()

        if status == "running":
            return ContainerStatus.RUNNING
        elif status:
            return ContainerStatus.STOPPED
        return ContainerStatus.NONE
```

**Key improvements:**
- Type-safe enum instead of strings
- Encapsulated in a class
- Color/icon properties bundled with status
- No string comparison bugs

---

### 3. Configuration Management

**Bash (23 lines, env vars only):**
```bash
get_remote_env_args() {
  REMOTE_ENV_ARGS=()
  [[ -n "${ANTHROPIC_API_KEY}" ]] && REMOTE_ENV_ARGS+=(--remote-env "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}")
  [[ -n "${OPENAI_API_KEY}" ]] && REMOTE_ENV_ARGS+=(--remote-env "OPENAI_API_KEY=${OPENAI_API_KEY}")
  REMOTE_ENV_ARGS+=(--remote-env "PREFER_OPENCODE=${PREFER_OPENCODE:-false}")
  [[ -n "${GIT_USER_NAME}" ]] && REMOTE_ENV_ARGS+=(--remote-env "GIT_AUTHOR_NAME=${GIT_USER_NAME}")
  [[ -n "${GIT_USER_EMAIL}" ]] && REMOTE_ENV_ARGS+=(--remote-env "GIT_AUTHOR_EMAIL=${GIT_USER_EMAIL}")
  [[ -n "${GIT_USER_NAME}" ]] && REMOTE_ENV_ARGS+=(--remote-env "GIT_COMMITTER_NAME=${GIT_USER_NAME}")
  [[ -n "${GIT_USER_EMAIL}" ]] && REMOTE_ENV_ARGS+=(--remote-env "GIT_COMMITTER_EMAIL=${GIT_USER_EMAIL}")
}
```

**Python (75 lines with YAML + env vars):**
```python
@dataclass
class Config:
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    git_user_name: Optional[str] = None
    git_user_email: Optional[str] = None
    dotfiles_dir: Path = field(default_factory=lambda: Path.home() / "github" / "devpod-dotfile")
    dotfiles_repo: str = "https://github.com/PercyODI/devpod-dotfile"
    images: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Config":
        """Load from environment variables."""
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            # ... etc
        )

    @classmethod
    def from_file(cls, path: Path) -> "Config":
        """Load from YAML file with env override."""
        # ... YAML parsing + env merging

    def get_remote_env_args(self) -> list[str]:
        """Build devcontainer CLI args."""
        # ... clean list building
```

**Key improvements:**
- Type-safe dataclass
- YAML config file support
- Environment variables override config file
- Default values in one place
- Easy to extend

---

### 4. Parallel Arrays vs Structured Data

**Bash (anti-pattern):**
```bash
local worktrees=()        # colored version
local worktrees_plain=()  # non-colored version
local paths=()            # actual paths

# Build three synchronized arrays
worktrees+=("$icon $name ($branch)")
worktrees_plain+=("$plain_icon $name ($branch)")
paths+=("$path")

# Hope they stay synchronized...
```

**Python (proper data structure):**
```python
@dataclass
class WorktreeInfo:
    path: Path
    branch: str
    status: ContainerStatus

    @property
    def name(self) -> str:
        return self.path.name

# Build single list of structured objects
worktrees: list[WorktreeInfo] = []
for line in git_output:
    worktrees.append(WorktreeInfo(
        path=Path(path),
        branch=branch,
        status=container.get_status(),
    ))
```

---

### 5. Error Handling

**Bash:**
```bash
set -e  # Die on ANY error - too blunt

# No cleanup, no rollback
# Can't distinguish between different error types
# No way to recover
```

**Python:**
```python
try:
    worktree_path = ws.add_worktree(branch)
    success(f"Worktree created at: {worktree_path}")

    if not no_start:
        subprocess.run(["devcontainer", "up", ...], check=True)
        success("Devcontainer started")

except ValueError as e:
    error(f"Invalid input: {e}")
    sys.exit(1)
except subprocess.CalledProcessError as e:
    error(f"Command failed: {e}")
    # Could rollback worktree creation here
    sys.exit(1)
```

**Key improvements:**
- Granular error handling
- Distinguish error types
- Can rollback on partial failure
- Better error messages

---

### 6. CLI Argument Parsing

**Bash (manual parsing):**
```bash
while [[ $# -gt 0 ]]; do
  case $1 in
    --dotfile|-d)
      use_dotfile_repo=true
      shift
      ;;
    *)
      error "Unknown option: $1"
      return 1
      ;;
  esac
done
```

**Python (Click framework):**
```python
@click.command()
@click.argument("worktree", required=False)
@click.option("--dotfile", "-d", is_flag=True, help="Use external dotfiles")
@click.option("--select", "-s", is_flag=True, help="Interactive selection")
def up(worktree: Optional[str], dotfile: bool, select: bool) -> None:
    """Start the devcontainer."""
    # Arguments already parsed and validated
```

**Key improvements:**
- Auto-generated help text
- Type conversion
- Validation
- Tab completion support
- Less boilerplate

---

### 7. Help System

**Bash (500+ lines of heredocs):**
```bash
show_help() {
  cat <<EOF
dv - Devcontainer management tool

Usage:
  dv <command> [options]

# ... 50 more lines
EOF
}

cmd_up() {
  if [[ $1 == "--help" ]]; then
    cat <<EOF
Usage: dv up [worktree] [--dotfile]
# ... 30 more lines
EOF
    return 0
  fi
  # ... actual implementation
}
```

**Python (auto-generated from docstrings):**
```python
@click.command()
@click.argument("worktree", required=False)
@click.option("--dotfile", "-d", is_flag=True, help="Use external dotfiles")
def up(worktree: Optional[str], dotfile: bool) -> None:
    """Start the devcontainer.

    Examples:
        dv up main
        dv up --dotfile
    """
    # Click generates help automatically from:
    # - Function signature
    # - Docstring
    # - Option help text
```

---

## Metrics Comparison

| Metric | Bash | Python |
|--------|------|--------|
| Total lines | 1,203 | ~800 |
| Lines in main CLI | 500+ | 350 |
| Help text | 500+ | 0 (auto-generated) |
| Error handling | `set -e` | Try/except per operation |
| Type safety | None | Full type hints |
| Data structures | Arrays/strings | Dataclasses/Enums |
| Testing | Hard | Easy |
| Dependencies | bash 4+, git, docker | Python 3.9+, click, rich |

## When to Use Each

### Use Bash when:
- One-off scripts
- Simple wrappers (< 200 lines)
- Only using basic tools
- No error recovery needed

### Use Python when:
- Complex business logic
- Team collaboration
- Need testing
- Configuration management
- Multiple data structures
- Error recovery needed
- Long-term maintenance

## Conclusion

The Python version is:
- **More maintainable** - Clear structure, type hints
- **More robust** - Better error handling
- **More testable** - Unit tests, mocking
- **More extensible** - Easy to add features
- **Simpler** - Less code for same functionality

Trade-off: Requires Python runtime (but most systems have it).
