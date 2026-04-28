#!/usr/bin/env bash

# DocGen-RAG Installation Script
set -e

echo "Starting DocGen-RAG CLI Installation..."

if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH."
    echo "Please install Docker Desktop or Docker Engine first."
    exit 1
fi

echo "Docker is installed."

if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "uv installed successfully. You may need to restart your terminal or source your profile later."
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
CLI_SCRIPT="$SCRIPT_DIR/scripts/docgen_cli.py"

if [ ! -f "$CLI_SCRIPT" ]; then
    echo "Error: Could not find $CLI_SCRIPT. Please run this script directly from the docgen-rag folder."
    exit 1
fi

chmod +x "$CLI_SCRIPT"

TARGET_DIR="$HOME/.local/bin"
mkdir -p "$TARGET_DIR"

if ln -sf "$CLI_SCRIPT" "$TARGET_DIR/docgen"; then
    echo "Successfully linked 'docgen' CLI to $TARGET_DIR/docgen"
else
    echo "Error: Failed to link the script to $TARGET_DIR."
    exit 1
fi

echo ""
echo "Installation complete!"
echo "Make sure $TARGET_DIR is in your PATH."
echo "You can now run 'docgen' from anywhere in your terminal."
