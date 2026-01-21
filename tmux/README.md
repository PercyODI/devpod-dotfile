# Tmux Development Workspace

A carefully designed tmux workspace optimized for development with AI assistance, test-driven development, and efficient panel management.

## Quick Start

```bash
# Start the development workspace in current directory
dev

# Start with custom session name
dev my-project

# Start in specific directory
dev my-project /path/to/project
```

After running the command, you'll have a tmux session with:
- **Main pane**: Neovim editor (60% width)
- **Right-top pane**: Claude Code AI assistant (40% width, 60% height)
- **Right-bottom pane**: Test watcher terminal (40% width, 40% height)
- **Bottom pane**: Command/build terminal (full width, 20% height)

## Layout Visualization

```
┌──────────────────────┬─────────────┐
│                      │             │
│                      │   Claude    │
│       Neovim         │   (Pane 1)  │
│     (Pane 0)         ├─────────────┤
│                      │             │
│                      │    Tests    │
│                      │   (Pane 2)  │
├──────────────────────┴─────────────┤
│         Commands/Build              │
│            (Pane 3)                 │
└─────────────────────────────────────┘
```

## Keybindings

All tmux commands require the prefix key first: `Ctrl-a`

### Quick Navigation (No Prefix)

These work immediately without pressing `Ctrl-a` first:

| Key | Action |
|-----|--------|
| `Alt+h` | Move to left pane |
| `Alt+j` | Move to pane below |
| `Alt+k` | Move to pane above |
| `Alt+l` | Move to right pane |

### Direct Pane Selection (With Prefix)

Jump directly to specific panes:

| Key | Action |
|-----|--------|
| `Ctrl-a` `1` | Jump to Neovim |
| `Ctrl-a` `2` | Jump to Claude |
| `Ctrl-a` `3` | Jump to Test watcher |
| `Ctrl-a` `4` | Jump to Command terminal |

### Panel Toggle (With Prefix)

Show/hide panels while preserving their content:

| Key | Action |
|-----|--------|
| `Ctrl-a` `Shift+C` | Toggle Claude panel |
| `Ctrl-a` `Shift+T` | Toggle Test panel |
| `Ctrl-a` `Shift+B` | Toggle Bottom command panel |
| `Ctrl-a` `z` | Zoom/unzoom current pane (built-in) |

### Layout Presets (With Prefix)

Quick layout configurations:

| Key | Action | Layout |
|-----|--------|--------|
| `Ctrl-a` `Shift+R` | Restore default layout | All panes visible |
| `Ctrl-a` `Shift+F` | Focus mode | Nvim + bottom terminal only |
| `Ctrl-a` `Shift+V` | Review mode | Nvim + Claude side-by-side |

### Standard Tmux Operations (With Prefix)

| Key | Action |
|-----|--------|
| `Ctrl-a` `\|` | Split pane vertically |
| `Ctrl-a` `-` | Split pane horizontally |
| `Ctrl-a` `h/j/k/l` | Navigate panes (vim-style) |
| `Ctrl-a` `Shift+H/J/K/L` | Resize panes |
| `Ctrl-a` `r` | Reload tmux config |
| `Ctrl-a` `d` | Detach from session |

## How It Works

### Panel Toggle Mechanism

The toggle keybindings use a smart resize approach:

```bash
# Example: Toggle Claude panel (Ctrl-a + Shift+C)
if pane_width <= 5:
    resize_to_40%    # Show the panel
else:
    resize_to_1      # Hide the panel
```

**Why this approach:**
- **Preserves state**: Your Claude session stays alive with full history
- **Fast**: No process spawning/killing overhead
- **Intuitive**: Single key toggles visibility
- **Flexible**: Works with any pane layout

### Session Management

The `dev-workspace.sh` script:
1. Checks if a session exists; if yes, attaches to it
2. Creates a new detached session with the "editor" window
3. Splits panes in the optimal layout
4. Starts Claude in the right-top pane
5. Starts Neovim in the main pane
6. Adds welcome messages to other panes
7. Attaches to the session

**Smart reattachment:**
- From outside tmux: Attaches to the session
- From inside tmux: Switches to the session (no nesting)

### Directory Handling

```bash
# Panes inherit the starting directory
tmux split-window -c "#{pane_current_path}"
```

This ensures new panes start in your project directory, not your home directory.

## LazyVim Compatibility

This setup is carefully designed to avoid conflicts with LazyVim keybindings:

### No Conflicts Because:

1. **Prefix requirement**: All tmux commands need `Ctrl-a` first
2. **Different scope**: Tmux operates at terminal level, LazyVim at editor level
3. **Capital letters**: Using `C`, `T`, `B`, `R`, `F`, `V` avoids lowercase conflicts
4. **Alt-based navigation**: `Alt+h/j/k/l` works at tmux level, doesn't interfere with vim

### LazyVim Keybindings (Still Work Normally)

| LazyVim Key | Action | Conflict? |
|-------------|--------|-----------|
| `Space` + [key] | Leader commands | ✅ No conflict |
| `Ctrl-w` + [key] | Window navigation | ✅ No conflict |
| `Ctrl-h/j/k/l` | Navigate vim splits | ✅ No conflict |

### When You're In Neovim:
- All LazyVim keybindings work normally
- Tmux keybindings require `Ctrl-a` prefix first
- To switch panes, use `Alt+h/j/k/l` or `Ctrl-a` `1/2/3/4`

### When You're In Claude or Terminal Panes:
- Tmux keybindings work normally
- Use `Ctrl-a` `1` to jump back to Neovim

## Typical Workflows

### Workflow 1: TDD (Test-Driven Development)

1. Start workspace: `dev`
2. In Test pane (`Ctrl-a` `3`): Start test watcher
   ```bash
   npm run test:watch
   # or: pytest --watch
   # or: cargo watch -x test
   ```
3. In Neovim pane (`Ctrl-a` `1`): Write code
4. Tests run automatically in the Test pane
5. If stuck, ask Claude (`Ctrl-a` `2`) for help
6. Toggle test panel when not needed: `Ctrl-a` `Shift+T`

### Workflow 2: Pair Programming with Claude

1. Start workspace: `dev`
2. Enable Review mode: `Ctrl-a` `Shift+V`
3. In Neovim: Work on code
4. In Claude (`Alt+l`): Ask questions, get suggestions
5. Switch back to Neovim (`Alt+h`) to implement
6. Use bottom terminal for git commits: `Ctrl-a` `4`

### Workflow 3: Deep Focus Coding

1. Start workspace: `dev`
2. Enable Focus mode: `Ctrl-a` `Shift+F` (hides Claude and Test panels)
3. Work in Neovim with bottom terminal for commands
4. When stuck, restore layout: `Ctrl-a` `Shift+R`
5. Ask Claude for help, then return to Focus mode

### Workflow 4: Debugging

1. Start workspace: `dev`
2. Zoom Neovim: `Ctrl-a` `z` (full screen)
3. Review code, set breakpoints
4. Unzoom: `Ctrl-a` `z`
5. In bottom terminal: Run debugger
6. In Claude: Ask about error messages
7. In Test pane: Check test output

## Design Decisions

### Why These Percentages?

- **Neovim (60% width)**: Primary workspace, needs most screen space
- **Claude (40% width, 60% height)**: Enough space to read responses comfortably
- **Test (40% width, 40% height)**: Sufficient for test output, not too distracting
- **Bottom (20% height)**: Enough for command output without overwhelming

### Why Four Panes?

This is the sweet spot for development:
- **Neovim**: Core editing
- **Claude**: AI assistance (reduces context switching)
- **Test watcher**: Immediate feedback loop
- **Command terminal**: Git, builds, deployment

More panes = cognitive overload. Fewer panes = too much switching.

### Why Toggle Instead of Kill/Respawn?

**Toggle (resize to 1 pixel):**
- ✅ Preserves process state and history
- ✅ Fast (no process spawning)
- ✅ Can be undone instantly
- ✅ Maintains pane IDs (keybindings still work)

**Kill/respawn:**
- ❌ Loses Claude conversation history
- ❌ Loses test watcher state
- ❌ Slower to restart processes
- ❌ More complex scripting required

### Why Ctrl-a as Prefix?

- `Ctrl-b`: Default tmux prefix, but conflicts with vim "page up"
- `Ctrl-a`: Common alternative, works well with vim users
- Already configured in your tmux.conf
- Easy to reach with left hand while right hand on mouse/trackpad

### Why Alt+h/j/k/l for Quick Navigation?

- No prefix needed = faster
- Vim-style navigation = familiar to nvim users
- Alt is rarely used by terminal applications
- Works even when focused in Neovim (caught by tmux first)

## Advanced Customization

### Change Panel Sizes

Edit `tmux.conf` (tmux/tmux.conf:126) to adjust the restore layout:

```tmux
# Current sizes
bind R select-layout tiled \; \
  resize-pane -t 0 -x 60% \; \
  resize-pane -t 1 -x 40% \; \
  resize-pane -t 2 -y 40% \; \
  resize-pane -t 3 -y 20%
```

Change percentages to your preference, then reload: `Ctrl-a` `r`

### Customize Welcome Messages

Edit `dev-workspace.sh` (tmux/dev-workspace.sh:67) to change the messages in test/command panes:

```bash
tmux send-keys -t "$SESSION_NAME:editor.2" "echo 'Your custom message'" C-m
```

### Auto-start Test Watcher

Edit `dev-workspace.sh` (tmux/dev-workspace.sh:67) to automatically start your test watcher:

```bash
# Instead of echo message, start your test runner
tmux send-keys -t "$SESSION_NAME:editor.2" "npm run test:watch" C-m
```

### Add More Panes

You can add more panes in the script:

```bash
# Add a 5th pane (example)
tmux split-window -h -c "$WORK_DIR" -t "$SESSION_NAME:editor.3"
```

Then add corresponding keybindings in `tmux.conf`.

### Change Keybindings

Edit `tmux.conf` to remap any binding:

```tmux
# Example: Use Ctrl-a + c for Claude instead of C
bind c if-shell \
  "[ $(tmux display-message -p -t 1 '#{pane_width}') -le 5 ]" \
  "resize-pane -t 1 -x 40%" \
  "resize-pane -t 1 -x 1"
```

## Troubleshooting

### Keybindings Not Working

1. Reload tmux config: `Ctrl-a` `r`
2. If that doesn't work, restart tmux session:
   ```bash
   tmux kill-session -t dev
   dev
   ```

### Panes Have Wrong Sizes

Reset to default layout: `Ctrl-a` `Shift+R`

### Claude Not Starting

1. Check Claude is installed: `which claude`
2. Check Claude is in PATH: `echo $PATH | grep .local/bin`
3. Manually start: Jump to Claude pane (`Ctrl-a` `2`) and type `claude`

### Alt+h/j/k/l Not Working in Terminal

Your terminal may not support Alt key properly. Check terminal settings:
- **iTerm2**: Preferences → Profiles → Keys → "Left Option key" = "Esc+"
- **Terminal.app**: Preferences → Profiles → Keyboard → "Use Option as Meta key"
- **Alacritty**: Already works by default

Alternatively, use the prefix version: `Ctrl-a` `h/j/k/l`

### Session Already Exists Error

The script should auto-attach. If it doesn't:
```bash
# List sessions
tmux ls

# Attach to existing session
tmux attach -t dev

# Or kill and recreate
tmux kill-session -t dev
dev
```

## Best Practices

1. **Use Focus Mode** when deep in flow state
2. **Keep Claude panel visible** when learning new concepts
3. **Toggle test panel** during refactoring to reduce noise
4. **Use bottom terminal** for git operations to keep history
5. **Zoom pane** (`Ctrl-a` `z`) when reading long outputs
6. **Create project-specific sessions** with custom names: `dev project-name`
7. **Detach, don't exit**: Use `Ctrl-a` `d` to keep session alive in background

## Files in This Setup

- `tmux.conf`: Main tmux configuration with keybindings
- `dev-workspace.sh`: Session initialization script
- `README.md`: This documentation

## Resources

- [Tmux Cheat Sheet](https://tmuxcheatsheet.com/)
- [LazyVim Documentation](https://www.lazyvim.org/)
- [Claude Code Documentation](https://github.com/anthropics/claude-code)

## Contributing

Feel free to customize this setup for your workflow. Common customizations:
- Adjust panel percentages
- Change keybindings to your preference
- Add auto-start commands for your tools
- Create multiple workspace scripts for different projects
