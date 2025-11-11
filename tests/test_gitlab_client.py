import pytest
from unittest.mock import MagicMock, patch
import gitlab

# Import the functions to be tested
from gemini_gitlab_workflow.gitlab_client import (
    get_gitlab_client,
    get_project,
    get_project_issues,
    get_project_issue,
    get_issue_links,
    get_issue_notes,
    get_project_labels,
    create_project_label,
    delete_project_label,
    create_project_issue,
    delete_project_issue,
    create_issue_note,
    create_issue_link,
)

@pytest.fixture(scope="function")
def mock_gitlab_instance():
    """Mocks the gitlab.Gitlab instance."""
    with patch('gitlab.Gitlab') as mock:
        instance = mock.return_value
        instance.auth.return_value = None
        yield instance

@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Automatically sets required environment variables for all tests."""
    monkeypatch.setenv("GGW_GITLAB_URL", "https://gitlab.example.com")
    monkeypatch.setenv("GGW_GITLAB_PRIVATE_TOKEN", "fake_token")
    # Clear the lru_cache for get_gitlab_client before each test
    get_gitlab_client.cache_clear()

def test_get_gitlab_client_success(mock_gitlab_instance):
    """Tests successful GitLab client initialization."""
    client = get_gitlab_client()
    mock_gitlab_instance.auth.assert_called_once()
    assert client is not None

def test_get_gitlab_client_missing_env_vars(monkeypatch):
    """Tests that client initialization fails if env vars are missing."""
    monkeypatch.delenv("GGW_GITLAB_URL")
    with pytest.raises(ValueError, match="must be set"):
        get_gitlab_client()

def test_get_gitlab_client_auth_fails(mock_gitlab_instance):
    """Tests that client initialization fails if gitlab.auth() fails."""
    mock_gitlab_instance.auth.side_effect = gitlab.exceptions.GitlabAuthenticationError("Auth failed")
    with pytest.raises(ConnectionError, match="Auth failed"):
        get_gitlab_client()

def test_get_project(mock_gitlab_instance):
    """Tests fetching a project."""
    mock_project = MagicMock()
    mock_gitlab_instance.projects.get.return_value = mock_project
    project = get_project("123")
    mock_gitlab_instance.projects.get.assert_called_once_with("123")
    assert project == mock_project

def test_get_project_issues(mock_gitlab_instance):
    """Tests listing project issues."""
    mock_project = MagicMock()
    mock_gitlab_instance.projects.get.return_value = mock_project
    get_project_issues("123", all=True)
    mock_project.issues.list.assert_called_once_with(all=True)

def test_get_project_issue(mock_gitlab_instance):
    """Tests fetching a single project issue."""
    mock_project = MagicMock()
    mock_gitlab_instance.projects.get.return_value = mock_project
    get_project_issue("123", 456)
    mock_project.issues.get.assert_called_once_with(456)

def test_get_issue_links(mock_gitlab_instance):
    """Tests listing issue links."""
    mock_issue = MagicMock()
    mock_project = MagicMock()
    mock_project.issues.get.return_value = mock_issue
    mock_gitlab_instance.projects.get.return_value = mock_project
    get_issue_links("123", 456)
    mock_issue.links.list.assert_called_once_with(all=True)

def test_get_issue_notes(mock_gitlab_instance):
    """Tests listing issue notes."""
    mock_issue = MagicMock()
    mock_project = MagicMock()
    mock_project.issues.get.return_value = mock_issue
    mock_gitlab_instance.projects.get.return_value = mock_project
    get_issue_notes("123", 456)
    mock_issue.notes.list.assert_called_once_with(all=True)

def test_get_project_labels(mock_gitlab_instance):
    """Tests listing project labels."""
    mock_project = MagicMock()
    mock_gitlab_instance.projects.get.return_value = mock_project
    get_project_labels("123")
    mock_project.labels.list.assert_called_once_with(all=True)

def test_create_project_label(mock_gitlab_instance):
    """Tests creating a project label."""
    mock_project = MagicMock()
    mock_gitlab_instance.projects.get.return_value = mock_project
    label_data = {'name': 'test-label', 'color': '#ff0000'}
    create_project_label("123", label_data)
    mock_project.labels.create.assert_called_once_with(label_data)

def test_delete_project_label(mock_gitlab_instance):
    """Tests deleting a project label."""
    mock_project = MagicMock()
    mock_gitlab_instance.projects.get.return_value = mock_project
    delete_project_label("123", "test-label")
    mock_project.labels.delete.assert_called_once_with("test-label")

def test_create_project_issue(mock_gitlab_instance):
    """Tests creating a project issue."""
    mock_project = MagicMock()
    mock_gitlab_instance.projects.get.return_value = mock_project
    issue_data = {'title': 'Test Issue'}
    create_project_issue("123", issue_data)
    mock_project.issues.create.assert_called_once_with(issue_data)

def test_delete_project_issue(mock_gitlab_instance):
    """Tests deleting a project issue."""
    mock_project = MagicMock()
    mock_gitlab_instance.projects.get.return_value = mock_project
    delete_project_issue("123", 456)
    mock_project.issues.delete.assert_called_once_with(456)

def test_create_issue_note(mock_gitlab_instance):
    """Tests creating an issue note."""
    mock_issue = MagicMock()
    mock_project = MagicMock()
    mock_project.issues.get.return_value = mock_issue
    mock_gitlab_instance.projects.get.return_value = mock_project
    note_data = {'body': 'Test note'}
    create_issue_note("123", 456, note_data)
    mock_issue.notes.create.assert_called_once_with(note_data)

def test_create_issue_link(mock_gitlab_instance):
    """Tests creating an issue link."""
    mock_issue = MagicMock()
    mock_project = MagicMock()
    mock_project.issues.get.return_value = mock_issue
    mock_gitlab_instance.projects.get.return_value = mock_project
    create_issue_link("123", 456, 789)
    expected_link_data = {'target_project_id': '123', 'target_issue_iid': 789, 'link_type': 'relates_to'}
    mock_issue.links.create.assert_called_once_with(expected_link_data)
