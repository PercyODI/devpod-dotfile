# devpod-dotfile

A Dotfile repo specifically for devpod environments

## System Requirements

The following is required on the host system. Currently, no automation is set up for this, as it can vary a lot.

### Installed Applications

- Docker / Docker Desktop
- devcontainers
- Modern terminal (Wezterm, kitty, warp, etc)

## Aliases

```terminal
# Starts a dev container instance on the current working directory.
alias dup="devcontainer up \
    --workspace-folder . \
    --dotfiles-repository https://github.com/PercyODI/devpod-dotfile/tree/switch-devcontainer-cli \
    --mount type=bind,source=${SSH_AUTH_SOCK},target=/ssh-agent \
    --update-remote-user-uid-default on \
    --remote-env SSH_AUTH_SOCK=\"/ssh-agent\""

# Starts a dev container instance on the current working directory, and
# removes the old container if it exists
alias dup-reset="devcontainer up \
    --workspace-folder . \
    --dotfiles-repository https://github.com/PercyODI/devpod-dotfile/tree/switch-devcontainer-cli \
    --mount type=bind,source=${SSH_AUTH_SOCK},target=/ssh-agent \
    --update-remote-user-uid-default on \
    --remove-existing-container \
    --remote-env SSH_AUTH_SOCK=\"/ssh-agent\""

# Starts a dev container instance using local dotfiles repo
alias dup-local="devcontainer up \
    --workspace-folder . \
    --mount type=bind,source=/run/host-services/ssh-auth.sock,target=/ssh-agent \
    --mount type=bind,source=$HOME/github/devpod-dotfile,target=/dotfiles \
    --update-remote-user-uid-default on \
    --remove-existing-container && 
    devcontainer exec --workspace-folder . -- bash -lc 'cd /dotfiles && ./install.sh'"

# SSH into the dev container
alias dgo="devcontainer exec --workspace-folder . zsh"
```
