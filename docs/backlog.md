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
*   **Implement Project Map Generation:**
    *   Parse issue descriptions for `/blocked by #<IID>` and `/blocking #<IID>` patterns.
    *   Use `networkx` to build a dependency graph.
    *   Save the graph in `node-link` format to `project_map.yaml`.
*   **Handle Unassigned Issues:** Place issues without hierarchy labels into a dedicated `_unassigned` directory.

## Current Development

*   **Testing Strategy Implementation:** In progress. Test environment set up, initial unit tests for `_slugify`, `_generate_markdown_content`, and `_get_issue_filepath` implemented and passing. Label parsing logic for Epic and Story issues clarified and implemented.

## Future Features / Enhancements:
