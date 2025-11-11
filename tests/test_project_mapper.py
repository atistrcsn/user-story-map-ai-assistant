import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path

from gemini_gitlab_workflow.project_mapper import build_project_map

# --- Mocks and Fixtures ---

@pytest.fixture
def mock_gitlab_client():
    """Mocks the gitlab_client module."""
    with patch('gemini_gitlab_workflow.project_mapper.gitlab_client') as mock:
        yield mock

@pytest.fixture
def mock_file_system_repo():
    """Mocks the file_system_repo module."""
    with patch('gemini_gitlab_workflow.project_mapper.file_system_repo') as mock:
        # Provide a default return value for _slugify to avoid errors
        mock._slugify.side_effect = lambda text: text.lower().replace(' ', '-')
        yield mock

@pytest.fixture
def mock_issues():
    """Provides a list of mock GitLab issue objects."""
    epic = MagicMock()
    epic.iid = 1
    epic.title = "My Epic"
    epic.labels = ["Type::Epic", "Backbone::Core"]
    epic.description = ""

    story1 = MagicMock()
    story1.iid = 2
    story1.title = "My Story 1"
    story1.labels = ["Type::Story", "Backbone::Core"]
    story1.description = "/blocking #3"

    story2 = MagicMock()
    story2.iid = 3
    story2.title = "My Story 2"
    story2.labels = ["Type::Story"]
    story2.description = ""

    return [epic, story1, story2]

# --- Tests ---

def test_build_project_map_happy_path(mock_gitlab_client, mock_file_system_repo, mock_issues):
    # Arrange
    mock_gitlab_client.get_project_issues.return_value = mock_issues
    
    # Mock the links for story1 to be linked to the epic
    mock_link = MagicMock()
    mock_link.iid = 1 # Epic's iid
    mock_gitlab_client.get_issue_links.return_value = [mock_link]
    mock_gitlab_client.get_issue_notes.return_value = []

    # Mock file path generation
    mock_file_system_repo.get_issue_filepath.side_effect = [
        Path("backbones/core/my-epic/epic.md"), # for epic
        Path("backbones/core/story-my-story-1.md"), # for story1 (initial path)
        Path("_unassigned/story-my-story-2.md"), # for story2
    ]

    # Act
    result = build_project_map("123")

    # Assert
    assert result["status"] == "success"
    assert result["issues_found"] == 3
    
    # Verify GitLab client calls
    mock_gitlab_client.get_project_issues.assert_called_once_with("123", all=True)
    # Called for story1 and story2
    assert mock_gitlab_client.get_issue_links.call_count == 2 

    # Verify File System Repo calls
    assert mock_file_system_repo.write_issue_file.call_count == 3
    mock_file_system_repo.write_project_map.assert_called_once()

    # Check that the story is placed under the epic path
    # The final call for story1 should have the correct, nested path
    final_story1_path_call = call(Path("backbones/core/my-epic/story-my-story-1.md"), mock_issues[1])
    mock_file_system_repo.write_issue_file.assert_has_calls([final_story1_path_call], any_order=True)

    # Check link creation
    map_data = result["map_data"]
    assert {"source": 1, "target": 2, "type": "contains"} in map_data["links"]
    assert {"source": 2, "target": 3, "type": "blocks"} in map_data["links"]

def test_build_project_map_api_error(mock_gitlab_client, mock_file_system_repo):
    # Arrange
    mock_gitlab_client.get_project_issues.side_effect = ConnectionError("API is down")

    # Act
    result = build_project_map("123")

    # Assert
    assert result["status"] == "error"
    assert "API is down" in result["message"]
    mock_file_system_repo.write_project_map.assert_not_called()
