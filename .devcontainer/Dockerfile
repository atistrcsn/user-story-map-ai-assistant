# Use the official Go image as our foundation.
FROM mcr.microsoft.com/devcontainers/python:2-3.12-bookworm

# Set environment variables to prevent interactive prompts during package installations.
ENV DEBIAN_FRONTEND=noninteractive

# Install additional, project-specific system-level dependencies.
# RUN apt-get update && apt-get install -y \\
#     && apt-get clean \\
#     && rm -rf /var/lib/apt/lists/*

# The container will run as root, as specified in devcontainer.json.
# All subsequent commands will be run in the context of the workspace directory.
WORKDIR /workspaces

# This is the command that keeps the container running, allowing VS Code to attach.
CMD ["sleep", "infinity"]