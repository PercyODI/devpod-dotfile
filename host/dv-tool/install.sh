#!/usr/bin/env bash

set -e

echo "Installing dv (Python version)..."

# Check for Python 3.9+
if ! command -v python3 &>/dev/null; then
    echo "Error: Python 3 is required but not found."
    exit 1
fi

python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.9+ required (found $python_version)"
    exit 1
fi

# Install using pip
echo "Installing with pip..."
python3 -m pip install --user --upgrade .

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "⚠️  Warning: ~/.local/bin is not in your PATH"
    echo ""
    echo "Add this to your ~/.bashrc or ~/.zshrc:"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
    echo ""
fi

# Check installation
if command -v dv &>/dev/null; then
    echo ""
    echo "✅ Installation successful!"
    echo ""
    dv --version
    echo ""
    echo "Get started:"
    echo "  dv --help"
    echo "  dv clone git@github.com:user/repo.git"
    echo "  dv up"
else
    echo ""
    echo "❌ Installation completed but 'dv' command not found."
    echo ""
    echo "Try:"
    echo "  1. Add ~/.local/bin to your PATH"
    echo "  2. Run: hash -r"
    echo "  3. Open a new terminal"
fi

# Offer to copy example config
echo ""
read -p "Copy example config to ~/.config/dv/config.yml? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    mkdir -p ~/.config/dv
    cp example-config.yml ~/.config/dv/config.yml
    echo "✅ Config copied to ~/.config/dv/config.yml"
    echo "   Edit this file to customize your settings."
fi
