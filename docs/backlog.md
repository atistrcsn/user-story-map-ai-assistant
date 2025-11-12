# Project Backlog

This document serves as a living backlog for all tasks, features, and implementation plans for the GitLab AI Assistant project.

## Feature: AI-Assisted Story Map Creation

This feature enables a user to provide a high-level idea and have the AI assistant analyze the project context, propose a breakdown into epics and stories, identify dependencies (like blocking relationships), and finally, create the new issues in GitLab.

### Enhanced End-to-End Workflow (Optimized Plan)

1.  **Smart Sync (Prerequisite):** Instead of a full sync, the process starts with a 'smart sync'. It fetches only `updated_at` timestamps from GitLab, compares them to a local cache, and downloads the full content only for issues that have changed. This ensures a fast startup.

2.  **User Input:** The user provides a high-level concept or feature requirement.

3.  **Two-Phase AI Analysis (Context-Aware):** To manage large contexts, the analysis is split into two phases:
    *   **3.1. Pre-filtering:** A small, fast LLM receives the user's request and a list of all documents/issues (with summaries). It returns a list of the top 10-15 most relevant files.
    *   **3.2. Deep Analysis:** The main, powerful LLM performs the detailed analysis using only this pre-filtered, highly relevant context.

4.  **Structured Dialogue (User Confirmation):** The AI engages in a step-by-step confirmation process, asking for approval at each logical stage (e.g., after the issue breakdown, after placement, after dependency suggestion) to ensure clarity and user control.

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
    *   `smart_sync`: Intelligent, timestamp-based synchronization with GitLab.
    *   `build_project_map`: Builds a dependency graph and project map from issues.
    *   Clean, testable logic, decoupled from the CLI layer.
*   **Comprehensive Test Coverage:** Unit tesztek a CLI és a service rétegre is (`test_gemini_cli.py`, `test_gitlab_service.py`).
*   **Implement Upload of AI-generated Issues to GitLab (Implementation and Testing):** AI-generated and user-approved issues (including labels and issue links for hierarchy) are uploaded to GitLab using a separate `gemini-cli upload story-map` command, after the `create-feature` command has locally generated the story map. This includes calling the `gitlab_service.upload_artifacts_to_gitlab` function with the generated `project_map` data, and automated tests.

*   **Correct handling of dependency chains:** Fixed a bug where the `create-feature` command by generated `project_map.yaml` did not contain the correct `contains` type links between newly created epics and stories. The system now correctly builds hierarchical links in `project_map.yaml`, ensuring parent-child relationships between agile elements.

### Next Steps (Planned):

*   **AI Integration (Pre-filtering):** Implement the first phase of AI analysis within the `create feature` command to identify relevant context files.
*   **AI Integration (Deep Analysis):** Implement the second phase to generate a structured plan based on the filtered context.
*   **Structured Dialogue:** Create the interactive user confirmation workflow.

## Implement Robust GitLab Upload Functionality

**Status:** [DONE]

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

**Status:** [DONE]

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

## Implement AI Integration (Deep Analysis)

**Status:** DONE

**Description:** Implement the second phase of the AI analysis. This involves using a powerful AI model to analyze the content of the pre-filtered, relevant files and generate a structured implementation plan in JSON format. This plan will define the new epics, stories, and their relationships.

**Implementation Plan:**

1.  **Test-Driven Development (`test_ai_service.py`):**
    *   Create a new test case `test_generate_implementation_plan` in `scripts/tests/test_ai_service.py`.
    *   The test will mock the AI API call and provide a sample user request and context content as input.
    *   It will define an expected JSON output representing the structured plan and assert that the new `generate_implementation_plan` function correctly parses this JSON into a Python dictionary.

2.  **AI Service Enhancement (`ai_service.py`):**
    *   Create a new function `generate_implementation_plan(user_prompt: str, context_content: str)`.
    *   This function will construct a detailed prompt instructing the AI to act as a senior software architect, analyze the provided context, and return a single JSON object containing a `proposed_issues` list.
    *   The prompt will specify the exact JSON structure required for each proposed issue (title, description, labels, etc.).

3.  **CLI Workflow Update (`gemini_cli.py`):**
    *   Modify the `create-feature` command.
    *   After receiving the list of relevant files from the pre-filtering step, implement a new helper function to read the full content of these files into a single string.
    *   Call the new `ai_service.generate_implementation_plan` with the user's request and the aggregated content.
    *   For this implementation, the command will pretty-print the resulting structured plan to the console for verification.

4.  **Verification:**
    *   Run `pytest` to ensure the new test case passes.
    *   Manually run the `create-feature` command to verify the end-to-end process and inspect the structured plan printed to the console.

5.  **Documentation:**
    *   Upon completion, activate the "Documentation Reconciliation Protocol" to update all relevant documents with the status of this task.
---

## Future Features / Enhancements:

---

## Fix Story Map Generation and Upload Logic

**Status:** [DONE]

**Description:** Fixed several bugs in the `create-feature` and `upload-story-map` commands to ensure correct generation and uploading of new stories.

**Implementation Plan:**

1.  **Fix Incorrect Story File Path:** Modified `cli.py` to correctly identify existing epics from the `project_map.yaml` and place new stories within their corresponding epic directories. This resolves the issue where stories for existing epics were created at the wrong level.
2.  **Remove Description from `project_map.yaml`:** Modified `cli.py` to stop adding the full `description` field to the `project_map.yaml` for new issues. This keeps the map lightweight and focused on structure.
3.  **Upload Description from File:** Modified `gitlab_uploader.py` to read the description directly from the content of the local `.md` file during the upload process. This ensures that the full, detailed description is correctly uploaded to the GitLab issue.
4.  **Filter for New Links:** The upload process in `gitlab_uploader.py` was optimized to only process links where the source or target is a new issue. This prevents the system from creating duplicate "blocks" comments for existing relationships.
5.  **Correct Board Ordering:** The reordering logic was updated to use `move_before_id` instead of `move_after_id`. This compensates for the GitLab board's inverted visual display, ensuring stories now correctly appear *under* their parent epics.

**Testing Ideas:**

*   Verified that creating a new story for an existing epic places the `.md` file in the correct subdirectory.
*   Verified that the `project_map.yaml` no longer contains the `description` field for newly created nodes.
*   Verified that uploading a new story correctly populates the issue's description field in GitLab from the local file.

### Proposed Backlog Item

**Title:** Feature: Anonymize GitLab Context During AI Processing

**User Story:**
*As a security-conscious user, I want to ensure that project-specific sensitive identifiers (like GitLab URL and Project ID) are not sent to external AI providers, so that I can preserve project data privacy and security.*

**Description:**
In the current operation, the `create-feature` command directly passes the content of relevant issues and documents, which may contain the project's URL and identifiers, as part of the prompt to the AI LLM. This poses a data privacy risk.

This task aims to introduce a "filter and re-substitution" mechanism that anonymizes outgoing data and de-anonymizes incoming data.

**Implementation Steps:**

1.  **Outgoing Data Redaction (Prompt Anonymization):**
    *   Before `gemini_cli` sends the prompt to `ai_service`, a new function must scan the entire context text.
    *   For example, all occurrences of `GITLAB_URL` and `GITLAB_PROJECT_ID` etc. must be replaced with a generic, non-identifiable placeholder (e.g., `[PROJECT_URL]` and `[PROJECT_ID]`).
    *   Only this anonymized context can be passed to the AI.

2.  **Incoming Data Re-substitution (Response De-anonymization):**
    *   After `ai_service` returns the JSON-formatted, generated story map, a new function must scan the `description` field of all items in the `proposed_issues` list.
    *   All occurrences of the `[PROJECT_URL]` and `[PROJECT_ID]` etc. placeholders must be replaced with the original values from environment variables.
    *   The `_generate_local_files` and subsequent `upload_artifacts_to_gitlab` functions will then receive this "restored" data structure.

**Acceptance Criteria:**
*   Prompts sent to the AI provider are guaranteed not to contain the specific GitLab URL or Project ID.
*   Any `[PROJECT_URL]` and `[PROJECT_ID]`etc. placeholders potentially returned in AI-generated issue descriptions are correctly restored to their original values.
*   The process must be completely transparent to the user.
*   New unit tests will be introduced to verify both the anonymization and de-anonymization logic.

---

## Future Features / Enhancements:

### Proposed Backlog Item

**Title:** Feature: Configurable User Story Language

**Status:** [PLANNED]

**Description:** This feature allows users to configure the language in which AI-generated user story files are created. By default, the language will be 'english', but users can change this setting in a configuration file. The AI will then adhere to this configured language when planning the user story map. Additionally, the system may be extended to detect the language of existing user stories during the initial synchronization and automatically set this language in the configuration file for subsequent use.

**Implementation Plan:**
1.  **Configuration Mechanism:** Implement a way to store and retrieve the preferred language setting (e.g., in `gitlab-config.json` or a new configuration file).
2.  **AI Service Integration:** Modify the `ai_service.py` to accept a `language` parameter for user story generation.
3.  **CLI Integration:** Update the `create-feature` command in `gemini_cli.py` to read the configured language and pass it to the AI service.
4.  **Language Detection (Optional):** Implement a language detection mechanism during the `smart_sync` process to identify the language of existing user stories and update the configuration.

**Testing Ideas:**
*   Verify that the default language ('english') is used when no configuration is specified.
*   Test changing the language in the configuration and confirm the AI generates user stories in the new language.
*   (If implemented) Verify that the language detection correctly identifies the language of existing stories and updates the configuration.

---

### Proposed Backlog Item

**Title:** Feature: Manual End-to-End Testing

**Status:** [PLANNED]

**Description:** Manually test the entire `ggw` project with a sample project, focusing on user-side intensive testing.

**Implementation Plan:**
*   Set up a new sample GitLab project.
*   Run `ggw` commands against the sample project.
*   Document any issues or unexpected behavior.

**Testing Ideas:**
*   Verify that `sync` command correctly fetches issues.
*   Verify that `create-feature` command generates correct story maps.
*   Verify that `upload` command correctly creates issues and links in GitLab.

---

### Proposed Backlog Item

**Title:** Enhancement: Integrate Coverage Report into GitLab Pipeline

**Status:** [PLANNED]

**Description:** Investigate and implement a solution to include the code coverage report in the GitLab pipeline's uploaded test reports, if feasible.

**Implementation Plan:**
*   Research GitLab CI/CD documentation for coverage report integration.
*   Modify `.gitlab-ci.yml` to generate and upload coverage reports.
*   Verify the report appears in GitLab.

**Testing Ideas:**
*   Run pipeline and check for coverage report in GitLab UI.

---

### Proposed Backlog Item

**Title:** Enhancement: Pipeline Cache Optimization

**Status:** [PLANNED]

**Description:** Optimize the GitLab CI/CD pipeline to ensure effective use of caching for faster execution.

**Implementation Plan:**
*   Review existing `.gitlab-ci.yml` for cache configurations.
*   Identify potential areas for caching (e.g., `uv` dependencies).
*   Implement or adjust cache settings.
*   Monitor pipeline execution times to confirm improvements.

**Testing Ideas:**
*   Run pipeline multiple times and compare execution times with and without cache.

---

### Proposed Backlog Item

**Title:** Enhancement: Conditional Pipeline Triggering for Documentation Changes

**Status:** [PLANNED]

**Description:** Implement a mechanism in the GitHub Actions workflow to prevent unnecessary test and build pipeline runs when only documentation or non-code files have been modified.

**Implementation Plan:**
*   Analyze `.github/workflows/ci.yml` to identify current pipeline triggers.
*   Research GitHub Actions `on.<push|pull_request>.paths` or `on.<push|pull_request>.paths-ignore` features to conditionally run jobs based on file changes.
*   Investigate using a specific flag in the commit message (e.g., `[skip ci]`, `[docs]`) as an alternative or supplementary method, and evaluate this against best practices.
*   Define rules to skip test and build stages if changes are limited to `docs/` directory or other specified non-code files.
*   Implement the changes in `.github/workflows/ci.yml`.

**Testing Ideas:**
*   Make a change only in a documentation file and verify that the test and build stages are skipped.
*   Make a change in a code file and verify that the full pipeline runs.