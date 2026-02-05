#!/usr/bin/env bash
set -euo pipefail

MARK_DIR="${HOME}/.local/state/devpod-dotfiles/steps"
mkdir -p "$MARK_DIR"

log() { printf "\n[%s] %s\n" "$(date -Is)" "$*"; }

have() { command -v "$1" >/dev/null 2>&1; }

mark_path() {
  # sanitize name -> filename
  local name="${1//[^a-zA-Z0-9_.-]/_}"
  echo "${MARK_DIR}/${name}.done"
}

run_step() {
  local name="$1"
  shift
  local m
  m="$(mark_path "$name")"

  if [[ -f "$m" ]]; then
    log "SKIP  $name (marker exists: $m)"
    return 0
  fi

  log "RUN   $name"
  "$@"
  : >"$m"
  log "DONE  $name (marked: $m)"
}

# ---------------------------
# Package install (Debian/Ubuntu)
# ---------------------------
install_pkgs_debian() {
  sudo apt-get update -y
  sudo apt-get install -y \
    git curl ca-certificates unzip \
    zsh \
    ripgrep \
    fd-find \
    fzf \
    jq \
    build-essential \
    openssh-client \
    tmux
}

# Make `fd` available even if distro uses `fdfind`
ensure_fd_shim() {
  if have fd; then return 0; fi
  if have fdfind; then
    mkdir -p "${HOME}/.local/bin"
    ln -sf "$(command -v fdfind)" "${HOME}/.local/bin/fd"
    return 0
  fi
  # If neither exists, don't fail the whole bootstrap
  log "WARN  fd/fdfind not found; skipping fd shim"
  return 0
}

# ---------------------------
# Install lazy git
# ---------------------------
install_lazygit() {
  local tmp
  tmp="$(mktemp -d)"
  trap 'rm -rf "${tmp:-}"' RETURN

  local LAZYGIT_VERSION=$(curl -s "https://api.github.com/repos/jesseduffield/lazygit/releases/latest" | \grep -Po '"tag_name": *"v\K[^"]*')
  curl -Lo "$tmp/lazygit.tar.gz" "https://github.com/jesseduffield/lazygit/releases/download/v${LAZYGIT_VERSION}/lazygit_${LAZYGIT_VERSION}_Linux_x86_64.tar.gz"
  tar -xzf "$tmp/lazygit.tar.gz" -C "$tmp" lazygit
  sudo install "$tmp/lazygit" -D -t /usr/local/bin/
}

# ---------------------------
# Neovim install (pinned release)
# ---------------------------
install_neovim_release() {
  local NVIM_VER="0.11.5"

  if have nvim; then
    return 0
  fi

  local arch
  arch="$(uname -m)"
  case "$arch" in
  x86_64 | amd64) arch="linux-x86_64" ;;
  aarch64 | arm64) arch="linux-arm64" ;;
  *)
    log "WARN  Unsupported arch for nvim release tarball: $(uname -m). Skipping nvim install."
    return 0
    ;;
  esac

  local tmp
  tmp="$(mktemp -d)"
  trap 'rm -rf "${tmp:-}"' RETURN

  curl -fsSL -o "$tmp/nvim.tar.gz" \
    "https://github.com/neovim/neovim/releases/download/v${NVIM_VER}/nvim-${arch}.tar.gz"

  tar -C "$tmp" -xzf "$tmp/nvim.tar.gz"

  # Directory names in official artifacts:
  # - linux64 -> nvim-linux-x86_64
  # - linuxarm64 -> nvim-linux-arm64
  local extracted="nvim-${arch}"
  local extracted_dir="$tmp/$extracted"

  if [[ ! -d "$extracted_dir" ]]; then
    # fallback to common names if artifact naming differs
    extracted_dir="$(find "$tmp" -maxdepth 1 -type d -name 'nvim-linux*' | head -n1 || true)"
  fi

  if [[ -z "${extracted_dir:-}" || ! -d "$extracted_dir" ]]; then
    log "WARN  Could not find extracted nvim dir; skipping nvim install."
    return 0
  fi

  sudo rm -rf /opt/nvim
  sudo mv "$extracted_dir" /opt/nvim
  sudo ln -sf /opt/nvim/bin/nvim /usr/local/bin/nvim
}

# ---------------------------
# Dotfiles linking
# ---------------------------
link_configs() {
  # Get the directory where install.sh lives (dotfiles repo root in your layout)
  local script_dir
  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

  mkdir -p "${HOME}/.config"

  # --- Neovim config ---
  local target_nvim="${script_dir}/nvim"
  local dest_nvim="${HOME}/.config/nvim"

  if [[ ! -d "$target_nvim" ]]; then
    log "WARN  Expected nvim config at: $target_nvim (not found). Skipping nvim link."
  else
    # If dest exists and is not a symlink, back it up
    if [[ -e "$dest_nvim" && ! -L "$dest_nvim" ]]; then
      local backup="${dest_nvim}.bak.$(date +%Y%m%d%H%M%S)"
      log "INFO  Backing up existing $dest_nvim -> $backup"
      mv "$dest_nvim" "$backup"
    fi

    # If it's a symlink but points somewhere else, replace it
    if [[ -L "$dest_nvim" ]]; then
      rm -f "$dest_nvim"
    fi

    ln -s "$target_nvim" "$dest_nvim"
    log "INFO  Linked nvim config: $dest_nvim -> $target_nvim"
  fi

  # --- Zsh rc ---
  local target_zshrc="${script_dir}/zsh/.zshrc"
  local dest_zshrc="${HOME}/.zshrc"

  if [[ -f "$target_zshrc" ]]; then
    ln -snf "$target_zshrc" "$dest_zshrc"
    log "INFO  Linked zshrc: $dest_zshrc -> $target_zshrc"
  else
    log "WARN  Expected zshrc at: $target_zshrc (not found). Skipping zshrc link."
  fi

  # --- oh-my-zsh Customization
  local target_ohmyzsh="${script_dir}/zsh/oh-my-zsh/custom"
  local dest_ohmyzsh="${HOME}/.oh-my-zsh/custom"

  if [[ ! -d "$target_ohmyzsh" ]]; then
    log "WARN  Expected oh-my-zsh config at: $target_ohmyzsh (not found). Skipping oh-my-zsh link."
  else
    # If dest exists and is not a symlink, back it up
    if [[ -e "${dest_ohmyzsh}" && ! -L "${dest_ohmyzsh}" ]]; then
      local backup="${dest_ohmyzsh}.bak.$(date +%Y%m%d%H%M%S)"
      log "INFO  Backing up existing $dest_ohmyzsh -> $backup"
      mv "${dest_ohmyzsh}" "$backup"
    fi

    # If it's a symlink but points somewhere else, replace it
    if [[ -L "${dest_ohmyzsh}" ]]; then
      rm -f "${dest_ohmyzsh}"
    fi

    ln -s "${target_ohmyzsh}" "${dest_ohmyzsh}"
    log "INFO  Linked oh-my-zsh config: $dest_ohmyzsh -> $target_ohmyzsh"
  fi

  # --- Lazygit config ---
  local target_lazygit="${script_dir}/lazygit"
  local dest_lazygit="${HOME}/.config/lazygit"

  if [[ ! -d "$target_lazygit" ]]; then
    log "WARN  Expected lazygit config at: $target_lazygit (not found). Skipping lazygit link."
  else
    # If dest exists and is not a symlink, back it up
    if [[ -e "$dest_lazygit" && ! -L "$dest_lazygit" ]]; then
      local backup="${dest_lazygit}.bak.$(date +%Y%m%d%H%M%S)"
      log "INFO  Backing up existing $dest_lazygit -> $backup"
      mv "$dest_lazygit" "$backup"
    fi

    # If it's a symlink but points somewhere else, replace it
    if [[ -L "$dest_lazygit" ]]; then
      rm -f "$dest_lazygit"
    fi

    ln -s "$target_lazygit" "$dest_lazygit"
    log "INFO  Linked lazygit config: $dest_lazygit -> $target_lazygit"
  fi

  # --- Tmux config ---
  local target_tmux="${script_dir}/tmux"
  local dest_tmux="${HOME}/.config/tmux"

  if [[ ! -d "$target_tmux" ]]; then
    log "WARN  Expected tmux config at: $target_tmux (not found). Skipping tmux link."
  else
    # If dest exists and is not a symlink, back it up
    if [[ -e "$dest_tmux" && ! -L "$dest_tmux" ]]; then
      local backup="${dest_tmux}.bak.$(date +%Y%m%d%H%M%S)"
      log "INFO  Backing up existing $dest_tmux -> $backup"
      mv "$dest_tmux" "$backup"
    fi

    # If it's a symlink but points somewhere else, replace it
    if [[ -L "$dest_tmux" ]]; then
      rm -f "$dest_tmux"
    fi

    ln -s "$target_tmux" "$dest_tmux"
    log "INFO  Linked tmux config: $dest_tmux -> $target_tmux"
  fi
}

# ---------------------------
# oh-my-zsh
# ---------------------------
install_oh_my_zsh() {
  if [[ -d "${HOME}/.oh-my-zsh" ]]; then
    return 0
  fi
  RUNZSH=no CHSH=no KEEP_ZSHRC=yes \
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
}

# Try to set default shell (best effort; don't fail if not allowed)
# set_default_shell_zsh() {
#   if ! have zsh; then return 0; fi
#   if [[ "${SHELL:-}" == "$(command -v zsh)" ]]; then return 0; fi
#
#   # chsh may not exist or may be blocked in containers; treat as best-effort
#   if have chsh; then
#     chsh -s "$(command -v zsh)" || true
#   fi
#   return 0
# }

# ---------------------------
# LazyVim bootstrap
# ---------------------------
lazyvim_sync() {
  # If nvim isn't present, no-op
  if ! have nvim; then
    log "WARN  nvim not found; skipping Lazy sync"
    return 0
  fi

  # Don't fail the entire bootstrap if plugins have transient issues
  nvim --headless "+Lazy! sync" +qa || true
}

# ---------------------------
# Claude Code install
# ---------------------------
install_claude_code() {
  if have claude; then
    log "INFO  Claude Code already installed: $(command -v claude)"
    return 0
  fi

  log "INFO  Installing Claude Code..."
  # Run in non-interactive mode to avoid terminal control sequences
  curl -fsSL https://claude.ai/install.sh | bash -s -- 2>&1 | cat

  # Ensure ~/.local/bin is in PATH for current session
  export PATH="${HOME}/.local/bin:${PATH}"

  # Verify installation
  if ! have claude; then
    log "WARN  Claude Code installation completed but binary not found in PATH"
    return 1
  fi

  log "INFO  Claude Code installed successfully: $(command -v claude)"
}

# ---------------------------
# Opencode install
# ---------------------------
install_opencode() {
  if have opencode; then
    log "INFO  Opencode already installed: $(command -v opencode)"
    return 0
  fi

  log "INFO  Installing Opencode..."
  # Run in non-interactive mode to avoid terminal control sequences
  curl -fsSL https://opencode.ai/install | bash -s -- 2>&1 | cat

  # Ensure ~/.opencode/bin is in PATH for current session
  export PATH="${HOME}/.opencode/bin:${PATH}"

  # Verify installation
  if ! have opencode; then
    log "WARN  Opencode installation completed but binary not found in PATH"
    return 1
  fi

  log "INFO  Opencode installed successfully: $(command -v opencode)"
}

configure_claude_code() {
  local script_dir
  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

  # --- ~/.claude/settings.json ---
  # Create Claude config directory
  mkdir -p "${HOME}/.claude"

  # Link Claude settings from repo
  local target_claude="${script_dir}/claude/settings.json"
  local dest_claude="${HOME}/.claude/settings.json"

  if [[ ! -f "$target_claude" ]]; then
    log "WARN  Expected Claude settings at: $target_claude (not found). Skipping Claude config."
    return 0
  fi

  # Backup existing config if present
  if [[ -e "$dest_claude" && ! -L "$dest_claude" ]]; then
    local backup="${dest_claude}.bak.$(date +%Y%m%d%H%M%S)"
    log "INFO  Backing up existing Claude settings: $dest_claude -> $backup"
    mv "$dest_claude" "$backup"
  fi

  # Remove old symlink if it points elsewhere
  if [[ -L "$dest_claude" ]]; then
    rm -f "$dest_claude"
  fi

  # Create symlink
  ln -s "$target_claude" "$dest_claude"
  log "INFO  Linked Claude settings: $dest_claude -> $target_claude"

  # --- ~/.claude.json ---
  # Copy and configure Claude settings from template
  local template_claude_json="${script_dir}/claude/claude.json.template"
  local dest_claude_json="${HOME}/.claude.json"

  if [[ ! -f "$template_claude_json" ]]; then
    log "WARN  Expected .claude.json template at: $template_claude_json (not found). Skipping .claude.json config."
    return 0
  fi

  # Backup existing config if present
  if [[ -e "$dest_claude_json" && ! -L "$dest_claude_json" ]]; then
    local backup="${dest_claude_json}.bak.$(date +%Y%m%d%H%M%S)"
    log "INFO  Backing up existing .claude.json settings: $dest_claude_json -> $backup"
    mv "$dest_claude_json" "$backup"
  fi

  # Remove old symlink if it points elsewhere
  if [[ -L "$dest_claude_json" ]]; then
    rm -f "$dest_claude_json"
  fi

  # Copy template to destination
  cp "$template_claude_json" "$dest_claude_json"
  log "INFO  Copied .claude.json template to: $dest_claude_json"

  # Get API key suffix from environment variable if available
  if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    local api_key="${ANTHROPIC_API_KEY}"

    if [[ ${#api_key} -ge 20 ]]; then
      local api_key_suffix="${api_key: -20}"

      # Add API key suffix to approved list using jq
      local tmp_json
      tmp_json="$(mktemp)"
      jq --arg key "$api_key_suffix" '.customApiKeyResponses.approved += [$key]' "$dest_claude_json" >"$tmp_json"
      mv "$tmp_json" "$dest_claude_json"
      log "INFO  Added API key suffix to approved list"
    else
      log "WARN  ANTHROPIC_API_KEY is too short (less than 20 characters)"
    fi
  else
    log "INFO  ANTHROPIC_API_KEY not set. Skipping API key configuration."
  fi

  # Determine project path (find actual project, not dotfiles directory)
  local project_path=""
  if [[ -d "/workspaces" ]]; then
    # Find first directory in /workspaces that isn't the dotfiles directory
    for dir in /workspaces/*/; do
      dir="${dir%/}" # Remove trailing slash
      if [[ "$dir" != "$script_dir" && -d "$dir" ]]; then
        project_path="$dir"
        break
      fi
    done
  fi

  # Exit if no project found
  if [[ -z "$project_path" ]]; then
    log "WARN  No project directory found in /workspaces (excluding dotfiles). Skipping project configuration."
    return 0
  fi

  # Add project entry using jq
  local tmp_json
  tmp_json="$(mktemp)"
  jq --arg path "$project_path" '.projects[$path] = {"allowedTools": [], "mcpContextUris": [], "mcpServers": {}, "enabledMcpjsonServers": [], "disabledMcpjsonServers": [], "hasTrustDialogAccepted": true}' "$dest_claude_json" >"$tmp_json"
  mv "$tmp_json" "$dest_claude_json"
  log "INFO  Added project configuration for: $project_path"

  # Verify Claude Code works (non-interactive test)
  if have claude; then
    log "INFO  Verifying Claude Code installation..."
    claude --version || log "WARN  Claude Code verification returned non-zero exit"
  fi
}

configure_opencode() {
  local script_dir
  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

  # Create Opencode config directory
  mkdir -p "${HOME}/.config/opencode"

  # Copy Opencode config from repo
  local target_opencode="${script_dir}/opencode/opencode.json"
  local dest_opencode="${HOME}/.config/opencode/opencode.json"

  if [[ ! -f "$target_opencode" ]]; then
    log "WARN  Expected Opencode config at: $target_opencode (not found). Skipping Opencode config."
    return 0
  fi

  # Backup existing config if present
  if [[ -e "$dest_opencode" && ! -L "$dest_opencode" ]]; then
    local backup="${dest_opencode}.bak.$(date +%Y%m%d%H%M%S)"
    log "INFO  Backing up existing Opencode config: $dest_opencode -> $backup"
    mv "$dest_opencode" "$backup"
  fi

  # Remove old symlink if it points elsewhere
  if [[ -L "$dest_opencode" ]]; then
    rm -f "$dest_opencode"
  fi

  # Copy config to destination
  cp "$target_opencode" "$dest_opencode"
  log "INFO  Copied Opencode config to: $dest_opencode"

  # Verify Opencode works (non-interactive test)
  if have opencode; then
    log "INFO  Verifying Opencode installation..."
    opencode --version || log "WARN  Opencode verification returned non-zero exit"
  fi
}

configure_git() {
  # Configure git to trust all workspace directories
  # This prevents "dubious ownership" errors in devcontainers
  # where the filesystem owner may not match the container user

  if ! have git; then
    log "WARN  git not found; skipping git configuration"
    return 0
  fi

  git config --global --add safe.directory '/workspaces/*' || true
  log "INFO  Configured git safe.directory: /workspaces/*"
}

configure_ssh() {
  sudo chmod 666 /ssh/agent

  # Configure SSH known_hosts
  local mounted_known_hosts="/ssh/known_hosts"
  local dest_ssh_dir="${HOME}/.ssh"
  local dest_known_hosts="${dest_ssh_dir}/known_hosts"

  # Create .ssh directory if it doesn't exist
  mkdir -p "$dest_ssh_dir"
  chmod 700 "$dest_ssh_dir"

  if [[ ! -f "$mounted_known_hosts" ]]; then
    log "WARN  Expected mounted SSH known_hosts at: $mounted_known_hosts (not found). Skipping known_hosts config."
    return 0
  fi

  # Remove existing known_hosts if it exists (whether file or symlink)
  if [[ -e "$dest_known_hosts" || -L "$dest_known_hosts" ]]; then
    rm -f "$dest_known_hosts"
  fi

  # Create symlink to mounted known_hosts
  ln -s "$mounted_known_hosts" "$dest_known_hosts"
  log "INFO  Linked SSH known_hosts: $dest_known_hosts -> $mounted_known_hosts"
}

# ---------------------------
# Run multiple steps in parallel with side-by-side output
# ---------------------------
run_steps_parallel() {
  local -a names=()
  local -a funcs=()
  local -a pids=()
  local -a tmpfiles=()
  local -a markers=()

  # Parse arguments: name1 func1 name2 func2 ...
  while [[ $# -gt 0 ]]; do
    names+=("$1")
    funcs+=("$2")
    shift 2
  done

  local num_tasks=${#names[@]}
  if [[ $num_tasks -eq 0 ]]; then
    return 0
  fi

  # Check if any tasks are already done
  local -a pending_names=()
  local -a pending_funcs=()
  for i in "${!names[@]}"; do
    local m="$(mark_path "${names[$i]}")"
    if [[ -f "$m" ]]; then
      log "SKIP  ${names[$i]} (marker exists: $m)"
    else
      pending_names+=("${names[$i]}")
      pending_funcs+=("${funcs[$i]}")
    fi
  done

  # If nothing to do, return
  if [[ ${#pending_names[@]} -eq 0 ]]; then
    return 0
  fi

  # Start all tasks in background
  for i in "${!pending_names[@]}"; do
    local name="${pending_names[$i]}"
    local func="${pending_funcs[$i]}"
    local tmpfile="$(mktemp)"
    local m="$(mark_path "$name")"

    tmpfiles+=("$tmpfile")
    markers+=("$m")

    log "RUN   $name (parallel)"

    # Run in background, redirecting all output to tmpfile
    (
      "$func" >"$tmpfile" 2>&1
      local exit_code=$?
      if [[ $exit_code -eq 0 ]]; then
        : >"$m"
        echo "[DONE] $name" >>"$tmpfile"
      else
        echo "[FAILED] $name (exit code: $exit_code)" >>"$tmpfile"
      fi
    ) &

    pids+=($!)
  done

  # Print initial header
  printf "\n=== Installing in parallel (monitoring progress) ===\n"

  # Monitor progress with side-by-side display
  # Fixed display height: 1 header line + 10 content lines = 11 lines total
  local display_lines=11
  local still_running=true
  local first_iteration=true

  while $still_running; do
    still_running=false

    # Check if any process is still running
    for pid in "${pids[@]}"; do
      if kill -0 "$pid" 2>/dev/null; then
        still_running=true
        break
      fi
    done

    # Move cursor back up to overwrite previous output (except on first iteration)
    if [[ "$first_iteration" = false ]]; then
      tput cuu $display_lines
    fi
    first_iteration=false

    # Get last 10 lines from each tmpfile and display side-by-side
    # Strip ANSI escape codes, carriage returns, and other control characters to prevent display issues
    # This removes: escape sequences, CR, backspace, and other non-printable characters except newline/tab
    local sanitize='sed "s/\x1b\[[0-9;]*[a-zA-Z]//g; s/\x1b[()][AB012]//g; s/\r//g; s/[\x08\x0B\x0C]//g"'
    local output=""
    if [[ ${#tmpfiles[@]} -eq 1 ]]; then
      # Single column: header + 10 lines
      output=$(echo "=== ${pending_names[0]} ===" && tail -n 10 "${tmpfiles[0]}" 2>/dev/null | eval "$sanitize" | head -n 10 || echo "")
    elif [[ ${#tmpfiles[@]} -eq 2 ]]; then
      # Two columns
      output=$(pr -m -t -w "$(tput cols)" \
        <(echo "=== ${pending_names[0]} ===" && tail -n 10 "${tmpfiles[0]}" 2>/dev/null | eval "$sanitize" | head -n 10 || echo "") \
        <(echo "=== ${pending_names[1]} ===" && tail -n 10 "${tmpfiles[1]}" 2>/dev/null | eval "$sanitize" | head -n 10 || echo "") 2>/dev/null || echo "")
    else
      # Three or more columns
      output=$(pr -m -t -w "$(tput cols)" \
        <(echo "=== ${pending_names[0]} ===" && tail -n 10 "${tmpfiles[0]}" 2>/dev/null | eval "$sanitize" | head -n 10 || echo "") \
        <(echo "=== ${pending_names[1]} ===" && tail -n 10 "${tmpfiles[1]}" 2>/dev/null | eval "$sanitize" | head -n 10 || echo "") \
        <(echo "=== ${pending_names[2]:-} ===" && tail -n 10 "${tmpfiles[2]:-/dev/null}" 2>/dev/null | eval "$sanitize" | head -n 10 || echo "") 2>/dev/null || echo "")
    fi

    # Print exactly display_lines lines (pad with empty lines if needed)
    local line_count=0
    while IFS= read -r line && [[ $line_count -lt $display_lines ]]; do
      tput el # Clear to end of line
      printf "%s\n" "$line"
      line_count=$((line_count + 1))
    done <<<"$output"

    # Pad with empty lines to maintain fixed height
    while [[ $line_count -lt $display_lines ]]; do
      tput el
      printf "\n"
      line_count=$((line_count + 1))
    done

    if $still_running; then
      sleep 0.2
    fi
  done

  # Wait for all processes to complete
  wait

  # Show final output - leave the last display in place
  printf "\n\n=== Parallel installation complete ===\n\n"

  # Check for failures and show full output for failed tasks
  local has_failures=false
  for i in "${!pending_names[@]}"; do
    local name="${pending_names[$i]}"
    local tmpfile="${tmpfiles[$i]}"
    local m="${markers[$i]}"

    if [[ -f "$m" ]]; then
      log "DONE  $name"
    else
      has_failures=true
      log "FAILED  $name"
      printf "\n--- Full output for: %s ---\n" "$name"
      cat "$tmpfile"
      printf "\n"
    fi
  done

  # If no failures, we're done
  if [[ "$has_failures" = true ]]; then
    log "ERROR Some parallel tasks failed. See output above."
    # Cleanup temp files
    for tmpfile in "${tmpfiles[@]}"; do
      rm -f "$tmpfile"
    done
    return 1
  fi

  # Cleanup temp files
  for tmpfile in "${tmpfiles[@]}"; do
    rm -f "$tmpfile"
  done
}
# ---------------------------
# Main
# ---------------------------
main() {
  # Ensure sudo is available if we need it; if not, we can still link configs
  if ! have sudo; then
    log "WARN  sudo not found. Package installs / /opt installs may fail; continuing with user-level steps."
  fi

  # Install packages only on Debian/Ubuntu (safe guard)
  if [[ -f /etc/debian_version ]]; then
    run_step "apt_update_and_install_packages" install_pkgs_debian
    run_step "ensure_fd_shim" ensure_fd_shim
  else
    log "INFO  Non-debian base detected; skipping apt package step"
  fi

  run_step "install_neovim" install_neovim_release
  run_step "install_oh_my_zsh" install_oh_my_zsh
  run_step "link_nvim_zsh_lazygit_and_tmux_configs" link_configs
  # run_step "set_default_shell_zsh" set_default_shell_zsh
  run_step "install_lazygit" install_lazygit

  # Install Claude Code, Opencode, and LazyVim Plugins in parallel with side-by-side output
  run_steps_parallel \
    "install_claude_code" install_claude_code \
    "install_opencode" install_opencode \
    "lazyvim_sync_plugins" lazyvim_sync

  run_step "configure_git" configure_git
  run_step "configure_claude_code" configure_claude_code
  run_step "configure_opencode" configure_opencode
  run_step "configure_ssh" configure_ssh

  log "All steps complete."
}

main "$@"
