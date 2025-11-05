import pytest
import json
from unittest.mock import MagicMock, patch

from gitlab_service import smart_sync

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
def mock_gitlab_project(mocker, mock_issue_1, mock_issue_2):
    """Fixture to mock the gitlab project object and its methods."""
    mock_project = MagicMock()
    mock_project.issues.list.return_value = [mock_issue_1, mock_issue_2]
    mock_project.issues.get.side_effect = lambda iid: {1: mock_issue_1, 2: mock_issue_2}[iid]
    
    mock_gl_client = MagicMock()
    mock_gl_client.projects.get.return_value = mock_project
    mocker.patch('gitlab_service.get_gitlab_client', return_value=mock_gl_client)
    
    return mock_project

@pytest.fixture
def mock_cache_paths(mocker, tmp_path):
    """Fixture to patch cache path constants to use a temporary directory."""
    cache_file_path = tmp_path / "timestamps.json"
    mocker.patch('gitlab_service.CACHE_DIR', str(tmp_path))
    mocker.patch('gitlab_service.TIMESTAMPS_CACHE_PATH', str(cache_file_path))
    return cache_file_path


class TestSmartSyncLogic:

    def test_smart_sync_first_run(self, mock_gitlab_project, mock_cache_paths):
        """Test smart_sync logic when no cache file exists."""
        # Arrange
        cache_file = mock_cache_paths
        
        # Act
        result = smart_sync()

        # Assert
        assert result["status"] == "success"
        assert result["updated_count"] == 2
        assert len(result["updated_issues"]) == 2
        assert result["updated_issues"][0]["title"] == "First Issue"

        mock_gitlab_project.issues.list.assert_called_once()
        assert mock_gitlab_project.issues.get.call_count == 2

        assert cache_file.exists()
        with open(cache_file, 'r') as f:
            cached_data = json.load(f)
        assert cached_data == {
            "1": "2025-11-05T10:00:00.000Z",
            "2": "2025-11-05T11:00:00.000Z"
        }

    def test_smart_sync_no_changes(self, mock_gitlab_project, mock_cache_paths):
        """Test smart_sync logic when the cache is up to date."""
        # Arrange
        cache_file = mock_cache_paths
        with open(cache_file, 'w') as f:
            json.dump({"1": "2025-11-05T10:00:00.000Z", "2": "2025-11-05T11:00:00.000Z"}, f)

        # Act
        result = smart_sync()

        # Assert
        assert result["status"] == "success"
        assert result["updated_count"] == 0
        mock_gitlab_project.issues.get.assert_not_called()

    def test_smart_sync_with_updates(self, mock_gitlab_project, mock_cache_paths):
        """Test smart_sync logic when one issue has been updated."""
        # Arrange
        cache_file = mock_cache_paths
        with open(cache_file, 'w') as f:
            json.dump({"1": "2025-11-04T00:00:00.000Z", "2": "2025-11-05T11:00:00.000Z"}, f)

        # Act
        result = smart_sync()

        # Assert
        assert result["status"] == "success"
        assert result["updated_count"] == 1
        assert result["updated_issues"][0]["iid"] == 1
        mock_gitlab_project.issues.get.assert_called_once_with(1)

    def test_smart_sync_corrupted_cache(self, mock_gitlab_project, mock_cache_paths):
        """Test smart_sync logic with a corrupted cache file."""
        # Arrange
        cache_file = mock_cache_paths
        with open(cache_file, 'w') as f:
            f.write("this is not json")

        # Act
        result = smart_sync()

        # Assert (should behave like a first run)
        assert result["status"] == "success"
        assert result["updated_count"] == 2