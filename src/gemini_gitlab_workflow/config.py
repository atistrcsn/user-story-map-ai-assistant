import os
from pathlib import Path
from dataclasses import dataclass, field
import logging

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Centralized Path and Configuration Definitions ---

# The project root is the current working directory from where the command is executed.
# Path.cwd() is the pathlib modern, object-oriented equivalent of os.getcwd().
PROJECT_ROOT = Path.cwd()

# Get the data directory from environment variable, with a sensible default.
# This allows users to configure where the gitlab_data is stored.
DATA_DIR_NAME = os.getenv('GGW_DATA_DIR', 'gitlab_data')
DATA_DIR = PROJECT_ROOT / DATA_DIR_NAME

# Define absolute paths for other key locations based on the project root.
CACHE_DIR = PROJECT_ROOT / ".gemini_cache"
PROJECT_MAP_PATH = PROJECT_ROOT / "project_map.yaml"
DOCS_DIR = PROJECT_ROOT / "docs"
TIMESTAMPS_CACHE_PATH = CACHE_DIR / "timestamps.json"

# --- Gemini Model Configuration ---
# Allows overriding the default models via environment variables.
GEMINI_SMART_MODEL = os.getenv("GGW_GEMINI_SMART_MODEL", "gemini-2.5-pro")
GEMINI_FAST_MODEL = os.getenv("GGW_GEMINI_FAST_MODEL", "gemini-2.5-flash-lite")

# --- GitLab Configuration ---
@dataclass
class GitlabConfig:
    """A dataclass to hold all GitLab-related configuration."""
    url: str = field(default_factory=lambda: os.getenv("GGW_GITLAB_URL", ""))
    private_token: str = field(default_factory=lambda: os.getenv("GGW_GITLAB_PRIVATE_TOKEN", ""))
    project_id: str = field(default_factory=lambda: os.getenv("GGW_GITLAB_PROJECT_ID", ""))
    board_id: int | None = field(default_factory=lambda: os.getenv("GGW_GITLAB_BOARD_ID"))

    def __post_init__(self):
        """Validate that essential GitLab configuration is present."""
        if not self.url or not self.private_token or not self.project_id:
            raise ValueError(
                "Essential GitLab configuration (GGW_GITLAB_URL, "
                "GGW_GITLAB_PRIVATE_TOKEN, GGW_GITLAB_PROJECT_ID) is missing. "
                "Please check your .env file or environment variables."
            )
        if self.board_id:
            try:
                self.board_id = int(self.board_id)
            except (ValueError, TypeError):
                logging.warning(
                    f"GGW_GITLAB_BOARD_ID is not a valid integer ('{self.board_id}'). "
                    "Disabling board-related features."
                )
                self.board_id = None
