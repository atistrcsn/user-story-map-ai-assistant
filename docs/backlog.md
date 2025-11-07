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
    *   `smart_sync`: Intelligens, időbélyeg alapú szinkronizáció a GitLab-bel.
    *   `build_project_map`: Függőségi gráfot és projekt térképet épít az issue-kból.
    *   Tiszta, tesztelhető logika, leválasztva a CLI rétegről.
*   **Comprehensive Test Coverage:** Unit tesztek a CLI és a service rétegre is (`test_gemini_cli.py`, `test_gitlab_service.py`).
*   **Implement AI-generált Issue-k Feltöltése a GitLab-re (Implementáció és Tesztelés):** Az AI által generált és felhasználó által jóváhagyott issue-k (beleértve a címkéket és az issue linkeket a hierarchia számára) feltöltése a GitLab-re egy különálló `gemini-cli upload story-map` parancs segítségével történik, miután a `create-feature` parancs helyileg generálta a story map-et. Ez magában foglalja a `gitlab_service.upload_artifacts_to_gitlab` függvény meghívását a generált `project_map` adatokkal, és automatizált tesztekkel.

*   **Függőségi láncok helyes kezelése:** Kijavítottam egy hibát, ahol a `create-feature` parancs által generált `project_map.yaml` nem tartalmazta a helyes `contains` típusú linkeket az újonnan létrehozott epicek és sztorik között. A rendszer most már korrektül felépíti a hierarchikus linkeket a `project_map.yaml`-ban, biztosítva a szülő-gyermek kapcsolatot az agilis elemek között.

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

**Status:** DONE

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

## Future Features / Enhancements:

---

## Feladatok és Incidensek

*   **INC-001: `project_map.yaml` hiányzó `description` mező javítása**
    *   **Státusz:** [KÉSZ]
    *   **Leírás:** A `gemini_cli.py` `_generate_local_files` függvénye nem adta hozzá a `description` mezőt a `project_map.yaml`-ban létrehozott új issue node-okhoz. Ez üres leírások feltöltését okozta. A hiba javítva lett, a mező most már helyesen bekerül a project map-be.

*   **INC-002: A feltöltési logika hibásan próbált létező linkeket újra létrehozni**
    *   **Státusz:** [KÉSZ]
    *   **Leírás:** A `gitlab_service.py` `upload_artifacts_to_gitlab` függvénye a `project_map.yaml`-ban lévő összes `contains` típusú linket megpróbálta létrehozni, beleértve a már létezőket is. Ez `409 Conflict` API hibát okozott. A logika javítva lett, hogy a feltöltés már csak az újonnan generált issue-khoz tartozó linkeket hozza létre.
