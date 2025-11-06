# GitLab AI Assistant CLI

This directory contains the Python scripts for the GitLab AI Assistant, including the main command-line interface.

## Setup & Usage (with uv)

1.  **Navigate to the scripts directory:**
    ```sh
    cd scripts
    ```

2.  **Create a virtual environment:**
    ```sh
    uv venv
    ```

3.  **Activate the virtual environment:**
    ```sh
    source .venv/bin/activate
    ```

4.  **Install dependencies:**
    ```sh
    uv pip sync pyproject.toml
    ```

5.  **Configure Environment Variables:**
    Create a `.env` file in this directory (`/scripts`) and add the following variables:
    ```
    GITLAB_URL="https://your-gitlab-instance.com"
    GITLAB_PRIVATE_TOKEN="your_private_access_token"
    GITLAB_PROJECT_ID="your_project_id"
    ```

6.  **Run the CLI Tool:**
    The main tool is `gemini_cli.py`. You can see all available commands by running:
    ```sh
    python gemini_cli.py --help
    ```

    **Available Commands:**

    *   `sync map`: Fetches all issues from the configured GitLab project and builds a `project_map.yaml` file representing the nodes and their relationships.
        ```sh
        python gemini_cli.py sync map
        ```

    *   `create`: Initiates the AI-assisted workflow to create a new feature based on a high-level description. This command starts with a `smart-sync` to ensure the context is up-to-date.
        ```sh
        python gemini_cli.py create "Implement user profile pictures"
        ```

