"""
Gemini Custom Tools for interacting with the GitLab Workflow package.

This file defines the functions that will be exposed to the Gemini agent.
These functions act as a thin wrapper around the command-line interface (CLI)
of the `gemini-gitlab-workflow` package, using subprocess to call the `ggw` command.
"""

import subprocess
import shutil

def _run_ggw_command(command: list[str]) -> str:
    """
    A helper function to run a `ggw` command and return its output.
    Checks if the `ggw` command is available in the system path.
    """
    ggw_path = shutil.which("ggw")
    if not ggw_path:
        return (
            "Error: The 'ggw' command is not found. "
            "Please ensure the 'gemini-gitlab-workflow' package is installed correctly "
            "and its script directory is in your system's PATH."
        )

    try:
        process = subprocess.run(
            [ggw_path] + command,
            capture_output=True,
            text=True,
            check=True  # Raises CalledProcessError for non-zero exit codes
        )
        # Combine stdout and stderr to give the agent full context
        output = f"--- STDOUT ---\n{process.stdout}\n"
        if process.stderr:
            output += f"--- STDERR ---\n{process.stderr}\n"
        return output
    except subprocess.CalledProcessError as e:
        # This catches errors from the script itself (e.g., invalid config)
        return (
            f"Error executing command: {' '.join(command)}\n"
            f"Exit Code: {e.returncode}\n"
            f"--- STDOUT ---\n{e.stdout}\n"
            f"--- STDERR ---\n{e.stderr}\n"
        )
    except FileNotFoundError:
        # This is a fallback, but shutil.which should prevent this.
        return "Error: 'ggw' command not found. Installation is likely broken."
    except Exception as e:
        # Catch any other unexpected errors
        return f"An unexpected error occurred: {e}"

def create_feature_story_map(feature_description: str) -> str:
    """
    Generates a local story map (Epics, Stories) for a new feature description.
    
    This tool takes a high-level feature description, uses an AI to break it down
    into a plan of GitLab issues (Epics and Stories), and generates the corresponding
    local Markdown files. These files can then be reviewed and modified before
    uploading to GitLab.

    Args:
        feature_description: A clear, high-level description of the feature to be implemented.

    Returns:
        The output of the generation script, indicating success or failure.
    """
    return _run_ggw_command(["create-feature", feature_description])

def upload_story_map_to_gitlab() -> str:
    """
    Uploads the locally generated and reviewed story map to GitLab.

    This tool reads the local `project_map.yaml`, creates the defined labels and issues
    in GitLab, and sets up the relationships (e.g., linking Stories to Epics).
    It should only be run after `create_feature_story_map` and any desired
    manual refinements to the local Markdown files.

    Returns:
        The output of the upload script, summarizing the created artifacts.
    """
    return _run_ggw_command(["upload", "story-map"])
