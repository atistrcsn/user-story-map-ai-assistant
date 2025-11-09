import pytest
import json
import os
from unittest.mock import MagicMock, patch, call

from gemini_gitlab_workflow.gitlab_service import smart_sync, build_project_map, upload_artifacts_to_gitlab

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
    issue.labels = ["Type::Epic", "Backbone::User Authentication"]
    issue.web_url = "http://gitlab.example.com/project/101"
    issue.created_at = "2025-11-02T11:00:00.000Z"
    issue.updated_at = "2025-11-05T11:00:00.000Z"
    issue.description = "This epic covers all stories related to user login."
    issue.notes.list.return_value = []
    issue.task_completion_status = {"count": 0, "completed_count": 0}
    # For link testing
    issue.links.list.return_value = []
    return issue

@pytest.fixture
def mock_issue_story():
    issue = MagicMock()
    issue.iid = 102
    issue.title = "As a user, I can log in with email and password"
    issue.state = "opened"
    issue.labels = ["Type::Story", "Backbone::User Authentication"]
    issue.web_url = "http://gitlab.example.com/project/102"
    issue.created_at = "2025-11-03T12:00:00.000Z"
    issue.updated_at = "2025-11-05T12:00:00.000Z"
    issue.description = "User should be able to provide credentials and gain access."
    issue.notes.list.return_value = []
    issue.task_completion_status = {"count": 0, "completed_count": 0}
    # For link testing
    issue.links.list.return_value = []
    return issue

@pytest.fixture
def mock_issue_story_with_tasks():
    issue = MagicMock()
    issue.iid = 103
    issue.title = "As a user, I can reset my password"
    issue.state = "opened"
    issue.labels = ["Type::Story", "Backbone::User Authentication"]
    issue.web_url = "http://gitlab.example.com/project/103"
    issue.created_at = "2025-11-04T13:00:00.000Z"
    issue.updated_at = "2025-11-05T13:00:00.000Z"
    issue.description = "Password reset flow.\n- [ ] Send reset email\n- [ ] Verify token\n- [ ] Update password"
    issue.notes.list.return_value = []
    issue.task_completion_status = {"count": 3, "completed_count": 1}
    # For link testing
    issue.links.list.return_value = []
    return issue

@pytest.fixture
def mock_issue_task():
    issue = MagicMock()
    issue.iid = 104
    issue.title = "Create database migration for users table"
    issue.state = "opened"
    issue.labels = ["Type::Task", "Backbone::User Authentication"]
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
    mocker.patch('gemini_gitlab_workflow.gitlab_service.get_gitlab_client', return_value=mock_gl_client)
    
    return mock_project

@pytest.fixture
def mock_cache_paths(mocker, tmp_path):
    """Fixture to patch cache path constants to use a temporary directory."""
    cache_file_path = tmp_path / "timestamps.json"
    mocker.patch('gemini_gitlab_workflow.gitlab_service.CACHE_DIR', str(tmp_path))
    mocker.patch('gemini_gitlab_workflow.gitlab_service.TIMESTAMPS_CACHE_PATH', str(cache_file_path))
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


# --- New Fixtures for Link Testing ---
@pytest.fixture
def mock_issue_epic_linked():
    issue = MagicMock()
    issue.iid = 201
    issue.title = "New Epic for Linking"
    issue.state = "opened"
    issue.labels = ["Type::Epic", "Backbone::Test Backbone"]
    issue.web_url = "http://gitlab.example.com/project/201"
    issue.created_at = "2025-11-07T10:00:00.000Z"
    issue.updated_at = "2025-11-07T10:00:00.000Z"
    issue.description = "Epic for link testing."
    issue.notes.list.return_value = []
    issue.task_completion_status = {"count": 0, "completed_count": 0}
    issue.links.list.return_value = []
    return issue

@pytest.fixture
def mock_issue_story_linked(mock_issue_epic_linked):
    issue = MagicMock()
    issue.iid = 202
    issue.title = "Story Linked to Epic"
    issue.state = "opened"
    issue.labels = ["Type::Story", "Backbone::Test Backbone"]
    issue.web_url = "http://gitlab.example.com/project/202"
    issue.created_at = "2025-11-07T11:00:00.000Z"
    issue.updated_at = "2025-11-07T11:00:00.000Z"
    issue.description = "This story should be under the linked epic."
    issue.notes.list.return_value = []
    issue.task_completion_status = {"count": 0, "completed_count": 0}
    
    # This is the crucial part: mock the link
    mock_link = MagicMock()
    mock_link.iid = mock_issue_epic_linked.iid
    issue.links.list.return_value = [mock_link]
    return issue


class TestBuildProjectMap:

    def test_build_map_creates_files_and_nodes(self, mock_gitlab_project, tmp_path):
        # Act
        result = build_project_map()

        # Assert
        assert result["status"] == "success"
        assert result["issues_found"] == 5 # Tasks are no longer standalone files
        map_data = result["map_data"]
        assert len(map_data["nodes"]) == 5
        
        # Check that all non-task issues have a file
        # Note: We check against tmp_path now, which is automatically provided by pytest
        data_dir = tmp_path / "gitlab_data"
        assert (data_dir / "backbones" / "user-authentication" / "user-authentication-workflow.md").exists()
        assert not (data_dir / "_unassigned" / "create-database-migration-for-users-table.md").exists() # Task should not have a file
        assert (data_dir / "_unassigned" / "random-bug-fix.md").exists()

    def test_build_map_parses_relationships(self, mock_gitlab_project, mock_issue_story, mock_issue_story_with_tasks):
        # Arrange
        mock_issue_story.description = "Story description. /blocked by #101"
        mock_issue_story_with_tasks.description = "Story with tasks. /blocking #100"

        # Act
        result = build_project_map()

        # Assert
        assert result["status"] == "success"
        map_data = result["map_data"]
        assert len(map_data["links"]) == 2

        link1 = {"source": 101, "target": 102, "type": "blocks"}
        link2 = {"source": 103, "target": 100, "type": "blocks"}
        assert link1 in map_data["links"]
        assert link2 in map_data["links"]

    def test_build_map_creates_hierarchy_from_issue_links(self, mocker, tmp_path, mock_issue_epic_linked, mock_issue_story_linked):
        # Arrange
        mock_project = MagicMock()
        mock_project.issues.list.return_value = [mock_issue_epic_linked, mock_issue_story_linked]
        
        # Need to handle .get() for both issues
        def get_issue_side_effect(iid):
            if iid == mock_issue_epic_linked.iid:
                return mock_issue_epic_linked
            if iid == mock_issue_story_linked.iid:
                return mock_issue_story_linked
            raise ValueError(f"Issue with iid {iid} not found in mock")
        mock_project.issues.get.side_effect = get_issue_side_effect

        mock_gl_client = MagicMock()
        mock_gl_client.projects.get.return_value = mock_project
        mocker.patch('gemini_gitlab_workflow.gitlab_service.get_gitlab_client', return_value=mock_gl_client)
        
        # Act
        result = build_project_map()

        # Assert
        assert result["status"] == "success"
        map_data = result["map_data"]
        
        # 1. Check if the story file is in the epic's directory
        data_dir = tmp_path / "gitlab_data"
        epic_dir_name = "new-epic-for-linking"
        story_file_name = "story-story-linked-to-epic.md"
        expected_story_path = os.path.join("backbones", "test-backbone", epic_dir_name, story_file_name)
        
        story_node = next(node for node in map_data["nodes"] if node["id"] == mock_issue_story_linked.iid)
        assert story_node["local_path"] == expected_story_path
        assert (data_dir / expected_story_path).exists()

        # 2. Check if the 'contains' link was created in the map
        expected_link = {"source": mock_issue_epic_linked.iid, "target": mock_issue_story_linked.iid, "type": "contains"}
        assert expected_link in map_data["links"]


class TestUploadArtifactsToGitlab:

    @pytest.fixture
    def mock_gitlab_project_for_upload(self, mocker):
        """A specialized mock for testing the upload process."""
        mock_project = MagicMock()
        mock_label_existing = MagicMock()
        mock_label_existing.name = "Type::Story"
        mock_project.labels.list.return_value = [mock_label_existing]

        def create_issue_side_effect(data):
            mock_issue = MagicMock()
            mock_issue.iid = 1000 + len(mock_project.issues.create.call_args_list)
            mock_issue.title = data['title']
            return mock_issue
        mock_project.issues.create.side_effect = create_issue_side_effect

        mock_existing_issue_for_note = MagicMock()
        mock_existing_issue_for_note.iid = 50
        mock_project.issues.get.return_value = mock_existing_issue_for_note

        mock_gl_client = MagicMock()
        mock_gl_client.projects.get.return_value = mock_project
        mocker.patch('gemini_gitlab_workflow.gitlab_service.get_gitlab_client', return_value=mock_gl_client)
        
        return mock_project

    def test_upload_artifacts_in_correct_order(self, mock_gitlab_project_for_upload):
        # Arrange
        project_map = {
            "nodes": [
                {"id": "NEW_1", "title": "Implement New Feature", "labels": ["Type::Story"], "description": "This is a new feature."},
                {"id": "NEW_2", "title": "Fix Critical Bug", "labels": ["Type::Bug"], "description": "A critical bug to be fixed."}
            ],
            "links": [{"source": "NEW_1", "target": 50, "type": "blocks"}]
        }

        # Act
        result = upload_artifacts_to_gitlab(project_map)

        # Assert
        assert result["status"] == "success"
        assert result["labels_created"] == 1
        assert result["issues_created"] == 2
        assert result["notes_with_links_created"] == 1

        mock_gitlab_project_for_upload.labels.list.assert_called_once()
        expected_label_calls = [call({'name': 'Type::Bug', 'color': '#F0AD4E'})]
        mock_gitlab_project_for_upload.labels.create.assert_has_calls(expected_label_calls, any_order=True)

        expected_issue_calls = [
            call({'title': 'Implement New Feature', 'labels': ['Type::Story'], 'description': 'This is a new feature.'}),
            call({'title': 'Fix Critical Bug', 'labels': ['Type::Bug'], 'description': 'A critical bug to be fixed.'})
        ]
        mock_gitlab_project_for_upload.issues.create.assert_has_calls(expected_issue_calls, any_order=True)

        mock_gitlab_project_for_upload.issues.get.assert_called_once_with(50)
        mock_issue_for_note = mock_gitlab_project_for_upload.issues.get.return_value
        mock_issue_for_note.notes.create.assert_called_once_with({'body': '/blocked by #1001'})

    def test_upload_artifacts_creates_issue_links_for_contains_type(self, mock_gitlab_project_for_upload):
        # Arrange
        project_map = {
            "nodes": [
                {"id": "NEW_EPIC_1", "title": "My New Epic", "labels": ["Type::Epic"], "description": ""},
                {"id": "NEW_STORY_1", "title": "My New Story", "labels": ["Type::Story"], "description": ""}
            ],
            "links": [{"source": "NEW_EPIC_1", "target": "NEW_STORY_1", "type": "contains"}]
        }

        # Mock the created issues
        mock_epic = MagicMock()
        mock_epic.iid = 2001
        mock_story = MagicMock()
        mock_story.iid = 2002

        # Adjust side effects for issue creation and retrieval
        mock_gitlab_project_for_upload.issues.create.side_effect = [mock_epic, mock_story]
        mock_gitlab_project_for_upload.issues.get.return_value = mock_epic

        # Act
        result = upload_artifacts_to_gitlab(project_map)

        # Assert
        assert result["status"] == "success"
        assert result["issue_links_created"] == 1

        # 1. Verify that the epic issue was retrieved to create the link from it
        mock_gitlab_project_for_upload.issues.get.assert_called_once_with(mock_epic.iid)

        # 2. Verify that the links.create method was called on the epic with the story's iid
        mock_epic.links.create.assert_called_once_with({
            'target_project_id': mock_gitlab_project_for_upload.id,
            'target_issue_iid': mock_story.iid
        })

    def test_upload_artifacts_rollback_on_issue_failure(self, mock_gitlab_project_for_upload):
        # Arrange
        project_map = {
            "nodes": [
                {"id": "NEW_1", "title": "Implement New Feature", "labels": ["Type::Story", "NewLabel"], "description": "This is a new feature."}
            ],
            "links": []
        }

        # Simulate issue creation failure
        mock_gitlab_project_for_upload.issues.create.side_effect = Exception("Simulated issue creation failure")

        # Act
        result = upload_artifacts_to_gitlab(project_map)

        # Assert
        assert result["status"] == "error"
        assert "Simulated issue creation failure" in result["message"]
        
        # Verify label creation attempt
        expected_label_create_calls = [call({'name': 'NewLabel', 'color': '#F0AD4E'})]
        mock_gitlab_project_for_upload.labels.create.assert_has_calls(expected_label_create_calls, any_order=True)

        # Verify label deletion (rollback)
        expected_label_delete_calls = [call('NewLabel')]
        mock_gitlab_project_for_upload.labels.delete.assert_has_calls(expected_label_delete_calls, any_order=True)
        
        # Verify issue creation attempt
        mock_gitlab_project_for_upload.issues.create.assert_called_once()

    def test_upload_artifacts_ignores_existing_contains_links(self, mock_gitlab_project_for_upload):
        """
        Tests that the upload logic correctly ignores 'contains' links that
        already exist between non-NEW issues, preventing redundant API calls.
        """
        # Arrange
        project_map = {
            "nodes": [
                # A new issue is needed to trigger the upload process
                {"id": "NEW_1", "title": "A new story", "labels": ["Type::Story"], "description": "desc"}
            ],
            "links": [
                # This link already exists and should be ignored
                {"source": 101, "target": 102, "type": "contains"}
            ]
        }

        # Mock the .get call that would be used for link creation
        mock_existing_epic = MagicMock()
        mock_gitlab_project_for_upload.issues.get.return_value = mock_existing_epic

        # Act
        result = upload_artifacts_to_gitlab(project_map)

        # Assert
        assert result["status"] == "success"
        assert result["issue_links_created"] == 0 # No NEW links were in the map

        # Verify that the new issue was created
        mock_gitlab_project_for_upload.issues.create.assert_called_once()

        # CRITICAL: Verify that no attempt was made to create a link for the existing relationship
        mock_existing_epic.links.create.assert_not_called()


class TestGitlabServiceErrors:

    def test_functions_fail_without_env_vars(self, monkeypatch):
        """
        Tests that service functions return an error status when GitLab
        environment variables are not set.
        """
        # Arrange
        # Unset environment variables for the duration of this test
        monkeypatch.delenv("GITLAB_URL", raising=False)
        monkeypatch.delenv("GITLAB_PRIVATE_TOKEN", raising=False)
        monkeypatch.delenv("GITLAB_PROJECT_ID", raising=False)

        # Act
        sync_result = smart_sync()
        build_map_result = build_project_map()
        upload_result = upload_artifacts_to_gitlab({})

        # Assert
        assert sync_result["status"] == "error"
        assert "GITLAB_URL and GITLAB_PRIVATE_TOKEN must be set" in sync_result["message"]

        assert build_map_result["status"] == "error"
        assert "GITLAB_URL and GITLAB_PRIVATE_TOKEN must be set" in build_map_result["message"]
        
        assert upload_result["status"] == "error"
        assert "GITLAB_URL and GITLAB_PRIVATE_TOKEN must be set" in upload_result["message"]
