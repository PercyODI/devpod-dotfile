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
    build-essential
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
# Neovim install (pinned release)
# ---------------------------
install_neovim_release() {
  local NVIM_VER="0.11.5"

  if have nvim; then
    # Already present; do nothing.
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
  trap 'rm -rf "$tmp"' RETURN

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
  run_step "link_nvim_and_zsh_configs" link_configs
  run_step "install_oh_my_zsh" install_oh_my_zsh
  # run_step "set_default_shell_zsh" set_default_shell_zsh
  run_step "lazyvim_sync_plugins" lazyvim_sync

  log "All steps complete."
}

main "$@"
