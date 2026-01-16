# devpod-dotfile

A Dotfile repo specifically for devpod environments


## Host System Requirements

The following is required on the host system. Currently, no automation is set up for this, as it can vary a lot.

### Installed Applications

- Docker Desktop
- [Dev Container Cli](https://github.com/devcontainers/cli)
- [direnv](https://direnv.net/)
    - https://www.papermtn.co.uk/secrets-management-managing-environment-variables-with-direnv/
- Modern terminal (Wezterm, kitty, warp, iterm2, etc)

### SSH Keys

In order to use git via ssh, you must have the SSH Keys added to the keychain on the host. For example:

```
ssh-add ~/.ssh/github_id_ed25519
```

### Secrets

Secrets are expected to exist in `~/.envrc` on the via direnv host. Secrets will be loaded into the container with a specific env var name.

| Secret | Env Var Name |
|--------|--------------|
| Anthropic API Key | ANTHROPIC_API_KEY |
| Git User Name | GIT_USER_NAME |
| Git User Email | GIT_USER_EMAIL |

## Aliases

```terminal
# Starts a dev container instance on the current working directory.
alias dup="devcontainer up \
    --workspace-folder . \
    --dotfiles-repository https://github.com/PercyODI/devpod-dotfile \
    --mount type=bind,source=${SSH_AUTH_SOCK},target=/ssh-agent \
    --remote-env ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
    --update-remote-user-uid-default on"

# Starts a dev container instance on the current working directory, and
# removes the old container if it exists
alias dup-reset="devcontainer up \
    --workspace-folder . \
    --dotfiles-repository https://github.com/PercyODI/devpod-dotfile \
    --mount type=bind,source=${SSH_AUTH_SOCK},target=/ssh-agent \
    --remote-env ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
    --update-remote-user-uid-default on \
    --remove-existing-container"

# Starts a dev container instance using local dotfiles repo
alias dup-local="\
    devcontainer up \
        --workspace-folder . \
        --mount type=bind,source=/run/host-services/ssh-auth.sock,target=/ssh-agent \
        --mount type=bind,source=$HOME/github/devpod-dotfile,target=/dotfiles \
        --update-remote-user-uid-default on \
        --remove-existing-container &&
    devcontainer exec \
        --workspace-folder . \
        --remote-env ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
        -- bash -lc 'cd /dotfiles && ./install.sh'"

# SSH into the dev container
alias dgo='devcontainer exec \
    --workspace-folder . \
    --remote-env ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
    --remote-env GIT_AUTHOR_NAME=${GIT_USER_NAME} \
    --remote-env GIT_AUTHOR_EMAIL=${GIT_USER_EMAIL} \
    zsh'
```
