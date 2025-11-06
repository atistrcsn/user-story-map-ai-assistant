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

## Current Phase: AI-Assisted Feature Implementation

### Implemented:

*   **Core Project Structure:** (`gitlab_data`, `scripts` directories).
*   **Modern Python Environment:** (`uv`, `pyproject.toml`, `pytest`).
*   **Initial GitLab Sync Script:** (`sync_gitlab.py`) for basic data fetching.
*   **`gemini-cli` Command-Line Tool:** Initial version created with `typer`.
*   **Refactored Service Layer (`gitlab_service.py`):**
    *   `smart_sync`: Intelligens, időbélyeg alapú szinkronizáció a GitLab-bel.
    *   `build_project_map`: Függőségi gráfot és projekt térképet épít az issue-kból.
    *   Tiszta, tesztelhető logika, leválasztva a CLI rétegről.
*   **Comprehensive Test Coverage:** Unit tesztek a CLI és a service rétegre is (`test_gemini_cli.py`, `test_gitlab_service.py`).

### Next Steps (Planned):

*   **AI Integration (Pre-filtering):** Implement the first phase of AI analysis within the `create feature` command to identify relevant context files.
*   **AI Integration (Deep Analysis):** Implement the second phase to generate a structured plan based on the filtered context.
*   **Structured Dialogue:** Create the interactive user confirmation workflow.
*   **Local Generation & GitLab Upload:** Implement the final steps to create artifacts locally and upload them to GitLab.

## Implement Robust GitLab Upload Functionality

**Status:** PENDING

**Description:** Refactor and properly implement the `upload_artifacts_to_gitlab` function in `gitlab_service.py` using a test-driven approach to ensure correctness and reliability.

**Implementation Plan:**

1.  **Test-Driven Development (TDD):**
    *   In `scripts/tests/test_gitlab_service.py`, write a comprehensive test case `test_upload_artifacts_to_gitlab` using `unittest.mock` to simulate the GitLab API.
    *   The test must verify the correct order of operations: Labels -> Issues -> Dependency Comments.
    *   The test must assert that the correct data (titles, labels, comment text) is passed to the mocked API calls.

2.  **Refactor `upload_artifacts_to_gitlab`:**
    *   **Step 1: Handle Labels:** First, collect all unique labels from the input nodes, check which ones already exist on the project, and create the missing ones.
    *   **Step 2: Create Issues:** Create each issue, passing the now-guaranteed-to-exist labels. Store a mapping of temporary IDs (e.g., `NEW_1`) to the real GitLab IIDs.
    *   **Step 3: Create Dependency Comments:** Read the `links` from `project_map.yaml`. Use the ID map to find the real IIDs and post the correctly formatted `/blocks` or `/blocked by` comments to the appropriate issues.

3.  **Verification:**
    *   Run the test suite to ensure the implementation passes.
    *   Only after the test passes, update the status of the main feature in `docs/feature-ai-story-map-creation.md` to `[KÉSZ]`.

## Implement AI Integration (Pre-filtering)

**Status:** PENDING

**Description:** Implement the first phase of the two-phase AI analysis. This involves creating a mechanism that uses a fast AI model to intelligently select the most relevant context files (documentation and existing issues) based on a user's high-level feature request.

**Implementation Plan:**

1.  **New AI Module (`ai_service.py`):**
    *   Create `scripts/ai_service.py` to encapsulate all AI model interactions, keeping the codebase modular.
    *   Define a function `get_relevant_context_files(user_prompt: str, context_sources: list[dict])` within this module. This function will be responsible for building the prompt, calling the AI API, and parsing the response to extract the list of relevant file paths.

2.  **Test-Driven Development (`test_ai_service.py`):**
    *   Create the test file `scripts/tests/test_ai_service.py`.
    *   Write a test case `test_get_relevant_context_files` that uses `@patch` to mock the actual AI API call.
    *   The test will verify that the function constructs the correct prompt and correctly parses a simulated JSON response from the mock API.

3.  **Context Aggregation (`gemini_cli.py`):**
    *   In `gemini_cli.py`, within the `create_feature` command, implement helper functions to gather all potential context sources:
        *   One function to parse `project_map.yaml` and extract the `local_path` and `title` for all existing issues.
        *   Another function to recursively find all `.md` files in the `docs/` directory.
    *   These lists will be combined to form the `context_sources` input for the AI service.

4.  **AI Service Implementation (`ai_service.py`):**
    *   Implement the `get_relevant_context_files` function.
    *   It will dynamically construct a detailed prompt containing the user's request and the list of available context files with their summaries/titles.
    *   The prompt will instruct the AI to return a JSON list of the most relevant file paths.
    *   The function will call the AI model (initially mocked for testing) and parse the JSON response into a Python list.

5.  **CLI Integration:**
    *   Integrate the call to `ai_service.get_relevant_context_files` into the `create_feature` command in `gemini_cli.py`.
    *   For this initial implementation, the command will simply print the returned list of relevant files to the console for verification.

6.  **Documentation:**
    *   Update all relevant project documents (`backlog.md`, `feature-ai-story-map-creation.md`, `architecture-design-document.md`) to reflect the new module and the implementation's progress.

## Future Features / Enhancements:
