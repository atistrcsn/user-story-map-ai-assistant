import pytest
import typer
from typer.testing import CliRunner
import os
import json
from unittest.mock import MagicMock

# The CLI app to be tested
from gemini_cli import app
# The service layer to be mocked
import gitlab_service

runner = CliRunner()

# --- MOCK DATA --- #

@pytest.fixture
def mock_issue_1():
    issue = MagicMock()
    issue.iid = 1
    issue.title = "First Issue"
    issue.updated_at = "2025-11-05T10:00:00.000Z"
    return issue

@pytest.fixture
def mock_issue_2():
    issue = MagicMock()
    issue.iid = 2
    issue.title = "Second Issue"
    issue.updated_at = "2025-11-05T11:00:00.000Z"
    return issue

# --- FIXTURES --- #

@pytest.fixture
def mock_gitlab_client(mocker, mock_issue_1, mock_issue_2):
    """Fixture to mock the entire gitlab_service module and its functions."""
    # This fixture now mocks the service function, not the raw gitlab client
    mock_smart_sync = mocker.patch('gitlab_service.smart_sync')
    
    # Mock AI service calls to prevent actual API calls during CLI tests
    mocker.patch('ai_service.get_relevant_context_files', return_value=[])
    mocker.patch('ai_service.generate_implementation_plan', return_value={
        "proposed_issues": [
            {"id": "NEW_1", "title": "Mock Story", "description": "Mock description.", "labels": ["Type::Story"], "dependencies": {}}
        ]
    })
    mocker.patch('typer.confirm', return_value=True)
    mocker.patch('gitlab_service.build_project_map', return_value={
        "status": "success",
        "map_data": {"nodes": [], "links": []},
        "issues_found": 0
    })
    return mock_smart_sync


class TestCreateFeature:

    def test_sync_success_no_updates(self, mock_gitlab_client):
        """Test the CLI output when smart_sync reports no updates."""
        # Arrange
        mock_gitlab_client.return_value = {
            "status": "success",
            "updated_count": 0,
            "total_issues": 120
        }

        # Act
        result = runner.invoke(app, ["create-feature", "test feature"])

        # Assert
        assert result.exit_code == 0
        mock_gitlab_client.assert_called_once()

    def test_sync_success_with_updates(self, mock_gitlab_client):
        """Test the CLI output when smart_sync reports updates."""
        # Arrange
        mock_gitlab_client.return_value = {
            "status": "success",
            "updated_count": 2,
            "updated_issues": [
                {"iid": 1, "title": "First Issue"},
                {"iid": 2, "title": "Second Issue"}
            ],
            "total_issues": 2
        }

        # Act
        result = runner.invoke(app, ["create-feature", "test feature"])

        # Assert
        assert result.exit_code == 0
        mock_gitlab_client.assert_called_once()

    def test_sync_error(self, mock_gitlab_client, mocker):
        """Test the CLI output when smart_sync reports an error."""
        # Arrange
        mock_gitlab_client.return_value = {
            "status": "error",
            "message": "Invalid GitLab token"
        }
        # Ensure build_project_map also returns an error to trigger the exit
        mocker.patch('gitlab_service.build_project_map', return_value={
            "status": "error",
            "message": "Build map error"
        })

        # Act
        result = runner.invoke(app, ["create-feature", "test feature"])

        # Assert
        assert result.exit_code == 1
        mock_gitlab_client.assert_called_once()

    def test_create_feature_aborted_by_user(self, mock_gitlab_client, mocker):
        """
        Tests that the workflow correctly stops if the user does not approve the plan.
        """
        # Arrange
        # Mock typer.confirm to raise Abort, simulating the behavior of abort=True
        mocker.patch('typer.confirm', side_effect=typer.Abort)
        
        # Mock the function that would be called after approval to check it's NOT called
        mock_generate_files = mocker.patch('gemini_cli._generate_local_files')

        # Act
        result = runner.invoke(app, ["create-feature", "test feature"])

        # Assert
        # typer.confirm with abort=True raises Abort, which results in exit code 1
        assert result.exit_code == 1
        
        # Verify that the file generation was never triggered
        mock_generate_files.assert_not_called()


class TestGenerateLocalFiles:

    @pytest.fixture
    def mock_ai_plan_for_linking(self):
        """Provides a mock AI plan with a new epic, a story for it, and a dependent story."""
        return {
            "proposed_issues": [
                {
                    "id": "NEW_EPIC_1",
                    "title": "My New Test Epic",
                    "labels": ["Type::Epic", "Epic::My New Test Epic", "Backbone::Test"],
                    "description": "This is a new test epic."
                },
                {
                    "id": "NEW_STORY_1",
                    "title": "First Story for Epic",
                    "labels": ["Type::Story", "Epic::My New Test Epic", "Backbone::Test"],
                    "description": "This story belongs to the new epic."
                },
                {
                    "id": "NEW_STORY_2",
                    "title": "Second Story, blocked by first",
                    "labels": ["Type::Story", "Epic::My New Test Epic", "Backbone::Test"],
                    "description": "This story is blocked by the first one.",
                    "dependencies": {
                        "is_blocked_by": ["NEW_STORY_1"]
                    }
                }
            ]
        }

    def test_generate_local_files_creates_links_and_descriptions(self, mock_ai_plan_for_linking, mocker, tmp_path):
        """
        Tests that _generate_local_files correctly creates 'contains' and 'blocks' 
        links, and also correctly populates the 'description' field for new nodes
        in the project_map.yaml.
        """
        # Arrange
        from gemini_cli import _generate_local_files, PROJECT_MAP_PATH
        from rich.console import Console
        import yaml

        console = Console()

        # Mock the initial project_map.yaml to be empty
        with open(PROJECT_MAP_PATH, 'w') as f:
            yaml.dump({"nodes": [], "links": []}, f)

        # Act
        _generate_local_files(mock_ai_plan_for_linking, console)

        # Assert
        assert os.path.exists(PROJECT_MAP_PATH)
        with open(PROJECT_MAP_PATH, 'r') as f:
            project_map = yaml.safe_load(f)

        # --- Assertions for Links ---
        links = project_map.get("links", [])
        assert len(links) == 3
        expected_contains_link_1 = {'source': 'NEW_EPIC_1', 'target': 'NEW_STORY_1', 'type': 'contains'}
        expected_contains_link_2 = {'source': 'NEW_EPIC_1', 'target': 'NEW_STORY_2', 'type': 'contains'}
        expected_blocks_link = {'source': 'NEW_STORY_1', 'target': 'NEW_STORY_2', 'type': 'blocks'}
        assert expected_contains_link_1 in links
        assert expected_contains_link_2 in links
        assert expected_blocks_link in links

        # --- Assertions for Node Descriptions ---
        nodes = project_map.get("nodes", [])
        assert len(nodes) == 3
        
        # Create a map of nodes by their ID for easy lookup
        nodes_by_id = {node['id']: node for node in nodes}
        
        # Verify each new node has the correct description from the plan
        for issue_from_plan in mock_ai_plan_for_linking['proposed_issues']:
            temp_id = issue_from_plan['id']
            assert temp_id in nodes_by_id
            
            node_in_map = nodes_by_id[temp_id]
            assert 'description' in node_in_map
            assert node_in_map['description'] == issue_from_plan['description']


class TestUploadStoryMap:

    def test_upload_story_map_no_file(self):
        """
        Tests that the 'upload story-map' command fails gracefully with an error
        message if the project_map.yaml file does not exist.
        """
        # Arrange
        # The isolated_filesystem fixture ensures no project_map.yaml exists yet

        # Act
        result = runner.invoke(app, ["upload", "story-map"])

        # Assert
        assert result.exit_code == 1
        assert "not found" in result.stdout
        assert "Please generate a story map first" in result.stdout
