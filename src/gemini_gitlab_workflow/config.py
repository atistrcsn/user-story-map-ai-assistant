import os

# --- Centralized Path and Configuration Definitions ---

# The project root is the current working directory from where the command is executed.
PROJECT_ROOT = os.getcwd()

# Get the data directory from environment variable, with a sensible default.
# This allows users to configure where the gitlab_data is stored.
DATA_DIR_NAME = os.getenv('GGW_DATA_DIR', 'gitlab_data')
DATA_DIR = os.path.join(PROJECT_ROOT, DATA_DIR_NAME)

# Define absolute paths for other key locations based on the project root.
CACHE_DIR = os.path.join(PROJECT_ROOT, ".gemini_cache")
PROJECT_MAP_PATH = os.path.join(PROJECT_ROOT, "project_map.yaml")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
TIMESTAMPS_CACHE_PATH = os.path.join(CACHE_DIR, "timestamps.json")

# --- Gemini Model Configuration ---
# Allows overriding the default models via environment variables.
GEMINI_SMART_MODEL = os.getenv("GGW_GEMINI_SMART_MODEL", "gemini-2.5-pro")
GEMINI_FAST_MODEL = os.getenv("GGW_GEMINI_FAST_MODEL", "gemini-2.5-flash-lite")
