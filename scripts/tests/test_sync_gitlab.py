import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import Mock
from sync_gitlab import _slugify, _generate_markdown_content, AGILE_HIERARCHY_MAP, _get_issue_filepath

# Mock GitLab Issue object for testing
class MockGitlabIssue:
    def __init__(self, iid, title, issue_type, state, labels, milestone, assignee, due_date, created_at, updated_at, web_url, description=None):
        self.iid = iid
        self.title = title
        self.issue_type = issue_type
        self.state = state
        self.labels = labels
        self.milestone = {'title': milestone} if milestone else None
        self.assignee = {'username': assignee} if assignee else None
        self.due_date = due_date
        self.created_at = created_at
        self.updated_at = updated_at
        self.web_url = web_url
        self.description = description

# Tests for _slugify
def test_slugify_basic():
    assert _slugify("Hello World") == "hello-world"

def test_slugify_with_special_characters():
    assert _slugify("Hello, World! This is a test.") == "hello-world-this-is-a-test"

def test_slugify_with_multiple_spaces():
    assert _slugify("  Hello   World  ") == "hello-world"

def test_slugify_empty_string():
    assert _slugify("") == ""

def test_slugify_only_special_characters():
    assert _slugify("!@#$%^&*()") == ""

# Tests for _generate_markdown_content
def test_generate_markdown_content_full_issue():
    mock_issue = MockGitlabIssue(
        iid=1,
        title="Test Issue",
        issue_type="issue",
        state="opened",
        labels=["bug", "priority::high"],
        milestone="Sprint 1",
        assignee="testuser",
        due_date="2025-12-31",
        created_at="2025-11-01T10:00:00.000Z",
        updated_at="2025-11-01T11:00:00.000Z",
        web_url="http://gitlab.com/test/issue/1",
        description="This is a test description."
    )
    content = _generate_markdown_content(mock_issue)
    expected_content_start = """---
id: 1
title: Test Issue
type: issue
state: opened
labels:
- bug
- priority::high
milestone: Sprint 1
assignee: testuser
due_date: '2025-12-31'
created_at: '2025-11-01T10:00:00.000Z'
updated_at: '2025-11-01T11:00:00.000Z'
web_url: http://gitlab.com/test/issue/1
---

This is a test description."""
    assert content.strip() == expected_content_start.strip()

def test_generate_markdown_content_minimal_issue():
    mock_issue = MockGitlabIssue(
        iid=2,
        title="Minimal Issue",
        issue_type="task",
        state="closed",
        labels=[],
        milestone=None,
        assignee=None,
        due_date=None,
        created_at="2025-11-02T10:00:00.000Z",
        updated_at="2025-11-02T10:00:00.000Z",
        web_url="http://gitlab.com/test/issue/2",
        description=None
    )
    content = _generate_markdown_content(mock_issue)
    expected_content_start = """---
id: 2
title: Minimal Issue
type: task
state: closed
labels: []
created_at: '2025-11-02T10:00:00.000Z'
updated_at: '2025-11-02T10:00:00.000Z'
web_url: http://gitlab.com/test/issue/2
---

No description provided."""
    assert content.strip() == expected_content_start.strip()

def test_generate_markdown_content_with_empty_description():
    mock_issue = MockGitlabIssue(
        iid=3,
        title="Issue with Empty Description",
        issue_type="bug",
        state="opened",
        labels=[],
        milestone=None,
        assignee=None,
        due_date=None,
        created_at="2025-11-03T10:00:00.000Z",
        updated_at="2025-11-03T10:00:00.000Z",
        web_url="http://gitlab.com/test/issue/3",
        description=""
    )
    content = _generate_markdown_content(mock_issue)
    expected_content_start = """---
id: 3
title: Issue with Empty Description
type: bug
state: opened
labels: []
created_at: '2025-11-03T10:00:00.000Z'
updated_at: '2025-11-03T10:00:00.000Z'
web_url: http://gitlab.com/test/issue/3
---

No description provided."""
    assert content.strip() == expected_content_start.strip()

# Tests for _get_issue_filepath
def test_get_issue_filepath_unassigned():
    mock_issue = MockGitlabIssue(
        iid=101,
        title="Unassigned Issue",
        issue_type="issue",
        state="opened",
        labels=[],
        milestone=None, assignee=None, due_date=None, created_at="", updated_at="", web_url=""
    )
    base_output_dir = "test_output"
    expected_path = os.path.join(base_output_dir, "_unassigned", "unassigned-issue.md")
    assert _get_issue_filepath(mock_issue, base_output_dir) == expected_path

def test_get_issue_filepath_with_backbone_epic_story_labels():
    mock_issue = MockGitlabIssue(
        iid=102,
        title="User Registration Feature",
        issue_type="issue",
        state="opened",
        labels=["Backbone: User Access", "Type::Epic", "Type::Story"],
        milestone=None, assignee=None, due_date=None, created_at="", updated_at="", web_url=""
    )
    base_output_dir = "test_output"
    expected_path = os.path.join(
        base_output_dir,
        "backbones", "user-access",
        "epics", "user-registration-feature",
        "stories", "user-registration-feature",
        "user-registration-feature.md"
    )
    assert _get_issue_filepath(mock_issue, base_output_dir) == expected_path

def test_get_issue_filepath_with_task_label():
    mock_issue = MockGitlabIssue(
        iid=103,
        title="Implement Login Button",
        issue_type="task",
        state="opened",
        labels=["Task: Frontend Development"],
        milestone=None, assignee=None, due_date=None, created_at="", updated_at="", web_url=""
    )
    base_output_dir = "test_output"
    expected_path = os.path.join(
        base_output_dir,
        "tasks", "frontend-development",
        "implement-login-button.md"
    )
    assert _get_issue_filepath(mock_issue, base_output_dir) == expected_path

def test_get_issue_filepath_with_mixed_labels_and_order():
    mock_issue = MockGitlabIssue(
        iid=104,
        title="Payment Gateway Integration",
        issue_type="issue",
        state="opened",
        labels=["Type::Story", "Type::Epic", "Backbone: Payments"],
        milestone=None, assignee=None, due_date=None, created_at="", updated_at="", web_url=""
    )
    base_output_dir = "test_output"
    # Expecting order based on AGILE_HIERARCHY_MAP: Backbone -> Epic -> Story
    expected_path = os.path.join(
        base_output_dir,
        "backbones", "payments",
        "epics", "payment-gateway-integration",
        "stories", "payment-gateway-integration",
        "payment-gateway-integration.md"
    )
    assert _get_issue_filepath(mock_issue, base_output_dir) == expected_path

def test_get_issue_filepath_with_non_hierarchy_labels():
    mock_issue = MockGitlabIssue(
        iid=105,
        title="Bug Fix",
        issue_type="bug",
        state="opened",
        labels=["bug", "priority::high", "Type::Epic"],
        milestone=None, assignee=None, due_date=None, created_at="", updated_at="", web_url=""
    )
    base_output_dir = "test_output"
    expected_path = os.path.join(
        base_output_dir,
        "epics", "bug-fix",
        "bug-fix.md"
    )
    assert _get_issue_filepath(mock_issue, base_output_dir) == expected_path
