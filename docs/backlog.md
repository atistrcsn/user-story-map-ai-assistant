# Project Backlog

This document serves as a living backlog for all tasks, features, and implementation plans for the GitLab AI Assistant project.

## Current Phase: GitLab Synchronization Module Development

### Implemented:

*   Project structure (`gitlab_data`, `scripts` directories).
*   Modern Python environment setup (`uv`, `pyproject.toml`).
*   Configuration handling (`config.py`, `.gitignore` entry).
*   Initial `sync_gitlab.py` script with GitLab API connection and basic data fetching (issues, labels, milestones).
*   Added issue type to Markdown frontmatter.
### Next Steps (Planned):

*   **Implement File Generation Logic:**
    *   Define agile hierarchy mapping (Backbone, Epic, Story, Task) based on GitLab labels.
    *   Implement functions for generating file paths and filenames for issues.
    *   Implement functions for generating Markdown content with YAML frontmatter for issues.
    *   Integrate file writing logic into the `main` function.
    *   Add optional `gitlab_data` directory cleanup before sync.
*   **Handle Unassigned Issues:** Place issues without hierarchy labels into a dedicated `_unassigned` directory.

## Future Features / Enhancements:

*   **Visualization Setup (Obsidian):** Provide instructions and basic vault structure for visualizing synchronized data.
*   **Initial Visualization Guidance:** Offer guidance on creating user story maps in Obsidian Canvas.
*   **Incremental Synchronization:** Only update changed issues to improve performance.
*   **More Sophisticated Label Mapping:** Allow for more flexible and configurable mapping of GitLab labels to hierarchy levels.
*   **Support for Other GitLab Entities:** Extend synchronization to include Merge Requests, Snippets, etc.
*   **Error Reporting & Logging:** Implement robust error handling and logging mechanisms.
*   **Command-Line Arguments:** Allow configuration parameters to be passed via CLI arguments.
*   **Testing Strategy Implementation:** Implement a testing strategy for the existing codebase, focusing on critical components.
