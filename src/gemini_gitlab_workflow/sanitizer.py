"""
This module provides functions to anonymize and deanonymize text by replacing
sensitive information with placeholders.
"""

import os

def anonymize_text(text: str) -> str:
    """
    Replaces sensitive information in the text with placeholders.

    Args:
        text: The text to anonymize.

    Returns:
        The anonymized text.
    """
    gitlab_url = os.getenv("GGW_GITLAB_URL", "")
    project_id = os.getenv("GGW_GITLAB_PROJECT_ID", "")

    if gitlab_url:
        text = text.replace(gitlab_url, "[PROJECT_URL]")
    if project_id:
        text = text.replace(project_id, "[PROJECT_ID]")

    return text

def deanonymize_text(text: str) -> str:
    """
    Replaces placeholders in the text with sensitive information.

    Args:
        text: The text to deanonymize.

    Returns:
        The deanonymized text.
    """
    gitlab_url = os.getenv("GGW_GITLAB_URL", "")
    project_id = os.getenv("GGW_GITLAB_PROJECT_ID", "")

    if gitlab_url:
        text = text.replace("[PROJECT_URL]", gitlab_url)
    if project_id:
        text = text.replace("[PROJECT_ID]", project_id)

    return text
