import pytest
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
