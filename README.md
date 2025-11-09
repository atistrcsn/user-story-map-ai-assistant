# GitLab AI Assistant

This project is an intelligent CLI tool designed to streamline agile software development workflows using GitLab. It leverages AI to analyze high-level feature requests, break them down into epics and stories, and manage the synchronization between a local file-based representation and a GitLab project.

## Core Features

*   **AI-Assisted Story Map Generation:** Provide a high-level feature description, and the AI will analyze your project's context to propose a structured plan of epics and stories.
*   **Local First Workflow:** All changes are first generated locally as Markdown files and a `project_map.yaml`, allowing for review and version control before pushing to GitLab.
*   **Intelligent Synchronization:** Uses a smart-sync mechanism to only update local files for issues that have changed in GitLab, ensuring fast and efficient operation.
*   **Robust GitLab Integration:** Handles the creation of labels, issues, and hierarchical links (`relates_to`) in a transactional manner with rollback capabilities.

---

## Getting Started: A Two-Step Process

### Step 1: System-Wide Installation (One Time)

First, install the `ggw` command-line tool on your system.

1.  **Prerequisites:**
    *   Python 3.12+
    *   `uv` installed (`pip install uv`)

2.  **Run the Setup Script:**
    From the `gemini-gitlab-workflow` project directory, run the setup script. This will install the `ggw` command and make it available system-wide.

    ```bash
    ./setup.sh
    ```

### Step 2: Project Initialization (For Each Project)

For every project you want to manage with `ggw`, you need to initialize it.

1.  **Navigate to Your Project Directory:**
    ```bash
    cd /path/to/your/project
    ```

2.  **Initialize the Project:**
    Run the `init` command. This will create a `.env` file in your project directory.
    ```bash
    ggw init
    ```

3.  **Configure Your Project:**
    Open the newly created `.env` file and fill in your specific GitLab and Gemini API credentials. The `ggw` tool will automatically use this file for all commands run within this directory.

---

## Core Workflow

Once your project is initialized and configured, you can start using the main commands.

### 1. Synchronize with GitLab

Fetch the latest issue data from GitLab and build your local `gitlab_data/` directory and `project_map.yaml`.

```bash
ggw sync map
```

### 2. Create a New Feature

Provide a high-level description of a feature. The AI will analyze your project and propose a plan.

```bash
ggw create-feature "Implement user profile picture upload functionality"
```
The tool will present a plan for your approval. If you approve it, it will generate the necessary local `.md` files and update `project_map.yaml`.

### 3. Upload to GitLab

After generating the local files, upload them to GitLab. This command reads the `project_map.yaml`, creates the new labels and issues, and sets up the hierarchical links.

```bash
ggw upload story-map
```

---

## Command Reference

*   `ggw init`
    *   Initializes a project by creating a `.env` configuration file.

*   `ggw create-feature <FEATURE_DESCRIPTION>`
    *   Starts the AI-assisted workflow to generate a plan for a new feature.

*   `ggw sync map`
    *   Synchronizes with GitLab and rebuilds the local project map.

*   `ggw upload story-map`
    *   Uploads new, locally generated issues and links to GitLab.

---

## Building the Binary

To create a standalone, single-file executable that can be run without a Python installation, you can use PyInstaller directly.

1.  **Install development dependencies (if you haven't already):**
    ```bash
    uv pip install -e .[test]
    ```

2.  **Run the PyInstaller command:**
    ```bash
    uv run pyinstaller --name ggw --onefile --clean src/gemini_gitlab_workflow/cli.py
    ```

This command will run PyInstaller and create a `ggw` executable inside the `dist/` directory. You can then copy this file to any location (e.g., `/usr/local/bin`) and run it directly.

## Running Tests

To run the automated tests for the `gemini-gitlab-workflow` package itself, use the following command from its root directory:

```bash
uv run pytest --cov=src/gemini_gitlab_workflow tests/
```
