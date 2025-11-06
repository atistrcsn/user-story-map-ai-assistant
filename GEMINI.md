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

## GitLab Community Edition Limitations

**Attention:** This project uses the GitLab Community Edition (CE). This version does **not** support native issue dependencies (e.g., `blocked by`, `blocking`).

Therefore, the project follows a custom convention for managing dependencies:

1.  **Dependency Declaration:** Dependencies must be declared exclusively in **comments** using the format `/blocked by #<iid>` or `/blocking #<iid>`.
2.  **Parsing Logic:** The system must parse issue **comments** to build the dependency graph, not the issue description.

**All code handling GitLab issues must strictly adhere to this convention.**

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
