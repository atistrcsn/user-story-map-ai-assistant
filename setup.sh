#!/bin/bash

set -e

# Define the project root (where pyproject.toml is located)
PROJECT_ROOT="$(dirname "$(realpath "$0")")"

echo "Installing gemini-gitlab-workflow in editable mode..."
uv pip install -e "$PROJECT_ROOT"

echo "Creating global configuration directory..."
mkdir -p ~/.config/gemini_workflows

echo "Creating template configuration file..."
cat << EOF > ~/.config/gemini_workflows/config.yaml
# GitLab API Configuration
gitlab_url: "https://gitlab.com"
private_token: "your_private_token_here"
project_id: "your_project_id_here"
EOF

echo "Copying gemini_tools.py for Gemini CLI integration..."
mkdir -p ~/.gemini/custom_tools
cp "$PROJECT_ROOT/src/gemini_gitlab_workflow/gemini_tools.py" ~/.gemini/custom_tools/

echo "Setup complete. Please edit ~/.config/gemini_workflows/config.yaml with your GitLab details."
echo "You can now use the 'ggw' command and the Gemini CLI tools."
