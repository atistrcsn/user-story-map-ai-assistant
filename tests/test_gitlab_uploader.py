import pytest
from unittest.mock import MagicMock, patch, call
import gitlab

from gemini_gitlab_workflow.gitlab_uploader import upload_artifacts_to_gitlab

@pytest.fixture
def mock_gitlab_client():
    """Mocks the gitlab_client module."""
    with patch('gemini_gitlab_workflow.gitlab_uploader.gitlab_client') as mock:
        yield mock

@pytest.fixture
def mock_project_map():
    """Provides a sample project map for uploading."""
    return {
        "nodes": [
            {"id": "NEW_1", "title": "New Epic", "labels": ["Type::Epic", "NewLabel"], "description": ""},
            {"id": "NEW_2", "title": "New Story", "labels": ["Type::Story"], "description": "Desc"}
        ],
        "links": [
            {"source": "NEW_1", "target": "NEW_2", "type": "contains"},
            {"source": "NEW_2", "target": 123, "type": "blocks"}
        ]
    }

def test_upload_artifacts_happy_path(mock_gitlab_client, mock_project_map):
    # Arrange
    mock_gitlab_client.get_project_labels.return_value = []
    
    mock_issue_epic = MagicMock()
    mock_issue_epic.iid = 101
    mock_issue_story = MagicMock()
    mock_issue_story.iid = 102
    mock_gitlab_client.create_project_issue.side_effect = [mock_issue_epic, mock_issue_story]

    # Act
    result = upload_artifacts_to_gitlab("proj_id", mock_project_map)

    # Assert
    assert result["status"] == "success"
    assert result["labels_created"] == 3
    assert result["issues_created"] == 2
    assert result["issue_links_created"] == 1
    assert result["notes_with_links_created"] == 1

    mock_gitlab_client.create_project_label.assert_has_calls([
        call("proj_id", {'name': 'Type::Epic', 'color': '#F0AD4E'}),
        call("proj_id", {'name': 'NewLabel', 'color': '#F0AD4E'}),
    ], any_order=True)
    
    mock_gitlab_client.create_issue_note.assert_called_once_with(
        "proj_id", 123, {'body': '/blocked by #102'}
    )
    
    mock_gitlab_client.create_issue_link.assert_called_once_with("proj_id", 101, 102)

def test_upload_artifacts_rollback_on_failure(mock_gitlab_client, mock_project_map):
    # Arrange
    mock_gitlab_client.get_project_labels.return_value = []
    
    mock_issue_epic = MagicMock()
    mock_issue_epic.iid = 101
    mock_gitlab_client.create_project_issue.side_effect = [
        mock_issue_epic,
        gitlab.exceptions.GitlabError("Failed to create issue")
    ]

    # Act
    result = upload_artifacts_to_gitlab("proj_id", mock_project_map)

    # Assert
    assert result["status"] == "error"
    assert "Failed to create issue" in result["message"]

    # Verify rollback calls
    mock_gitlab_client.delete_project_issue.assert_called_once_with("proj_id", 101)
    mock_gitlab_client.delete_project_label.assert_has_calls([
        call("proj_id", "Type::Epic"),
        call("proj_id", "NewLabel"),
    ], any_order=True)

def test_upload_handles_existing_links_gracefully(mock_gitlab_client, mocker):
    # Arrange
    project_map_with_existing_link = {
        "nodes": [{"id": 1, "title": "Epic"}, {"id": 2, "title": "Story"}],
        "links": [{"source": 1, "target": 2, "type": "contains"}]
    }
    
    # Simulate the 409 Conflict error using a mock object
    mock_error = gitlab.exceptions.GitlabError("Issue(s) already assigned")
    mock_error.response_code = 409
    
    mock_gitlab_client.create_issue_link.side_effect = mock_error
    mock_gitlab_client.get_project_labels.return_value = []

    # Act
    result = upload_artifacts_to_gitlab("proj_id", project_map_with_existing_link)

    # Assert
    assert result["status"] == "success"
    assert result["issues_created"] == 0
    assert result["issue_links_created"] == 0 # 0 because it was skipped, not created
    mock_gitlab_client.create_issue_link.assert_called_once_with("proj_id", 1, 2)
