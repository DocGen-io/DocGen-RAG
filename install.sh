#!/usr/bin/env bash

# DocGen-RAG CLI Installation
# Installs the professional CLI tool with all required dependencies.

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

echo "DocGen-RAG CLI Installation"
echo "==========================="
echo ""

# -- Prerequisites ------------------------------------------------------------

if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH."
    echo "Install it from: https://docs.docker.com/get-docker/"
    exit 1
fi
echo "Docker: available"

if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "uv installed. You may need to restart your terminal."
fi
echo "uv: available"

# -- Install CLI dependencies ------------------------------------------------

echo ""
echo "Installing CLI dependencies..."
cd "$SCRIPT_DIR"
uv pip install -e ".[cli]"

echo ""
echo "Installation complete."
echo ""
echo "Usage:"
echo "  docgen init                   First-time setup"
echo "  docgen reboard                Reset config and setup again"
echo "  docgen run <git-url>          Generate documentation"
echo "  docgen config show            View configuration"
echo "  docgen provider list          List available providers"
echo "  docgen credentials check      Verify stored credentials"
echo ""
echo "Run 'docgen --help' for more options."

# -- Auto-run init if first time ----------------------------------------------

CONFIG_DIR="$HOME/.config/docgen"

if [ "$1" == "--reboard" ]; then
    echo ""
    echo "Reboarding requested..."
    echo ""
    uv run docgen reboard
elif [ ! -f "$CONFIG_DIR/settings.toml" ]; then
    echo ""
    echo "First-time setup detected. Running 'docgen init'..."
    echo ""
    uv run docgen init
else
    echo ""
    echo "DocGen is already configured. Run 'docgen reboard' or './install.sh --reboard' to run setup again."
fi
