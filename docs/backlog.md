# Project Backlog

This document serves as a living backlog for all tasks, features, and implementation plans for the GitLab AI Assistant project.

## Feature: AI-Assisted Story Map Creation

This feature enables a user to provide a high-level idea and have the AI assistant analyze the project context, propose a breakdown into epics and stories, identify dependencies, and finally, create the new issues in GitLab.

### Enhanced End-to-End Workflow (Optimized Plan)

1.  **Smart Sync (Prerequisite):** Instead of a full sync, the process starts with a 'smart sync'. It fetches only `updated_at` timestamps from GitLab, compares them to a local cache, and downloads the full content only for issues that have changed. This ensures a fast startup.

2.  **User Input:** The user provides a high-level concept or feature requirement.

3.  **Two-Phase AI Analysis (Context-Aware):** To manage large contexts, the analysis is split into two phases:
    *   **3.1. Pre-filtering:** A small, fast LLM receives the user's request and a list of all documents/issues (with summaries). It returns a list of the top 10-15 most relevant files.
    *   **3.2. Deep Analysis:** The main, powerful LLM performs the detailed analysis using only this pre-filtered, highly relevant context.

4.  **Structured Dialogue (User Confirmation):** The AI engages in a step-by-step confirmation process, asking for approval at each logical stage (e.g., after task decomposition, after placement, after dependency suggestion) to ensure clarity and user control.

5.  **Local Generation:** Based on the final approval, the AI performs the local changes:
    *   Creates new `.md` files in the `gitlab_data` directory.
    *   Updates the `project_map.yaml` with new nodes and links.

6.  **Robust Upload to GitLab:** The system propagates changes back to GitLab using a transactional and safe approach:
    *   **6.1. Throttling:** A small delay is introduced between API calls to avoid rate-limiting.
    *   **6.2. Transactional Logic:** The process logs its intended actions. If any step fails (e.g., an issue creation fails), it attempts to roll back the changes already made (e.g., delete previously created issues) to leave GitLab in a clean state, or provides a clear report of the partial success for manual cleanup.
    *   **6.3. Ordered Execution:** The upload proceeds in a strict order: Sync Labels -> Create Issues -> Create Dependency Comments.

---

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
