# Project-Specific Gemini Rules

This document outlines specific guidelines and conventions for the Gemini agent within this project.

## Git Commit Message Conventions

All commit messages should adhere to the [Conventional Commits specification](https://www.conventionalcommits.org/en/v1.0.0/).

### Format:

```
<type>(<scope>): <subject>

[body]

[footer]
```

### Type:

Must be one of the following:

*   **feat**: A new feature
*   **fix**: A bug fix
*   **docs**: Documentation only changes
*   **style**: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc.)
*   **refactor**: A code change that neither fixes a bug nor adds a feature
*   **perf**: A code change that improves performance
*   **test**: Adding missing tests or correcting existing tests
*   **build**: Changes that affect the build system or external dependencies (example scopes: gulp, broccoli, npm)
*   **ci**: Changes to our CI configuration files and scripts (example scopes: Travis, Circle, BrowserStack, SauceLabs)
*   **chore**: Other changes that don't modify src or test files
*   **revert**: Reverts a previous commit

### Scope:

Optional, but recommended. Describes the part of the codebase affected by the change (e.g., `gitlab-sync`, `docs`, `tests`, `config`).

### Subject:

A very short, concise description of the change:

*   Use the imperative, present tense: "change" not "changed" nor "changes"
*   Don't capitalize the first letter
*   No period (.) at the end

### Body:

Optional. Provides additional contextual information about the code changes.

*   Use the imperative, present tense: "change" not "changed" nor "changes"
*   Explain *why* the change was made, not *how*.

### Footer:

Optional. Can contain information about breaking changes or reference issues by their ID.

*   `BREAKING CHANGE:`: Indicates a breaking API change.
*   `Closes #<issue-number>`: References an issue that the commit closes.

## Documentation Language

All documentation within this `GEMINI.md` file must be written in English to ensure clarity and consistency for all contributors and AI agents.

## Issue Hierarchy Management

**Authoritative Source of Hierarchy:** The parent-child relationship between Epics and Stories is managed exclusively through GitLab's **"Related items"** feature (known as **Issue Links** in the API).

-   **Epic-Story Relationship:** A `Type::Story` issue is considered a child of a `Type::Epic` issue if, and only if, a `relates_to` link exists between them in GitLab.
-   **Synchronization Logic:** The synchronization script (`gitlab_service.py`) employs a multi-pass strategy to build the local file hierarchy:
    1.  It first processes all `Type::Epic` issues, creating their corresponding directories.
    2.  It then processes all `Type::Story` issues. For each story, it queries the GitLab API for its issue links.
    3.  If a link to a `Type::Epic` issue is found, the story's Markdown file is placed inside that Epic's directory.
-   **No More `Epic::` Labels:** The legacy convention of using `Epic::<name>` labels to define hierarchy is now **deprecated and must not be used**. All hierarchy is derived from issue links.

## File and Directory Structure Convention

To maintain a clean and portable project structure, all generated files and directories (artifacts, caches, data files) **MUST** be located in the **project root**. The project root is defined as the **current working directory** from which the `ggw` command is executed. This ensures that the tool always operates within the context of the user's target project.

This convention is enforced by using `pathlib.Path.cwd()` to dynamically identify the project root at runtime.

- **Project Root:** The current working directory (e.g., `/home/user/my-gitlab-project/`)
- **Generated Data:** `[Project Root]/gitlab_data/`
- **Generated Cache:** `[Project Root]/.gemini_cache/`
- **Generated Map:** `[Project Root]/project_map.yaml`

All scripts that create or read these files must adhere to this principle to ensure they work correctly regardless of the execution directory.

## Holistic Implementation Mandate

To ensure all implementation work is strictly aligned with both a pre-approved plan and the project's high-level goals, you MUST follow this protocol before using any file-modifying tools.

You are **FORBIDDEN** from starting implementation until you have completed and confirmed the following steps in order:

1.  **Acknowledge the Mandate:** Verbally confirm that you are initiating the Holistic Implementation Mandate.

2.  **Identify the Primary Plan:** Ask the user to provide the **exact, absolute path** to the primary feature specification document (e.g., `/workspaces/docs/feature-ai-story-map-creation.md`).

3.  **Load the Primary Plan:** Use the `read_file` tool to load the content of the primary plan document.

4.  **Perform Context Enrichment:**
    *   Analyze the content of the loaded **Primary Plan**.
    *   Based on this analysis, identify the 3-5 most relevant high-level documents from the `/docs` directory that provide architectural and requirement context (e.g., `architecture-design-document.md`, `product-requirements-document.md`).
    *   Verbally confirm with the user which supporting documents you have identified as most relevant.

5.  **Load the Full Context:** Use the `read_many_files` tool to load the **Primary Plan** AND the identified supporting documents from the `/docs` directory into your active context in a single operation.

6.  **Confirm and Commit:** State that you have successfully loaded the full context (the primary plan and its supporting documents). Confirm that all subsequent implementation steps will be guided by this **complete, holistic context**.

7.  **Track and Update Progress:** After successfully implementing a significant part of the plan, you MUST update the Primary Plan document to reflect the new status (e.g., by adding `[DONE]` or `Status: Implemented` markers to the relevant sections). This ensures the plan document is a living artifact that tracks real-world progress.

## Known Issues and Best Practices

### f-string Syntax in Prompts

*   **Issue:** A `ValueError: Invalid format specifier` can occur in Python scripts (like `ai_service.py`) when generating prompts using f-strings.
*   **Cause:** This error happens if the prompt template contains literal curly braces (`{` or `}`) that are intended for the final text (e.g., in a JSON example). The Python f-string parser incorrectly interprets these single braces as placeholders for variables.
*   **Solution:** All literal curly braces within an f-string **must** be escaped by doubling them. For example, a JSON example like `{"key": "value"}` must be written as `{{"key": "value"}}` inside an f-string. This is a mandatory best practice for prompt engineering within this project's Python code.

### Dependency Management with `uv`

To ensure consistent and efficient dependency management across the project, `uv` is the mandated tool. Always adhere to the following commands:

*   **Adding a dependency:** Use `uv add <package_name>` (e.g., `uv add requests`). For development dependencies, use `uv add --dev <package_name>` (e.g., `uv add --dev pytest-cov`).
*   **Removing a dependency:** Use `uv remove <package_name>` (e.g., `uv remove requests`). For development dependencies, use `uv remove --dev <package_name>`.
*   **Running commands within the virtual environment:** Always prefix your commands with `uv run` (e.g., `uv run your_script.py`, `uv run pytest`). This ensures that the command is executed within the project's isolated `uv` virtual environment, using the correct Python interpreter and installed packages.
### Running test with coverage:** `uv run pytest --cov=scripts scripts/tests/`

## Backlog (`docs/backlog.md`) Conventions

To maintain clarity and consistency in project planning, all entries added to `docs/backlog.md` must adhere to the following rules:

1.  **Language:** All entries must be written in **English**.
2.  **Structure:** Every new feature or task must have the following sections:
    *   **Status:** The current state of the item (e.g., `[PLANNED]`, `[IN PROGRESS]`, `[DONE]`)
    *   **Description:** A brief, clear explanation of the task or feature.
    *   **Implementation Plan:** A high-level, step-by-step plan of how the feature will be implemented.
    *   **Testing Ideas:** A few bullet points outlining how the implementation will be verified (e.g., unit tests for specific functions, integration test scenarios).