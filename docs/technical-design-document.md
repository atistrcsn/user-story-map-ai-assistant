# Technical Design Document (TDD)

## 1. Introduction

This document details the implementation plan for the GitLab Synchronization Module, outlining the technical choices and step-by-step execution.

## 2. Technology Stack

*   **Language:** Python 3.x
*   **GitLab API Client:** `python-gitlab` library
*   **Dependency Management:** `uv` with `pyproject.toml`
*   **Configuration:** Python module (`config.py`) for sensitive data.
*   **Output Format:** Markdown files with YAML frontmatter.

## 3. Module Design: `sync_gitlab.py`

### 3.1. Configuration Loading

*   The script will import `config.py` to access `GITLAB_URL`, `PRIVATE_TOKEN`, and `PROJECT_PATH`.

### 3.2. GitLab API Connection

*   Utilize `gitlab.Gitlab(url, private_token)` to establish a connection.
*   Perform `gl.auth()` to verify credentials.

### 3.3. Project Retrieval

*   Use `gl.projects.get(config.PROJECT_PATH)` to retrieve the target GitLab project object.

### 3.4. Data Fetching

*   Fetch all issues: `project.issues.list(all=True)`.
*   Fetch all labels: `project.labels.list(all=True)`.
*   Fetch all milestones: `project.milestones.list(all=True)`.

### 3.5. Agile Hierarchy Mapping

*   A dictionary or similar structure will map specific GitLab labels (e.g., "Backbone", "Epic", "Story", "Task") to their corresponding directory names and hierarchical levels.

### 3.6. File Path Generation

*   A function will determine the output file path for each issue based on its assigned labels and the defined hierarchy.
*   Example: An issue with labels "Backbone: Feature A", "Epic: Sub-feature B", "Story: User Story C" might map to `gitlab_data/backbones/feature-a/epics/sub-feature-b/stories/user-story-c.md`.

### 3.7. Markdown Content Generation

*   A function will construct the YAML frontmatter for each issue, including fields like:
    *   `id`: GitLab Issue IID
    *   `title`: Issue Title
    *   `type`: GitLab Issue Type (e.g., 'issue', 'task')
    *   `state`: Issue State (opened, closed)
    *   `labels`: List of assigned labels
    *   `milestone`: Milestone title (if any)
    *   `assignee`: Assignee username (if any)
    *   `due_date`: Due date (if any)
    *   `created_at`: Creation timestamp
    *   `updated_at`: Last update timestamp
    *   `web_url`: Link to the GitLab issue
*   The issue description will follow the YAML frontmatter.

### 3.8. File Writing

*   The script will iterate through all fetched issues.
*   For each issue, it will generate the file path and Markdown content.
*   It will ensure that the target directories exist (using `os.makedirs(..., exist_ok=True)`).
*   It will write the content to the determined file path.

### 3.9. `gitlab_data` Directory Cleanup

*   Before starting the synchronization, the script will optionally clear the contents of the `gitlab_data` directory to ensure a clean sync.

## 4. Error Handling

*   Implement `try-except` blocks for API calls and file operations.
*   Provide informative error messages to the console.

## 5. Future Considerations

*   Incremental synchronization (only update changed issues).
*   More sophisticated label-to-hierarchy mapping.
*   Support for other GitLab entities (e.g., Merge Requests).
