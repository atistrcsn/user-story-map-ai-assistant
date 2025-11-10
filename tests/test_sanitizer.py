"""
Unit tests for the sanitizer module.
"""

import os
from unittest.mock import patch
from gemini_gitlab_workflow.sanitizer import anonymize_text, deanonymize_text

def test_anonymize_text():
    """
    Tests that the anonymize_text function correctly replaces sensitive data.
    """
    text = "This is a test with https://gitlab.com and project 12345."
    expected = "This is a test with [PROJECT_URL] and project [PROJECT_ID]."

    with patch.dict(os.environ, {"GGW_GITLAB_URL": "https://gitlab.com", "GGW_GITLAB_PROJECT_ID": "12345"}):
        assert anonymize_text(text) == expected

def test_deanonymize_text():
    """
    Tests that the deanonymize_text function correctly restores sensitive data.
    """
    text = "This is a test with [PROJECT_URL] and project [PROJECT_ID]."
    expected = "This is a test with https://gitlab.com and project 12345."

    with patch.dict(os.environ, {"GGW_GITLAB_URL": "https://gitlab.com", "GGW_GITLAB_PROJECT_ID": "12345"}):
        assert deanonymize_text(text) == expected

def test_anonymize_text_no_env_vars():
    """
    Tests that the anonymize_text function does nothing when env vars are not set.
    """
    text = "This is a test with https://gitlab.com and project 12345."
    with patch.dict(os.environ, {}, clear=True):
        assert anonymize_text(text) == text

def test_deanonymize_text_no_env_vars():
    """
    Tests that the deanonymize_text function does nothing when env vars are not set.
    """
    text = "This is a test with [PROJECT_URL] and project [PROJECT_ID]."
    with patch.dict(os.environ, {}, clear=True):
        assert deanonymize_text(text) == text
