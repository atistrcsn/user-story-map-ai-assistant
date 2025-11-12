import pytest
from unittest.mock import MagicMock, patch, call, mock_open
import gitlab
from ruamel.yaml import YAML

# Assuming the GitlabUploader class is in this module
from gemini_gitlab_workflow.gitlab_uploader import GitlabUploader, upload_artifacts_to_gitlab
from gemini_gitlab_workflow.config import GitlabConfig

# --- Fixtures ---

@pytest.fixture
def mock_gitlab_client():
    """Mocks the gitlab_client module."""
    with patch('gemini_gitlab_workflow.gitlab_uploader.gitlab_client') as mock:
        yield mock

@pytest.fixture
def mock_config():
    """Mocks the GitlabConfig dataclass."""
    with patch('gemini_gitlab_workflow.gitlab_uploader.GitlabConfig') as mock:
        mock_instance = mock.return_value
        mock_instance.project_id = "12345"
        mock_instance.board_id = 99
        yield mock_instance

@pytest.fixture
def mock_yaml():
    """Mocks the ruamel.yaml YAML object and its methods."""
    with patch('gemini_gitlab_workflow.gitlab_uploader.YAML') as mock_yaml_class:
        mock_yaml_instance = mock_yaml_class.return_value
        mock_yaml_instance.load.return_value = {}
        mock_yaml_instance.dump.return_value = None
        yield mock_yaml_instance

@pytest.fixture
def mock_project_map():
    """Provides a sample project map for uploading."""
    return {
        "nodes": [
            {"id": 1, "title": "Existing Epic", "labels": ["Type::Epic", "Backbone::Frontend"]},
            {"id": "NEW_101", "title": "New Story", "labels": ["Type::Story", "Backbone::Frontend"], "local_path": "story1.md"},
            {"id": "NEW_102", "title": "Another Story", "labels": ["Type::Story", "Backbone::Backend"], "local_path": "story2.md"},
            {"id": 2, "title": "Existing Backend Epic", "labels": ["Type::Epic"]} # No backbone label
        ],
        "links": [
            {"source": 1, "target": "NEW_101", "type": "contains"},
            {"source": 2, "target": "NEW_102", "type": "contains"}
        ]
    }

# --- Test Cases ---

def test_upload_happy_path_with_reorder(mock_gitlab_client, mock_config, mock_yaml, mock_project_map):
    """
    Tests the full successful workflow: label, issue creation, map update, and reordering.
    """
    # Arrange
    # Mock file I/O
    with patch("builtins.open", mock_open(read_data="---\nid: NEW_101\n---\nDescription")):
        # Mock GitLab API responses
        mock_gitlab_client.get_project_labels.return_value = []
        
        mock_story_issue = MagicMock()
        mock_story_issue.iid = 201
        mock_story_issue.id = 201
        mock_story_issue.labels = ["Type::Story", "Backbone::Frontend"]
        
        mock_another_story = MagicMock()
        mock_another_story.iid = 202
        mock_another_story.id = 202
        mock_another_story.labels = ["Type::Story", "Backbone::Backend"]

        mock_gitlab_client.create_project_issue.side_effect = [mock_story_issue, mock_another_story]

        mock_epic_issue = MagicMock()
        mock_epic_issue.id = 1
        mock_epic_issue.iid = 1
        
        mock_backend_epic = MagicMock()
        mock_backend_epic.id = 2
        mock_backend_epic.iid = 2
        mock_backend_epic.labels = ["Type::Epic"] # Starts without backbone label

        # This is the crucial mock that was missing.
        mock_gitlab_client.get_project_issues.return_value = [mock_epic_issue, mock_backend_epic]
        mock_gitlab_client.get_project_issue.side_effect = [mock_epic_issue, mock_backend_epic]

        mock_board = MagicMock()
        mock_list_frontend = MagicMock()
        mock_list_frontend.id = 1
        mock_list_frontend.label = {'name': 'Backbone::Frontend'}
        # This mock is now required for the new reorder logic
        mock_list_backend = MagicMock()
        mock_list_backend.id = 2
        mock_list_backend.label = {'name': 'Backbone::Backend'}

        mock_board.lists.list.return_value = [mock_list_frontend, mock_list_backend]
        # The client now gets the board, then gets the list from the board.
        # We need to mock the .get() call on the board's list manager.
        mock_board.lists.get.side_effect = [mock_list_frontend, mock_list_backend]
        mock_gitlab_client.get_project_board.return_value = mock_board
        
        # The uploader calls get_project_issues to get the current order
        mock_gitlab_client.get_project_issues.side_effect = [[mock_epic_issue], [mock_backend_epic]]

        # Act
        uploader = GitlabUploader(mock_config.project_id, mock_project_map)
        result = uploader.upload()

        # Assert
        assert result["status"] == "success"
        assert result["issues_created"] == 2
        assert result["project_map_updated"] is True
        assert result["stories_reordered"] == 2

        # Assert map was updated
        mock_yaml.load.assert_called_once()
        mock_yaml.dump.assert_called_once()

        # Assert that the correct, abstracted reorder function was called
        assert mock_gitlab_client.reorder_issues_in_board_list.call_count == 2
        
        # Assert epic 2 was updated with the new label
        mock_backend_epic.save.assert_called_once()
        assert "Backbone::Backend" in mock_backend_epic.labels


def test_reordering_skipped_if_board_id_is_none(mock_gitlab_client, mock_config, mock_yaml, mock_project_map):
    """
    Tests that the reordering step is skipped if no board_id is configured.
    """
    # Arrange
    mock_config.board_id = None # Disable board ID
    with patch("builtins.open", mock_open(read_data="")):
        mock_gitlab_client.get_project_labels.return_value = []
        mock_issue = MagicMock()
        mock_issue.iid = 201
        mock_gitlab_client.create_project_issue.return_value = mock_issue

        # Act
        uploader = GitlabUploader(mock_config.project_id, mock_project_map)
        result = uploader.upload()

        # Assert
        assert result["status"] == "success"
        assert result["stories_reordered"] == 0
        mock_gitlab_client.get_project_board.assert_not_called()


def test_upload_rollback_on_failure(mock_gitlab_client, mock_config, mock_yaml, mock_project_map):
    """
    Tests that created artifacts are rolled back if an API error occurs.
    """
    # Arrange
    with patch("builtins.open", mock_open(read_data="")):
        mock_gitlab_client.get_project_labels.return_value = []
        
        mock_story_issue = MagicMock()
        mock_story_issue.iid = 201
        mock_story_issue.delete = MagicMock() # Mock the delete method for rollback
        
        mock_gitlab_client.create_project_issue.side_effect = [
            mock_story_issue,
            gitlab.exceptions.GitlabError("API Failure")
        ]

        # Act
        uploader = GitlabUploader(mock_config.project_id, mock_project_map)
        result = uploader.upload()

        # Assert
        assert result["status"] == "error"
        assert "API Failure" in result["message"]

        # Verify rollback calls
        mock_story_issue.delete.assert_called_once()
        # The labels created before failure should be rolled back
        mock_gitlab_client.delete_project_label.assert_has_calls([
            call(mock_config.project_id, "Type::Story"),
            call(mock_config.project_id, "Backbone::Frontend"),
            call(mock_config.project_id, "Backbone::Backend")
        ], any_order=True)