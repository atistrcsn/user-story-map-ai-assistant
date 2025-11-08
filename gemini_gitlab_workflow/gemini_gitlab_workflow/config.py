"""
Handles loading and accessing configuration for the Gemini GitLab Workflow tool.

This module manages a hierarchical configuration system, loading settings from:
1.  Default values defined in this file.
2.  A global configuration file (~/.config/gemini_workflows/config.yaml).
3.  A project-specific configuration file (.gemini-workflow.yaml) in the current directory.

Project-specific settings override global settings, which in turn override the defaults.
"""

import os
import yaml
from pathlib import Path

# --- Default Configuration ---
DEFAULT_CONFIG = {
    'gitlab': {
        'api_url': 'https://gitlab.com',
        'project_id': None,
        'private_token': None # This should be set in the global config
    },
    'paths': {
        'data_dir': 'gitlab_data',
        'project_map_file': 'project_map.yaml'
    },
    'labels': {
        'backbone_prefix': 'Backbone::',
        'epic_type_name': 'Type::Epic',
        'story_type_name': 'Type::Story',
        'colors': {
            'backbone': '#330066',
            'epic': '#6699cc',
            'story': '#eee600'
        }
    }
}

def _deep_update(source, overrides):
    """
    Recursively update a dictionary.
    """
    for key, value in overrides.items():
        if isinstance(value, dict) and key in source:
            source[key] = _deep_update(source.get(key, {}), value)
        else:
            source[key] = value
    return source

def load_config():
    """
    Loads the configuration from default, global, and project-specific files.
    """
    config = DEFAULT_CONFIG.copy()

    # 1. Load Global Config
    global_config_path = Path.home() / ".config" / "gemini_workflows" / "config.yaml"
    if global_config_path.exists():
        with open(global_config_path, 'r') as f:
            global_config = yaml.safe_load(f)
            if global_config:
                config = _deep_update(config, global_config)

    # 2. Load Project-Specific Config
    # We search upwards from the current directory for the config file
    current_dir = Path.cwd()
    project_config_path = None
    for parent in [current_dir] + list(current_dir.parents):
        potential_path = parent / ".gemini-workflow.yaml"
        if potential_path.exists():
            project_config_path = potential_path
            break
    
    if project_config_path:
        with open(project_config_path, 'r') as f:
            project_config = yaml.safe_load(f)
            if project_config:
                config = _deep_update(config, project_config)

    return config

# Load the configuration once when the module is imported
settings = load_config()

# --- Helper functions to get project-relative paths ---
def get_project_root():
    """
    Determines the project root by finding the directory containing the 
    .gemini-workflow.yaml file or defaulting to the current working directory.
    """
    current_dir = Path.cwd()
    for parent in [current_dir] + list(current_dir.parents):
        if (parent / ".gemini-workflow.yaml").exists():
            return parent
    return current_dir # Fallback to cwd if no config file is found

PROJECT_ROOT = get_project_root()

def get_data_dir():
    """Returns the absolute path to the data directory."""
    return PROJECT_ROOT / settings['paths']['data_dir']

def get_project_map_path():
    """Returns the absolute path to the project map file."""
    return PROJECT_ROOT / settings['paths']['project_map_file']