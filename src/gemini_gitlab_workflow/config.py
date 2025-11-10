import os
from pathlib import Path

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
