# GitLab Sync Script

This directory contains the Python script for synchronizing GitLab issues.

## Setup & Usage (with uv)

1.  **Navigate to the scripts directory:**
    ```sh
    cd scripts
    ```

2.  **Create a virtual environment:**
    ```sh
    uv venv
    ```

3.  **Install dependencies:**
    ```sh
    uv pip sync pyproject.toml
    ```

4.  **Configure the script:**
    Copy `config.py.example` to `config.py` and fill in your GitLab URL and Private Access Token.

5.  **Run the script:**
    ```sh
    uv run python sync_gitlab.py
    ```
