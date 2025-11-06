import pytest
import json
import os
from unittest.mock import MagicMock, patch

from gitlab_service import smart_sync, build_project_map, _get_issue_filepath, _generate_markdown_content, _slugify

# --- MOCK DATA --- #

@pytest.fixture
def mock_issue_backbone():
    issue = MagicMock()
    issue.iid = 100
    issue.title = "User Authentication Workflow"
    issue.state = "opened"
    issue.labels = ["Backbone::User Authentication"]
    issue.web_url = "http://gitlab.example.com/project/100"
    issue.created_at = "2025-11-01T10:00:00.000Z"
    issue.updated_at = "2025-11-05T10:00:00.000Z"
    issue.description = "Top-level workflow for user authentication."
    issue.notes.list.return_value = []
    issue.task_completion_status = {"count": 0, "completed_count": 0}
    return issue

@pytest.fixture
def mock_issue_epic():
    issue = MagicMock()
    issue.iid = 101
    issue.title = "Implement Login Feature"
    issue.state = "opened"
    issue.labels = ["Epic::Implement Login Feature", "Backbone::User Authentication"]
    issue.web_url = "http://gitlab.example.com/project/101"
    issue.created_at = "2025-11-02T11:00:00.000Z"
    issue.updated_at = "2025-11-05T11:00:00.000Z"
    issue.description = "This epic covers all stories related to user login."
    issue.notes.list.return_value = []
    issue.task_completion_status = {"count": 0, "completed_count": 0}
    return issue

@pytest.fixture
def mock_issue_story():
    issue = MagicMock()
    issue.iid = 102
    issue.title = "As a user, I can log in with email and password"
    issue.state = "opened"
    issue.labels = ["Type::Story", "Epic::Implement Login Feature", "Backbone::User Authentication"]
    issue.web_url = "http://gitlab.example.com/project/102"
    issue.created_at = "2025-11-03T12:00:00.000Z"
    issue.updated_at = "2025-11-05T12:00:00.000Z"
    issue.description = "User should be able to provide credentials and gain access."
    issue.notes.list.return_value = []
    issue.task_completion_status = {"count": 0, "completed_count": 0}
    return issue

@pytest.fixture
def mock_issue_story_with_tasks():
    issue = MagicMock()
    issue.iid = 103
    issue.title = "As a user, I can reset my password"
    issue.state = "opened"
    issue.labels = ["Type::Story", "Epic::Implement Login Feature", "Backbone::User Authentication"]
    issue.web_url = "http://gitlab.example.com/project/103"
    issue.created_at = "2025-11-04T13:00:00.000Z"
    issue.updated_at = "2025-11-05T13:00:00.000Z"
    issue.description = "Password reset flow.\n- [ ] Send reset email\n- [ ] Verify token\n- [ ] Update password"
    issue.notes.list.return_value = []
    issue.task_completion_status = {"count": 3, "completed_count": 1}
    return issue

@pytest.fixture
def mock_issue_task():
    issue = MagicMock()
    issue.iid = 104
    issue.title = "Create database migration for users table"
    issue.state = "opened"
    issue.labels = ["Type::Task", "Epic::Implement Login Feature", "Backbone::User Authentication"]
    issue.web_url = "http://gitlab.example.com/project/104"
    issue.created_at = "2025-11-05T14:00:00.000Z"
    issue.updated_at = "2025-11-05T14:00:00.000Z"
    issue.description = "Migration to add user table with email and password hash fields."
    issue.notes.list.return_value = []
    issue.task_completion_status = {"count": 0, "completed_count": 0}
    return issue

@pytest.fixture
def mock_issue_unassigned():
    issue = MagicMock()
    issue.iid = 105
    issue.title = "Random Bug Fix"
    issue.state = "opened"
    issue.labels = ["bug", "priority::high"]
    issue.web_url = "http://gitlab.example.com/project/105"
    issue.created_at = "2025-11-06T15:00:00.000Z"
    issue.updated_at = "2025-11-06T15:00:00.000Z"
    issue.description = "A critical bug that needs immediate attention."
    issue.notes.list.return_value = []
    issue.task_completion_status = {"count": 0, "completed_count": 0}
    return issue

# --- FIXTURES --- #

@pytest.fixture
def mock_gitlab_project(mocker, mock_issue_backbone, mock_issue_epic, mock_issue_story, mock_issue_story_with_tasks, mock_issue_task, mock_issue_unassigned):
    """Fixture to mock the gitlab project object and its methods."""
    mock_project = MagicMock()
    mock_project.issues.list.return_value = [
        mock_issue_backbone,
        mock_issue_epic,
        mock_issue_story,
        mock_issue_story_with_tasks,
        mock_issue_task,
        mock_issue_unassigned
    ]
    mock_project.issues.get.side_effect = lambda iid: {
        100: mock_issue_backbone,
        101: mock_issue_epic,
        102: mock_issue_story,
        103: mock_issue_story_with_tasks,
        104: mock_issue_task,
        105: mock_issue_unassigned
    }[iid]
    
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
        cache_file = mock_cache_paths
        result = smart_sync()
        assert result["status"] == "success"
        assert result["updated_count"] == 6 # All issues are new
        assert cache_file.exists()

    def test_smart_sync_no_changes(self, mock_gitlab_project, mock_cache_paths):
        cache_file = mock_cache_paths
        # Simulate all issues being up-to-date
        up_to_date_timestamps = {
            "100": "2025-11-05T10:00:00.000Z",
            "101": "2025-11-05T11:00:00.000Z",
            "102": "2025-11-05T12:00:00.000Z",
            "103": "2025-11-05T13:00:00.000Z",
            "104": "2025-11-05T14:00:00.000Z",
            "105": "2025-11-06T15:00:00.000Z",
        }
        with open(cache_file, 'w') as f:
            json.dump(up_to_date_timestamps, f)
        result = smart_sync()
        assert result["status"] == "success"
        assert result["updated_count"] == 0
        mock_gitlab_project.issues.get.assert_not_called()

    def test_smart_sync_with_updates(self, mock_gitlab_project, mock_cache_paths):
        cache_file = mock_cache_paths
        # Simulate one issue (100) being updated
        stale_timestamps = {
            "100": "2025-11-04T00:00:00.000Z", # Old timestamp
            "101": "2025-11-05T11:00:00.000Z",
            "102": "2025-11-05T12:00:00.000Z",
            "103": "2025-11-05T13:00:00.000Z",
            "104": "2025-11-05T14:00:00.000Z",
            "105": "2025-11-06T15:00:00.000Z",
        }
        with open(cache_file, 'w') as f:
            json.dump(stale_timestamps, f)
        result = smart_sync()
        assert result["status"] == "success"
        assert result["updated_count"] == 1
        mock_gitlab_project.issues.get.assert_called_once_with(100)

    def test_smart_sync_corrupted_cache(self, mock_gitlab_project, mock_cache_paths):
        cache_file = mock_cache_paths
        with open(cache_file, 'w') as f:
            f.write("this is not json")
        result = smart_sync()
        assert result["status"] == "success"
        assert result["updated_count"] == 6 # Should re-fetch all


class TestBuildProjectMap:

    @pytest.fixture
    def mock_data_dir(self, mocker, tmp_path):
        """Fixture to patch DATA_DIR to use a temporary directory."""
        data_dir_path = tmp_path / "gitlab_data"
        mocker.patch('gitlab_service.DATA_DIR', str(data_dir_path))
        return data_dir_path

    def test_build_map_creates_files_and_nodes(self, mock_gitlab_project, mock_data_dir, mock_issue_backbone, mock_issue_epic, mock_issue_story, mock_issue_story_with_tasks, mock_issue_unassigned, mock_issue_task):
        # Arrange
        # mock_gitlab_project is already configured with all issues
        # mock_data_dir ensures files are written to tmp_path

        # Act
        result = build_project_map()

        # Assert
        assert result["status"] == "success"
        # Expect 5 issues to be processed (Task is skipped)
        assert result["issues_found"] == 5

        map_data = result["map_data"]
        assert len(map_data["nodes"]) == 5
        # Check file creation for each type (except Task)
        assert (mock_data_dir / "backbones" / "user-authentication" / "user-authentication-workflow.md").exists()
        assert (mock_data_dir / "backbones" / "user-authentication" / "epics" / "implement-login-feature.md").exists()
        assert (mock_data_dir / "backbones" / "user-authentication" / "epics" / "stories" / "as-a-user-i-can-log-in-with-email-and-password.md").exists()
        assert (mock_data_dir / "backbones" / "user-authentication" / "epics" / "stories" / "as-a-user-i-can-reset-my-password.md").exists()
        assert (mock_data_dir / "_unassigned" / "random-bug-fix.md").exists()
        # Task should NOT have a file
        assert not (mock_data_dir / "backbones" / "user-authentication" / "epics" / "create-database-migration-for-users-table.md").exists()

        # Check node data for Backbone
        backbone_node = next(node for node in map_data["nodes"] if node["id"] == mock_issue_backbone.iid)
        assert backbone_node["local_path"] == os.path.join("backbones", "user-authentication", "user-authentication-workflow.md")

        # Check node data for Epic
        epic_node = next(node for node in map_data["nodes"] if node["id"] == mock_issue_epic.iid)
        assert epic_node["local_path"] == os.path.join("backbones", "user-authentication", "epics", "implement-login-feature.md")

        # Check node data for Story with tasks
        story_with_tasks_node = next(node for node in map_data["nodes"] if node["id"] == mock_issue_story_with_tasks.iid)
        assert story_with_tasks_node["local_path"] == os.path.join("backbones", "user-authentication", "epics", "stories", "as-a-user-i-can-reset-my-password.md")

    def test_build_map_parses_relationships(self, mock_gitlab_project, mock_data_dir, mock_issue_backbone, mock_issue_epic, mock_issue_story, mock_issue_story_with_tasks, mock_issue_task, mock_issue_unassigned):
        # Arrange
        # mock_issue_1.description = "This is the first issue. It is /blocked by #101"
        # mock_issue_epic.description = "This is an epic. /blocking #102"
        mock_issue_story.description = "Story description. /blocked by #101"
        mock_issue_story_with_tasks.description = "Story with tasks. /blocking #100"

        # Act
        result = build_project_map()

        # Assert
        assert result["status"] == "success"
        map_data = result["map_data"]
        assert len(map_data["links"]) == 2 # Expecting 2 links from the setup

        link1 = {"source": 101, "target": 102, "type": "blocks"} # Epic blocks Story
        link2 = {"source": 103, "target": 100, "type": "blocks"} # Story with tasks blocks Backbone
        assert link1 in map_data["links"]
        assert link2 in map_data["links"]



class TestUploadArtifactsToGitlab:

    @pytest.fixture
    def mock_gitlab_project_for_upload(self, mocker):
        """A specialized mock for testing the upload process."""
        mock_project = MagicMock()
        
        # Mock existing labels
        mock_label_existing = MagicMock()
        mock_label_existing.name = "Type::Story"
        mock_project.labels.list.return_value = [mock_label_existing]

        # Mock issue creation - return a mock issue with a new iid
        def create_issue_side_effect(data):
            mock_issue = MagicMock()
            # Simulate GitLab assigning a new IID
            mock_issue.iid = 1000 + len(mock_project.issues.create.call_args_list)
            mock_issue.title = data['title']
            return mock_issue
        mock_project.issues.create.side_effect = create_issue_side_effect

        # Mock getting an issue for adding notes
        mock_existing_issue_for_note = MagicMock()
        mock_existing_issue_for_note.iid = 50
        mock_project.issues.get.return_value = mock_existing_issue_for_note

        mock_gl_client = MagicMock()
        mock_gl_client.projects.get.return_value = mock_project
        mocker.patch('gitlab_service.get_gitlab_client', return_value=mock_gl_client)
        
        return mock_project

    def test_upload_artifacts_in_correct_order(self, mock_gitlab_project_for_upload):
        # Arrange
        from gitlab_service import upload_artifacts_to_gitlab
        from unittest.mock import call

        project_map = {
            "nodes": [
                {
                    "id": "NEW_1",
                    "title": "Implement New Feature",
                    "labels": ["Type::Story", "Epic::New Epic"], # One existing, one new label
                    "description": "This is a new feature."
                },
                {
                    "id": "NEW_2",
                    "title": "Fix Critical Bug",
                    "labels": ["Type::Bug"], # Another new label
                    "description": "A critical bug to be fixed."
                }
            ],
            "links": [
                # A new issue blocks an existing issue
                {"source": "NEW_1", "target": 50, "type": "blocks"} 
            ]
        }

        # Act
        result = upload_artifacts_to_gitlab(project_map)

        # Assert
        assert result["status"] == "success"
        assert result["labels_created"] == 2
        assert result["issues_created"] == 2
        assert result["links_created"] == 1

        # 1. Verify Label creation
        # It should first list existing labels
        mock_gitlab_project_for_upload.labels.list.assert_called_once()
        
        # It should create the two new labels, but not the existing one
        expected_label_calls = [
            call({'name': 'Epic::New Epic', 'color': '#F0AD4E'}), # Default color
            call({'name': 'Type::Bug', 'color': '#F0AD4E'})
        ]
        mock_gitlab_project_for_upload.labels.create.assert_has_calls(expected_label_calls, any_order=True)
        assert mock_gitlab_project_for_upload.labels.create.call_count == 2

        # 2. Verify Issue creation
        expected_issue_calls = [
            call({'title': 'Implement New Feature', 'labels': ['Type::Story', 'Epic::New Epic'], 'description': 'This is a new feature.'}),
            call({'title': 'Fix Critical Bug', 'labels': ['Type::Bug'], 'description': 'A critical bug to be fixed.'})
        ]
        mock_gitlab_project_for_upload.issues.create.assert_has_calls(expected_issue_calls, any_order=True)
        assert mock_gitlab_project_for_upload.issues.create.call_count == 2

        # 3. Verify Link (Note) creation
        # It should get the existing issue to add a note to it
        mock_gitlab_project_for_upload.issues.get.assert_called_once_with(50)
        
        # It should create a note on the issue returned by get()
        mock_issue_for_note = mock_gitlab_project_for_upload.issues.get.return_value
        # The IID of the new issue is simulated as 1001
        mock_issue_for_note.notes.create.assert_called_once_with({'body': '/blocked by #1001'})
