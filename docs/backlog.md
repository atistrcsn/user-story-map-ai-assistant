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

**Status:** [KÉSZ]

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

## Implement Real AI API Calls

**Status:** DONE

**Description:** Replace the mock AI calls in `ai_service.py` with actual calls to the Google Gemini API using the `google-generativeai` library. This will bring the AI-assisted feature to life.

**Implementation Plan:**

1.  **Prerequisites:**
    *   Add `google-generativeai` to the `dependencies` in `scripts/pyproject.toml`.
    *   Install the new dependency by running `uv pip install -r scripts/pyproject.toml`.
    *   Ensure the `GOOGLE_API_KEY` is set in the `.env` file in the project root.

2.  **Test-Driven Refactoring:**
    *   In `scripts/tests/test_ai_service.py`, change the mock target from our internal `call_google_gemini_api` to the external library's method: `@patch('google.generativeai.GenerativeModel.generate_content')`.
    *   Update the mock return value to be an object with a `.text` attribute, simulating the library's response object.
    *   Run `pytest` to confirm the tests fail (TDD Red phase).

3.  **Core Implementation (`ai_service.py`):**
    *   Add `import google.generativeai as genai` and `import os`.
    *   Configure the library at the module level using `genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))`.
    *   Rewrite the `call_google_gemini_api` function to:
        *   Instantiate a `genai.GenerativeModel`.
        *   Call the `model.generate_content()` method with the prompt.
        *   Include `try...except` block for robust error handling.
        *   Return the `response.text`.

4.  **Verification:**
    *   Run `pytest` again to confirm all tests now pass (TDD Green phase).
    *   Perform a manual, end-to-end test by running the `create-feature` command to see a real AI-generated response.

---

### Refactor Scripts into a Production-Ready Python Package

*   **Status:** `[PLANNED]`
*   **Description:** Refactor the collection of Python scripts into a formal, installable Python package named `gemini-gitlab-workflow`. The goal is to create a robust, maintainable, and extensible command-line tool (`ggw`) for managing the GitLab workflow, and to prepare it for deep integration as a custom tool within the Gemini CLI.
*   **Implementation Plan:**
    *   `[PLANNED]` Prepare src-layout as best practice
    *   `[PLANNED]` Structure the project as a standard Python package with `pyproject.toml`.
    *   `[PLANNED]` Create a centralized, hierarchical configuration system (`config.py`).
    *   `[PLANNED]` Develop a user-friendly Command-Line Interface (CLI) using Typer (`cli.py`).
    *   `[PLANNED]` Modularize the core logic into separate services (`gitlab_service.py`, `ai_service.py`).
    *   `[PLANNED]` Create a setup script (`setup.sh`) for easy installation and configuration.
    *   `[PLANNED]` Integrate the package's functionality as a custom tool for the Gemini CLI (`gemini_tools.py`).
    *   `[PLANNED]` Write comprehensive unit and integration tests for the new package structure.
*   **Testing Ideas:**
    *   Unit test individual functions in `gitlab_service` and `ai_service`.
    *   Test CLI commands (`ggw create-feature`, `ggw sync map`, etc.) with mocked APIs.
    *   End-to-end test: run the `setup.sh` script and then invoke the custom tool from within a Gemini CLI session.

---

## Future Features / Enhancements:

---

## Tasks and Incidents

*   **INC-001: Fix missing `description` field in `project_map.yaml`**
    *   **Status:** [DONE]
    *   **Description:** The `_generate_local_files` function in `gemini_cli.py` did not add the `description` field to the new issue nodes created in `project_map.yaml`. This caused empty descriptions to be uploaded. The bug has been fixed, and the field is now correctly included in the project map.

*   **INC-002: Upload logic incorrectly attempted to recreate existing links**
    *   **Status:** [DONE]
    *   **Description:** The `upload_artifacts_to_gitlab` function in `gitlab_service.py` attempted to create all `contains` type links in `project_map.yaml`, including those that already existed. This caused a `409 Conflict` API error. The logic has been fixed so that the upload now only creates links belonging to newly generated issues.

### **Proposed Backlog Item**

**Title:** Feature: Anonymize GitLab Context During AI Processing

**User Story:**
*As a security-conscious user, I want to ensure that project-specific sensitive identifiers (like GitLab URL and Project ID) are not sent to external AI providers, so that I can preserve project data privacy and security.*

**Description:**
In the current operation, the `create-feature` command directly passes the content of relevant issues and documents, which may contain the project's URL and identifiers, as part of the prompt to the AI LLM. This poses a data privacy risk.

This task aims to introduce a "filter and re-substitution" mechanism that anonymizes outgoing data and de-anonymizes incoming data.

**Implementation Steps:**

1.  **Outgoing Data Redaction (Prompt Anonymization):**
    *   Before `gemini_cli` sends the prompt to `ai_service`, a new function must scan the entire context text.
    *   All occurrences of `GITLAB_URL` and `GITLAB_PROJECT_ID` must be replaced with a generic, non-identifiable placeholder (e.g., `[PROJECT_URL]` and `[PROJECT_ID]`).
    *   Only this anonymized context can be passed to the AI.

2.  **Incoming Data Re-substitution (Response De-anonymization):**
    *   After `ai_service` returns the JSON-formatted, generated story map, a new function must scan the `description` field of all items in the `proposed_issues` list.
    *   All occurrences of the `[PROJECT_URL]` and `[PROJECT_ID]` placeholders must be replaced with the original values from environment variables.
    *   The `_generate_local_files` and subsequent `upload_artifacts_to_gitlab` functions will then receive this "restored" data structure.

**Acceptance Criteria:**
*   Prompts sent to the AI provider are guaranteed not to contain the specific GitLab URL or Project ID.
*   Any `[PROJECT_URL]` and `[PROJECT_ID]` placeholders potentially returned in AI-generated issue descriptions are correctly restored to their original values.
*   The process must be completely transparent to the user.
*   New unit tests will be introduced to verify both the anonymization and de-anonymization logic.