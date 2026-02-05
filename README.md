# devpod-dotfile

A Dotfile repo specifically for devpod environments

## Host System Requirements

The following is required on the host system. Currently, no automation is set up for this, as it can vary a lot.

### Setup

Clone this repository to a known location on your host system:

```bash
git clone https://github.com/PercyODI/devpod-dotfile.git ~/github/devpod-dotfile
```

Add the `host/bin` directory to your PATH by adding the following line to your shell configuration file (`.bashrc`, `.zshrc`, etc.):

```bash
export PATH="$HOME/github/devpod-dotfile/host/bin:$PATH"
```

After reloading your shell configuration (or opening a new terminal), you'll have access to the `d*` commands (e.g., `dup`, `dup-reset`, `dup-local`, `dgo`, `dgo-shell`, `dtemp-node`).

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

| Secret             | Env Var Name      | Default                 |
| ------------------ | ----------------- | ----------------------- |
| Anthropic API Key  | ANTHROPIC_API_KEY |                         |
| OpenAI API Key     | OPENAI_API_KEY    |                         |
| Git User Name      | GIT_USER_NAME     |                         |
| Git User Email     | GIT_USER_EMAIL    |                         |
| Local Dotfile Repo | DOTFILES_DIR      | ~/github/devpod-dotfile |
| Prefer Opencode    | PREFER_OPENCODE   | false                   |

### AI Assistant Selection

The dev container includes both Claude Code and Opencode AI assistants. By default, the `dev` command launches Claude Code. To use Opencode instead, set the `PREFER_OPENCODE` environment variable to `true` in your `~/.envrc` file:

```bash
export PREFER_OPENCODE=true
```

When you run the `dev` command, it will automatically launch the preferred AI assistant in the tmux pane.

## Available Commands

After adding `host/bin` to your PATH, the following commands are available. Alternatively, you can define these as aliases in your shell configuration:

```terminal
# Starts a dev container instance on the current working directory.
alias dup="devcontainer up \
    --workspace-folder . \
    --dotfiles-repository https://github.com/PercyODI/devpod-dotfile \
    --mount type=bind,source=/run/host-services/ssh-auth.sock,target=/ssh/agent \
    --mount type=bind,source=${HOME}/.ssh/known_hosts,target=/ssh/known_hosts,readonly \
    --remote-env ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
    --remote-env OPENAI_API_KEY=${OPENAI_API_KEY} \
    --remote-env PREFER_OPENCODE=${PREFER_OPENCODE:-false} \
    --update-remote-user-uid-default on"

# Starts a dev container instance on the current working directory, and
# removes the old container if it exists
alias dup-reset="devcontainer up \
    --workspace-folder . \
    --dotfiles-repository https://github.com/PercyODI/devpod-dotfile \
    --mount type=bind,source=/run/host-services/ssh-auth.sock,target=/ssh/agent \
    --mount type=bind,source=${HOME}/.ssh/known_hosts,target=/ssh/known_hosts,readonly \
    --remote-env ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
    --remote-env OPENAI_API_KEY=${OPENAI_API_KEY} \
    --remote-env PREFER_OPENCODE=${PREFER_OPENCODE:-false} \
    --update-remote-user-uid-default on \
    --remove-existing-container"

# Starts a dev container instance using local dotfiles repo
alias dup-local=" \
    devcontainer up \
        --workspace-folder . \
        --mount type=bind,source=/run/host-services/ssh-auth.sock,target=/ssh/agent \
        --mount type=bind,source=${HOME}/.ssh/known_hosts,target=/ssh/known_hosts \
        --mount type=bind,source=${DOTFILES_DIR:-${HOME}/github/devpod-dotfile},target=/dotfiles \
        --update-remote-user-uid-default on \
        --remove-existing-container &&
    devcontainer exec \
        --workspace-folder . \
        --remote-env ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
        --remote-env OPENAI_API_KEY=${OPENAI_API_KEY} \
        --remote-env PREFER_OPENCODE=${PREFER_OPENCODE:-false} \
        -- bash -c 'cd /dotfiles && ./install.sh'"

# SSH into the dev container and auto-launch tmux dev command
alias dgo="devcontainer exec \
    --workspace-folder . \
    --remote-env ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
    --remote-env OPENAI_API_KEY=${OPENAI_API_KEY} \
    --remote-env PREFER_OPENCODE=${PREFER_OPENCODE:-false} \
    --remote-env GIT_AUTHOR_NAME=\"${GIT_USER_NAME}\" \
    --remote-env GIT_AUTHOR_EMAIL=\"${GIT_USER_EMAIL}\" \
    --remote-env GIT_COMMITTER_NAME=\"${GIT_USER_NAME}\" \
    --remote-env GIT_COMMITTER_EMAIL=\"${GIT_USER_EMAIL}\" \
    zsh -ic dev"

# SSH into the dev container
alias dgo-shell="devcontainer exec \
    --workspace-folder . \
    --remote-env ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
    --remote-env OPENAI_API_KEY=${OPENAI_API_KEY} \
    --remote-env PREFER_OPENCODE=${PREFER_OPENCODE:-false} \
    --remote-env GIT_AUTHOR_NAME=\"${GIT_USER_NAME}\" \
    --remote-env GIT_AUTHOR_EMAIL=\"${GIT_USER_EMAIL}\" \
    --remote-env GIT_COMMITTER_NAME=\"${GIT_USER_NAME}\" \
    --remote-env GIT_COMMITTER_EMAIL=\"${GIT_USER_EMAIL}\" \
    zsh"
    
# Create a base Typescript/Node .devcontainer 
alias dtemp-node=" \
  devcontainer templates apply \
    -t ghcr.io/devcontainers/templates/typescript-node:4.0.2 \
    --omit-paths '[\".github/\*\"]'"
```
