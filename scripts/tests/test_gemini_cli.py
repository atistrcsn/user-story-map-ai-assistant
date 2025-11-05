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
        result = runner.invoke(app, ["create", "test feature"])

        # Assert
        assert result.exit_code == 0
        assert "Project is up-to-date. Total issues: 120." in result.stdout
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
        result = runner.invoke(app, ["create", "test feature"])

        # Assert
        assert result.exit_code == 0
        assert "Sync complete. Found 2 new or updated issues:" in result.stdout
        assert "- Fetched updated issue #1: First Issue" in result.stdout
        assert "- Fetched updated issue #2: Second Issue" in result.stdout
        mock_gitlab_client.assert_called_once()

    def test_sync_error(self, mock_gitlab_client):
        """Test the CLI output when smart_sync reports an error."""
        # Arrange
        mock_gitlab_client.return_value = {
            "status": "error",
            "message": "Invalid GitLab token"
        }

        # Act
        result = runner.invoke(app, ["create", "test feature"])

        # Assert
        assert result.exit_code == 1
        assert "Error during sync: Invalid GitLab token" in result.stdout
        mock_gitlab_client.assert_called_once()
