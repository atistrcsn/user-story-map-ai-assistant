import os
import pytest
from src.gemini_gitlab_workflow.sanitizer import Sanitizer

@pytest.fixture(autouse=True)
def set_env_vars():
    os.environ["GGW_GITLAB_URL"] = "https://gitlab.com/my-org/my-project"
    os.environ["GGW_GITLAB_PROJECT_ID"] = "12345"
    yield
    del os.environ["GGW_GITLAB_URL"]
    del os.environ["GGW_GITLAB_PROJECT_ID"]

@pytest.fixture
def sanitizer_instance():
    return Sanitizer()

def test_anonymize_text(sanitizer_instance):
    original_text = "This is a test with https://gitlab.com/my-org/my-project and project ID 12345."
    anonymized = sanitizer_instance.anonymize_text(original_text)
    assert anonymized == "This is a test with [PROJECT_URL] and project ID [PROJECT_ID]."

def test_deanonymize_text(sanitizer_instance):
    anonymized_text = "This is a test with [PROJECT_URL] and project ID [PROJECT_ID]."
    deanonymized = sanitizer_instance.deanonymize_text(anonymized_text)
    assert deanonymized == "This is a test with https://gitlab.com/my-org/my-project and project ID 12345."

def test_anonymize_and_deanonymize_roundtrip(sanitizer_instance):
    original_text = "Another test for https://gitlab.com/my-org/my-project and ID 12345, with some other text."
    anonymized = sanitizer_instance.anonymize_text(original_text)
    deanonymized = sanitizer_instance.deanonymize_text(anonymized)
    assert deanonymized == original_text

def test_anonymize_text_no_match(sanitizer_instance):
    original_text = "No GitLab URL or ID here."
    anonymized = sanitizer_instance.anonymize_text(original_text)
    assert anonymized == original_text

def test_deanonymize_text_no_match(sanitizer_instance):
    anonymized_text = "No placeholders here."
    deanonymized = sanitizer_instance.deanonymize_text(anonymized_text)
    assert deanonymized == anonymized_text