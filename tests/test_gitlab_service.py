import pytest
from unittest.mock import patch, MagicMock

from gemini_gitlab_workflow.gitlab_service import (
    smart_sync,
    build_project_map_and_sync_files,
    upload_new_artifacts,
)

@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Automatically sets the project ID for all tests."""
    monkeypatch.setenv("GGW_GITLAB_PROJECT_ID", "12345")

@pytest.fixture
def mock_gitlab_client():
    """Mocks the gitlab_client module."""
    with patch('gemini_gitlab_workflow.gitlab_service.gitlab_client') as mock:
        yield mock

@pytest.fixture
def mock_file_system_repo():
    """Mocks the file_system_repo module."""
    with patch('gemini_gitlab_workflow.gitlab_service.file_system_repo') as mock:
        yield mock

@pytest.fixture
def mock_project_mapper():
    """Mocks the project_mapper module."""
    with patch('gemini_gitlab_workflow.gitlab_service.project_mapper') as mock:
        yield mock

@pytest.fixture
def mock_gitlab_uploader():
    """Mocks the gitlab_uploader module."""
    with patch('gemini_gitlab_workflow.gitlab_service.gitlab_uploader') as mock:
        yield mock

def test_smart_sync_orchestration(mock_gitlab_client, mock_file_system_repo):
    # Arrange
    mock_file_system_repo.read_timestamps_cache.return_value = {"1": "2025-01-01T00:00:00.000Z"}
    
    issue1 = MagicMock()
    issue1.iid = 1
    issue1.updated_at = "2025-01-01T00:00:00.000Z" # Not updated
    
    issue2 = MagicMock()
    issue2.iid = 2
    issue2.title = "Updated Issue"
    issue2.updated_at = "2025-01-02T00:00:00.000Z" # Updated
    
    mock_gitlab_client.get_project_issues.return_value = [issue1, issue2]
    mock_gitlab_client.get_project_issue.return_value = issue2

    # Act
    result = smart_sync()

    # Assert
    assert result["status"] == "success"
    assert result["updated_count"] == 1
    assert result["updated_issues"][0]["title"] == "Updated Issue"
    
    mock_file_system_repo.read_timestamps_cache.assert_called_once()
    mock_gitlab_client.get_project_issues.assert_called_once()
    mock_gitlab_client.get_project_issue.assert_called_once_with("12345", 2)
    mock_file_system_repo.write_timestamps_cache.assert_called_once()

def test_build_project_map_orchestration(mock_project_mapper):
    # Arrange
    mock_project_mapper.build_project_map.return_value = {"status": "success", "issues_found": 5}

    # Act
    result = build_project_map_and_sync_files()

    # Assert
    assert result["status"] == "success"
    assert result["issues_found"] == 5
    mock_project_mapper.build_project_map.assert_called_once_with("12345")

def test_upload_new_artifacts_orchestration(mock_gitlab_uploader):
    # Arrange
    project_map = {"nodes": [], "links": []}
    mock_gitlab_uploader.upload_artifacts_to_gitlab.return_value = {"status": "success", "issues_created": 1}

    # Act
    result = upload_new_artifacts(project_map)

    # Assert
    assert result["status"] == "success"
    assert result["issues_created"] == 1
    mock_gitlab_uploader.upload_artifacts_to_gitlab.assert_called_once_with("12345", project_map)