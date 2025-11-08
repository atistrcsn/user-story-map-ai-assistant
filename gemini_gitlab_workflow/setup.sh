#!/bin/bash
#
# Setup script for the Gemini GitLab Workflow package.
# This script installs the package, creates the default configuration,
# and registers the custom tools with the Gemini CLI.
#

set -e # Exit immediately if a command exits with a non-zero status.

echo "--- Starting Gemini GitLab Workflow Setup ---"

# 1. Install the Python package
echo "[1/4] Installing the 'gemini-gitlab-workflow' package..."
uv pip install .
echo "✓ Package installed successfully."

# 2. Create the global configuration directory
CONFIG_DIR="$HOME/.config/gemini_workflows"
echo "[2/4] Checking for global configuration directory at $CONFIG_DIR..."
mkdir -p "$CONFIG_DIR"
echo "✓ Configuration directory is present."

# 3. Create a default global config file if it doesn't exist
CONFIG_FILE="$CONFIG_DIR/config.yaml"
echo "[3/4] Checking for global configuration file at $CONFIG_FILE..."
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Configuration file not found. Creating a default one."
    # Use a here-document to write the default config
    cat > "$CONFIG_FILE" << EOL
# --- Global Configuration for Gemini Workflows ---

# GitLab API settings
gitlab:
  api_url: "https://gitlab.com"
  
  # IMPORTANT: Add your GitLab Personal Access Token here.
  # This token requires 'api' scope.
  private_token: "YOUR_GITLAB_PRIVATE_TOKEN_HERE"

EOL
    echo "✓ Default global config created. Please edit it to add your private token."
else
    echo "✓ Global config file already exists."
fi

# 4. Register the custom tools with Gemini CLI
GEMINI_TOOLS_DIR="$HOME/.gemini/custom_tools"
echo "[4/4] Registering custom tools with Gemini CLI..."
mkdir -p "$GEMINI_TOOLS_DIR"
cp gemini_tools.py "$GEMINI_TOOLS_DIR/gitlab_workflow_tools.py"
echo "✓ Custom tools registered successfully."

echo ""
echo "--- Setup Complete! ---"
echo "IMPORTANT: Please edit the global configuration file at $CONFIG_FILE and add your GitLab private token."
echo "After that, create a '.gemini-workflow.yaml' file in your project's root directory to specify the project_id."
echo "You can now use the 'create_feature_story_map' and 'upload_story_map_to_gitlab' tools in the Gemini CLI."
