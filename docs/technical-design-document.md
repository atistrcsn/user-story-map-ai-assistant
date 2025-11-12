# Technical Design Document: Gemini GitLab Workflow

This document describes the detailed technical plan for the intelligent context management system designed to support GitLab-based development workflows. The plan is based on proposals and refinements made during the initial brainstorming phase.

## I. System Architecture

The system is designed as a command-line interface (CLI) tool (`ggw`) that interacts with GitLab and a Gemini AI model. The architecture is based on a service layer that separates concerns, ensuring modularity and testability.

### A. Core Principles

*   **Two-Phase AI Analysis:** Instead of passing the entire context to the main LLM at once, a smaller, faster model is used to filter for relevant information. This model receives the user request and a list of all documents/issues in the project (with titles and short summaries), and returns a list of the 10-15 most relevant files.
*   **Local First:** All changes are first generated and saved locally. This allows the user to review the plan before it is pushed to GitLab.
*   **Smart Sync:** To minimize wait times, the system avoids full synchronization whenever possible.
    *   **Implementation:** When the command is run, the system only requests the `updated_at` timestamps of the issues from the GitLab API, compares them to the state stored in `/.gemini_cache/`, and only re-downloads the full content of the issues that have changed. This ensures that the context is up-to-date with minimal delay.

### B. Data Model

*   **Local Representation:** GitLab issues are stored as Markdown files in the `gitlab_data/` directory. The directory structure mirrors the Epic-Story hierarchy.
*   **Project Map:** A `project_map.yaml` file serves as a centralized graph of the project, defining the nodes (issues) and links (dependencies, parent-child relationships).

### C. Components

*   **CLI (`cli.py`):** The user interface, built with `Typer`. It handles command parsing and orchestrates calls to the service layer.
    *   `gemini-cli sync`: Performs a "Smart Sync" to update the local data from GitLab.
    *   `gemini-cli create feature`: Initiates an interactive workflow to plan a new feature. The command follows the optimized "Enhanced Workflow": 1. Smart Sync. 2. User input. 3. Two-phase AI analysis. 4. Structured, step-by-step dialogue for approval. 5. Local file generation.
    *   `gemini-cli upload story-map`: Pushes the locally generated changes to GitLab. During this step, the tool reads the generated `.md` files to get the issue descriptions, ensuring the full content is uploaded.
*   **GitLab Service (`gitlab_service.py`):** Encapsulates all communication with the GitLab API.
*   **AI Service (`ai_service.py`):** Manages all interactions with the Gemini AI model, including prompt construction and response parsing.
*   **Configuration (`config.py`):** Centralized management of paths, API keys, and other settings.

## II. Detailed Workflow: `create feature`

1.  **Trigger:** The user runs `ggw create feature "New feature description"`.
2.  **Smart Sync:** The tool automatically runs a `smart_sync` to ensure the local context is up-to-date.
3.  **Phase 1: Pre-filtering:**
    *   The tool gathers all potential context sources (docs, existing issues).
    *   It calls the `ai_service` with the user's request and the list of sources.
    *   The AI returns a list of the most relevant file paths.
4.  **Phase 2: Deep Analysis:**
    *   The tool reads the content of the relevant files.
    *   It calls the `ai_service` again with the user's request and the filtered content.
    *   The AI returns a structured implementation plan (e.g., in JSON format).
5.  **User Confirmation:**
    *   The tool presents the plan to the user for approval in a structured, step-by-step manner.
6.  **Local Generation:**
    *   Upon approval, the tool creates the new Markdown files and updates the `project_map.yaml`.
7.  **Upload:**
    *   The user runs `ggw upload` to push the changes to GitLab.
    *   **Implementation Note on Board Ordering:** It was discovered that the GitLab board UI displays items in a visually inverted order compared to the API's list order. Therefore, to place a new story *under* its parent epic on the board, the `gitlab_uploader` uses the `move_before_id` parameter in the API call, positioning the story *before* the epic in the list, which results in the correct visual hierarchy.

## III. Testing Strategy

*   **Unit Tests:** Each module (`gitlab_service`, `ai_service`, etc.) will have comprehensive unit tests. The GitLab API and AI model will be mocked to ensure fast and reliable tests.
*   **Integration Tests:** Tests will be created to verify the interaction between the different components of the system.
*   **End-to-End Tests:** Manual or scripted tests will be performed to verify the entire workflow, from `sync` to `upload`.

### Test Cases for `project_map.yaml`

*   Verification of the generated `nodes` and `links` content based on a predefined mock GitLab dataset.
*   Testing of edge cases, such as issues with no dependencies or complex, multi-level hierarchies.
*   Ensuring that the local file paths in the map are generated correctly.
