#!/bin/bash

set -e

# Define the project root (where pyproject.toml is located)
PROJECT_ROOT="$(dirname "$(realpath "$0")")"

echo "Installing gemini-gitlab-workflow in editable mode..."
uv pip install -e "$PROJECT_ROOT"

echo "Copying gemini_tools.py for Gemini CLI integration..."
mkdir -p ~/.gemini/custom_tools
cp "$PROJECT_ROOT/src/gemini_gitlab_workflow/gemini_tools.py" ~/.gemini/custom_tools/

echo "Setup complete."
echo "The 'ggw' command is now installed."
echo "Navigate to your project directory and run 'ggw init' to get started."
