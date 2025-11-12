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
        assert mock_gitlab_client.move_issue_in_board_list.call_count == 2
        
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


def test_create_links_only_processes_new_links(mock_gitlab_client, mock_config):
    """
    Ensures that _create_links only attempts to create links that involve a new issue.
    """
    # Arrange
    project_map_with_old_links = {
        "nodes": [
            {"id": 1, "title": "Old Epic"},
            {"id": 2, "title": "Old Story"},
            {"id": "NEW_1", "title": "New Story"},
            {"id": "NEW_2", "title": "New Epic"},
        ],
        "links": [
            # This link already exists and should be ignored
            {"source": 1, "target": 2, "type": "contains"},
            # This link is new and should be created
            {"source": 1, "target": "NEW_1", "type": "contains"},
            # This 'blocks' link is new and should create a comment
            {"source": 2, "target": "NEW_1", "type": "blocks"},
            # This link is between two new issues
            {"source": "NEW_2", "target": "NEW_1", "type": "contains"},
        ]
    }
    uploader = GitlabUploader(mock_config.project_id, project_map_with_old_links)
    # Simulate that the new issues have been created and mapped
    uploader.new_issue_id_map = {"NEW_1": 101, "NEW_2": 102}

    # Act
    uploader._create_links()

    # Assert
    # 3 links should be created: (1 -> NEW_1), (2 blocks NEW_1), (NEW_2 -> NEW_1)
    assert uploader.links_created_count == 3
    
    # Verify that create_issue_link was called for the two 'contains' links
    mock_gitlab_client.create_issue_link.assert_has_calls([
        call(mock_config.project_id, 1, 101),
        call(mock_config.project_id, 102, 101)
    ], any_order=True)
    
    # Verify that create_issue_note was called for the 'blocks' link
    mock_gitlab_client.create_issue_note.assert_called_once_with(
        mock_config.project_id, 101, {'body': 'Blocked by #2'}
    )


def test_reorder_stories_on_board_uses_correct_ids(mock_gitlab_client, mock_config):
    """
    Verifies that the reorder logic calls the new client method with the correct ID types.
    """
    # Arrange
    mock_story_issue = MagicMock()
    mock_story_issue.iid = 55  # Project-specific IID
    mock_story_issue.id = 555 # Global ID
    mock_story_issue.labels = ["Type::Story", "Backbone::Test"]

    mock_epic_issue = MagicMock()
    mock_epic_issue.iid = 11 # Project-specific IID
    mock_epic_issue.id = 111 # Global ID
    mock_epic_issue.labels = ["Type::Epic", "Backbone::Test"]

    uploader = GitlabUploader(mock_config.project_id, {})
    uploader.reorder_list = [(mock_story_issue, mock_epic_issue)]

    # Mock the board and list finding logic
    mock_board = MagicMock()
    mock_list = MagicMock()
    mock_list.label = {'name': 'Backbone::Test'}
    mock_board.lists.list.return_value = [mock_list]
    mock_gitlab_client.get_project_board.return_value = mock_board

    # Act
    uploader._reorder_stories_on_board()

    # Assert
    # Verify that the NEW, correct client function is called.
    mock_gitlab_client.move_issue_in_board_list.assert_called_once_with(
        project_id=mock_config.project_id,
        issue_iid=55,          # The IID of the issue to move
        move_before_id=111     # The GLOBAL ID of the issue to move it before
    )
    
    # Ensure the old, incorrect function is NOT called
    mock_gitlab_client.reorder_issues_in_board_list.assert_not_called()

