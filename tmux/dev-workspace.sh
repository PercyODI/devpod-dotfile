#!/usr/bin/env bash
# dev-workspace.sh - Initialize a tmux development workspace with nvim, Claude, command panels

set -euo pipefail

SESSION_NAME="${1:-dev}"
WORK_DIR="${2:-$(pwd)}"
PROJECT_NAME="$(basename "$WORK_DIR")"
WINDOW_NAME="$PROJECT_NAME"

# Set terminal tab title (works for WezTerm, iTerm2, and most modern terminals)
printf '\033]0;%s\007' "$PROJECT_NAME"

# If session exists, attach/switch
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "Session '$SESSION_NAME' already exists. Attaching..."
  if [ -z "${TMUX:-}" ]; then
    tmux attach-session -t "$SESSION_NAME"
  else
    tmux switch-client -t "$SESSION_NAME"
  fi
  exit 0
fi

# Create new session (pane 0)
tmux new-session -d -x- -y- -s "$SESSION_NAME" -n "$PROJECT_NAME" -c "$WORK_DIR"

# 1) Create bottom full-width Commands pane (starts as pane 1, becomes pane 2 after Claude pane is created)
tmux split-window -v -l 10% -c "$WORK_DIR" -t "$SESSION_NAME:$WINDOW_NAME.0"

# Ensure we’re operating in the top pane (pane 0) for the remaining splits
tmux select-pane -t "$SESSION_NAME:$WINDOW_NAME.0"

# Create the right Claude pane
tmux split-window -h -l 33% -c "$WORK_DIR" -t "$SESSION_NAME:$WINDOW_NAME.0"

# Force command pane to correct size after all splits are complete
# tmux resize-pane -t "$SESSION_NAME:$WINDOW_NAME.2" -y 5%

# Set pane titles (requires pane-border-status for display)
tmux select-pane -t "$SESSION_NAME:$WINDOW_NAME.0" -T "Neovim"
tmux select-pane -t "$SESSION_NAME:$WINDOW_NAME.1" -T "Claude"
tmux select-pane -t "$SESSION_NAME:$WINDOW_NAME.2" -T "Commands"
# tmux select-pane -t "$SESSION_NAME:$WINDOW_NAME.3" -T "Tests"

# Start processes
tmux send-keys -t "$SESSION_NAME:$WINDOW_NAME.0" "cd \"$WORK_DIR\" && nvim ." C-m
tmux send-keys -t "$SESSION_NAME:$WINDOW_NAME.1" "cd \"$WORK_DIR\" && claude" C-m
tmux send-keys -t "$SESSION_NAME:$WINDOW_NAME.2" "cd \"$WORK_DIR\" && echo 'Command pane - Run builds, git commands, etc.'" C-m
# tmux send-keys -t "$SESSION_NAME:$WINDOW_NAME.3" "cd \"$WORK_DIR\" && echo 'Test watcher pane - Run your test commands here'" C-m

# Focus Neovim
tmux select-pane -t "$SESSION_NAME:$WINDOW_NAME.0"

# Attach/switch
if [ -z "${TMUX:-}" ]; then
  tmux attach-session -t "$SESSION_NAME"
else
  tmux switch-client -t "$SESSION_NAME"
fi
