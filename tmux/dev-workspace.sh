#!/usr/bin/env bash
# dev-workspace.sh - Initialize a tmux development workspace with nvim, Claude, test watcher, and command panels

set -euo pipefail

SESSION_NAME="${1:-dev}"
WORK_DIR="${2:-$(pwd)}"

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
tmux new-session -d -s "$SESSION_NAME" -n "editor" -c "$WORK_DIR"

# 1) Create bottom full-width Commands pane (pane 1)
tmux split-window -v -l 20% -c "$WORK_DIR" -t "$SESSION_NAME:editor.0"

# Ensure we’re operating in the top pane (pane 0) for the remaining splits
tmux select-pane -t "$SESSION_NAME:editor.0"

# Create the right Claude pane
tmux split-window -h -l 40% -c "$WORK_DIR" -t "$SESSION_NAME:editor.0"

# 3) Split the right pane vertically into Claude (top ~60%) and Tests (bottom ~40%)
# Target the right pane (pane 2), split off the bottom 40% -> new pane 3
# tmux split-window -h -l 40% -c "$WORK_DIR" -t "$SESSION_NAME:editor.2"

# Set pane titles (requires pane-border-status for display)
tmux select-pane -t "$SESSION_NAME:editor.0" -T "Neovim"
tmux select-pane -t "$SESSION_NAME:editor.1" -T "Claude"
tmux select-pane -t "$SESSION_NAME:editor.2" -T "Commands"
# tmux select-pane -t "$SESSION_NAME:editor.3" -T "Tests"

# Start processes
tmux send-keys -t "$SESSION_NAME:editor.0" "cd \"$WORK_DIR\" && nvim ." C-m
tmux send-keys -t "$SESSION_NAME:editor.1" "cd \"$WORK_DIR\" && claude" C-m
tmux send-keys -t "$SESSION_NAME:editor.2" "cd \"$WORK_DIR\" && echo 'Command pane - Run builds, git commands, etc.'" C-m
# tmux send-keys -t "$SESSION_NAME:editor.3" "cd \"$WORK_DIR\" && echo 'Test watcher pane - Run your test commands here'" C-m

# Focus Neovim
tmux select-pane -t "$SESSION_NAME:editor.0"

# Attach/switch
if [ -z "${TMUX:-}" ]; then
  tmux attach-session -t "$SESSION_NAME"
else
  tmux switch-client -t "$SESSION_NAME"
fi
