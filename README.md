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
-- Starts a dev container instance on the current working directory.
alias dup="devcontainer up \
    --workspace-folder . \
    --dotfiles-repository https://github.com/PercyODI/devpod-dotfile \
    --mount type=bind,source=${SSH_AUTH_SOCK},target=/ssh-agent \
    --update-remote-user-uid-default on \
    --remote-env SSH_AUTH_SOCK=\"/ssh-agent\""

-- Starts a dev container instance on the current working directory, and
-- removes the old container if it exists
alias dup-reset="devcontainer up \
    --workspace-folder . \
    --dotfiles-repository https://github.com/PercyODI/devpod-dotfile \
    --mount type=bind,source=${SSH_AUTH_SOCK},target=/ssh-agent \
    --update-remote-user-uid-default on \
    --remove-existing-container \
    --remote-env SSH_AUTH_SOCK=\"/ssh-agent\""

-- SSH into the dev container
alias dgo="devcontainer exec --workspace-folder . /bin/bash"
```
