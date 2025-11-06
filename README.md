# GitLab AI Assistant

This project aims to create a robust, file-based system for synchronizing GitLab entities (Issues, Labels, Milestones) and optionally visualizing them, serving as a foundation for an AI assistant.

## Core Components:

1.  **Synchronization System:** A Python script to fetch data from a self-hosted GitLab CE instance via its API and transform it into local Markdown files.
2.  **Visualization System:** An open-source, browser-based tool (e.g., Obsidian) to display the file structure as a user story map.

## Data Structure:

*   **Entities:** Issues, Labels, Milestones.
*   **Target:** Local, directory-based filesystem.
*   **Hierarchy:** Agile methodology-based (Backbone -> Epic -> Story), defined by GitLab's "Related items" feature (Issue Links) to create parent-child relationships between Epics and Stories.
*   **Format:** Markdown files with YAML frontmatter for metadata (iid, status, relationships, etc.).

## Current Status:

The initial synchronization script setup is complete, and the GitLab API connection has been successfully tested.

## Setup & Usage:

Refer to the `scripts/README.md` for instructions on setting up the Python environment and running the synchronization script.

## Documentation:

Detailed documentation can be found in the `docs/` directory.
