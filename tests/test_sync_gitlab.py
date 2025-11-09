import pytest
from unittest.mock import Mock
import os
from gemini_gitlab_workflow.sync_gitlab import _slugify, _generate_markdown_content, AGILE_HIERARCHY_MAP, _get_issue_filepath

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

# Tests for main() function
from unittest.mock import patch, mock_open
from gemini_gitlab_workflow.sync_gitlab import main
from io import StringIO



# Mock GitLab Project object
class MockGitlabProject:
    def __init__(self, name_with_namespace, issues_list):
        self.name_with_namespace = name_with_namespace
        self.issues = Mock()
        self.issues.list.return_value = issues_list

# Mock GitLab API object
class MockGitlabAPI:
    def __init__(self, project_mock):
        self.projects = Mock()
        self.projects.get.return_value = project_mock
        self.project_mock = project_mock

    def auth(self):
        pass

@patch('gitlab.Gitlab')
@patch('gemini_gitlab_workflow.sync_gitlab.config')
@patch('os.makedirs')
@patch('os.path.exists')
@patch('shutil.rmtree')
@patch('builtins.open', new_callable=mock_open)
def test_main_sync_process(
    mock_open_file,
    mock_rmtree,
    mock_path_exists,
    mock_makedirs,
    mock_config,
    mock_gitlab_class,
):
    # Configure mocks
    mock_config.GITLAB_URL = "http://mock-gitlab.com"
    mock_config.PRIVATE_TOKEN = "mock-token"
    mock_config.PROJECT_PATH = "mock-group/mock-project"

    mock_path_exists.return_value = True  # Simulate gitlab_data dir exists for cleanup

    # Mock GitLab issues
    mock_issue_1 = MockGitlabIssue(
        iid=1,
        title="Test Issue 1",
        issue_type="issue",
        state="opened",
        labels=["Backbone: Feature A", "Type::Epic"],
        milestone="Sprint 1",
        assignee="user1",
        due_date="2025-01-01",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T01:00:00Z",
        web_url="http://mock-gitlab.com/issue/1",
        description="Description for Issue 1."
    )

    mock_issue_2 = MockGitlabIssue(
        iid=2,
        title="Test Issue 2",
        issue_type="task",
        state="closed",
        labels=["Type::Story", "Task: Subtask for Epic"],
        milestone=None,
        assignee="user2",
        due_date=None,
        created_at="2024-01-02T00:00:00Z",
        updated_at="2024-01-02T01:00:00Z",
        web_url="http://mock-gitlab.com/issue/2",
        description="Description for Issue 2."
    )
    
    mock_issue_3 = MockGitlabIssue(
        iid=3,
        title="Unassigned Issue",
        issue_type="bug",
        state="opened",
        labels=[], # No hierarchy labels
        milestone=None,
        assignee=None,
        due_date=None,
        created_at="2024-01-03T00:00:00Z",
        updated_at="2024-01-03T01:00:00Z",
        web_url="http://mock-gitlab.com/issue/3",
        description="Description for Unassigned Issue."
    )

    mock_project = MockGitlabProject(
        name_with_namespace="Mock Group / Mock Project",
        issues_list=[mock_issue_1, mock_issue_2, mock_issue_3],
    )
    mock_gitlab_instance = MockGitlabAPI(mock_project)
    mock_gitlab_class.return_value = mock_gitlab_instance

    # Run the main function
    main()

    # Assertions
    mock_rmtree.assert_called_once_with("/gitlab_data")
    mock_makedirs.assert_any_call("/gitlab_data", exist_ok=True)

    # Verify GitLab API calls
    mock_gitlab_class.assert_called_once_with(
        mock_config.GITLAB_URL, private_token=mock_config.PRIVATE_TOKEN
    )
    mock_gitlab_instance.projects.get.assert_called_once_with(mock_config.PROJECT_PATH)
    mock_project.issues.list.assert_called_once_with(all=True)

    # Verify file writing operations, paths and content
    expected_filepath_1 = os.path.join(
        "/gitlab_data",
        "backbones", "feature-a",
        "epics", "test-issue-1",
        "test-issue-1.md"
    )
    expected_content_1 = _generate_markdown_content(mock_issue_1)

    expected_filepath_2 = os.path.join(
        "/gitlab_data",
        "stories", "test-issue-2",
        "tasks", "subtask-for-epic",
        "test-issue-2.md"
    )
    expected_content_2 = _generate_markdown_content(mock_issue_2)

    expected_filepath_3 = os.path.join(
        "/gitlab_data",
        "_unassigned",
        "unassigned-issue.md"
    )
    expected_content_3 = _generate_markdown_content(mock_issue_3)

    mock_open_file.assert_any_call(expected_filepath_1, "w", encoding="utf-8")
    mock_open_file().write.assert_any_call(expected_content_1)
    
    mock_open_file.assert_any_call(expected_filepath_2, "w", encoding="utf-8")
    mock_open_file().write.assert_any_call(expected_content_2)
    
    mock_open_file.assert_any_call(expected_filepath_3, "w", encoding="utf-8")
    mock_open_file().write.assert_any_call(expected_content_3)
    # Ensure os.makedirs is called for each unique directory needed
    mock_makedirs.assert_any_call(os.path.dirname(expected_filepath_1), exist_ok=True)
    mock_makedirs.assert_any_call(os.path.dirname(expected_filepath_2), exist_ok=True)
    mock_makedirs.assert_any_call(os.path.dirname(expected_filepath_3), exist_ok=True)