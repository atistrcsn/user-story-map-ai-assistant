# GitLab AI Assistant

This project is an intelligent CLI tool designed to streamline agile software development workflows using GitLab. It leverages AI to analyze high-level feature requests, break them down into epics and stories, and manage the synchronization between a local file-based representation and a GitLab project.

## Core Features

*   **AI-Assisted Story Map Generation:** Provide a high-level feature description, and the AI will analyze your project's context to propose a structured plan of epics and stories.
*   **Local First Workflow:** All changes are first generated locally as Markdown files and a `project_map.yaml`, allowing for review and version control before pushing to GitLab.
*   **Intelligent Synchronization:** Uses a smart-sync mechanism to only update local files for issues that have changed in GitLab, ensuring fast and efficient operation.
*   **Robust GitLab Integration:** Handles the creation of labels, issues, and hierarchical links (`relates_to`) in a transactional manner with rollback capabilities.

---

## Setup and Installation

This project is now a formal Python package (`gemini-gitlab-workflow`) and uses `uv` for environment and dependency management.

1.  **Prerequisites:**
    *   Python 3.12+
    *   `uv` installed (`pip install uv`)

2.  **Run the Setup Script:**
    From the project root (`/workspaces`), run the `setup.sh` script. This will:
    *   Install the `gemini-gitlab-workflow` package in editable mode.
    *   Create a global configuration directory (`~/.config/gemini_workflows/`).
    *   Create a template `config.yaml` file for your GitLab details.
    *   Copy `gemini_tools.py` for Gemini CLI integration.

    ```bash
    ./setup.sh
    ```

3.  **Configure GitLab and Gemini API Keys:**
    Edit the newly created configuration file (`~/.config/gemini_workflows/config.yaml`) with your GitLab instance URL, private token, project ID, and your Gemini API key.

    ```yaml
    # GitLab API Configuration
    gitlab_url: "https://your-gitlab-instance.com"
    private_token: "your_private_token_here"
    project_id: "your_gitlab_project_id"

    # Gemini API Configuration
    gemini_worker_api_key: "your_gemini_api_key"
    ```

---

## Core Workflow

The primary workflow consists of three main steps, accessible via the `ggw` command. Always ensure you are in the project's `uv` environment or use `uv run`.

### Step 1: Synchronize with GitLab

First, synchronize the local state with your GitLab project. This command fetches the latest issue data and rebuilds your local `gitlab_data/` directory and `project_map.yaml`.

```bash
uv run ggw sync map
```

### Step 2: Create a New Feature

Provide a high-level description of a feature. The AI will analyze your project and propose a plan.

```bash
uv run ggw create-feature "Implement user profile picture upload functionality"
```
The tool will present a plan for your approval. If you approve it, it will generate the necessary local `.md` files and update `project_map.yaml`.

### Step 3: Upload to GitLab

After generating the local files, upload them to GitLab. This command reads the `project_map.yaml`, creates the new labels and issues, and sets up the hierarchical links.

```bash
uv run ggw upload story-map
```

---

## Command Reference

All commands are run via `uv run ggw [COMMANDS]`.

*   `create-feature <FEATURE_DESCRIPTION>`
    *   Starts the AI-assisted workflow to generate a plan for a new feature.
    *   Generates local files upon user approval.

*   `sync map`
    *   Synchronizes with GitLab and rebuilds the local `project_map.yaml` and `gitlab_data/` directory.

*   `upload story-map`
    *   Uploads new, locally generated issues and links from `project_map.yaml` to GitLab.

---

## Running Tests

To run the automated tests and generate a coverage report, use the following command from the project root:

```bash
uv run pytest --cov=src/gemini_gitlab_workflow tests/
```