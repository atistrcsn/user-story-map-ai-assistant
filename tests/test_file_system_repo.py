import pytest
import yaml
import json
from pathlib import Path

from gemini_gitlab_workflow.file_system_repo import (
    _slugify,
    get_issue_filepath,
    _generate_markdown_content,
    write_issue_file,
    write_project_map,
    read_timestamps_cache,
    write_timestamps_cache,
)
from unittest.mock import MagicMock

# --- Fixtures ---

@pytest.fixture
def mock_issue():
    """A mock GitLab issue object."""
    issue = MagicMock()
    issue.iid = 123
    issue.title = "Test Issue: Special Chars & Spaces"
    issue.state = "opened"
    issue.labels = ["Type::Story", "Backbone::Core Features"]
    issue.web_url = "http://gitlab.example.com/project/123"
    issue.created_at = "2025-01-01T00:00:00.000Z"
    issue.updated_at = "2025-01-02T00:00:00.000Z"
    issue.description = "This is a test description."
    issue.task_completion_status = {"count": 2, "completed_count": 1}
    return issue

@pytest.fixture
def mock_config_paths(mocker, tmp_path):
    """Mocks the config paths to use a temporary directory."""
    mock_data_dir = tmp_path / "gitlab_data"
    mock_cache_dir = tmp_path / ".gemini_cache"
    mock_project_map_path = tmp_path / "project_map.yaml"
    mock_timestamps_path = mock_cache_dir / "timestamps.json"

    mocker.patch('gemini_gitlab_workflow.config.DATA_DIR', mock_data_dir)
    mocker.patch('gemini_gitlab_workflow.config.CACHE_DIR', mock_cache_dir)
    mocker.patch('gemini_gitlab_workflow.config.PROJECT_MAP_PATH', mock_project_map_path)
    mocker.patch('gemini_gitlab_workflow.config.TIMESTAMPS_CACHE_PATH', mock_timestamps_path)
    
    return {
        "data_dir": mock_data_dir,
        "cache_dir": mock_cache_dir,
        "project_map_path": mock_project_map_path,
        "timestamps_path": mock_timestamps_path,
    }


# --- Tests ---

def test_slugify():
    assert _slugify("Hello World!") == "hello-world"
    assert _slugify("  Leading/Trailing Spaces  ") == "leading-trailing-spaces"
    assert _slugify("Multiple---dashes") == "multiple-dashes"
    assert _slugify("UPPERCASE") == "uppercase"

@pytest.mark.parametrize("title, labels, expected_path", [
    ("My Epic", ["Type::Epic", "Backbone::Alpha"], Path("backbones/alpha/my-epic/epic.md")),
    ("My Story", ["Type::Story", "Backbone::Alpha"], Path("backbones/alpha/story-my-story.md")),
    ("Unassigned Story", ["Type::Story"], Path("_unassigned/story-unassigned-story.md")),
    ("A Task", ["Type::Task"], None),
])
def test_get_issue_filepath(title, labels, expected_path):
    assert get_issue_filepath(title, labels) == expected_path

def test_generate_markdown_content(mock_issue):
    content = _generate_markdown_content(mock_issue)
    assert "iid: 123" in content
    assert "title: 'Test Issue: Special Chars & Spaces'" in content
    assert "---" in content
    assert "This is a test description." in content
    # Check if yaml.dump was used correctly
    parsed = yaml.safe_load(content.split("---")[1])
    assert parsed["iid"] == 123

def test_write_issue_file(mock_issue, mock_config_paths):
    relative_path = Path("test/story-test-issue.md")
    full_path = write_issue_file(relative_path, mock_issue)
    
    expected_path = mock_config_paths["data_dir"] / relative_path
    assert full_path == expected_path
    assert full_path.exists()
    
    content = full_path.read_text()
    assert "iid: 123" in content
    assert "This is a test description." in content

def test_write_project_map(mock_config_paths):
    project_map_data = {"nodes": [{"id": 1, "title": "Node 1"}], "links": []}
    write_project_map(project_map_data)
    
    path = mock_config_paths["project_map_path"]
    assert path.exists()
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    assert data["nodes"][0]["id"] == 1

def test_timestamps_cache_read_write(mock_config_paths):
    # Test writing
    timestamps = {"1": "2025-01-01T00:00:00.000Z"}
    write_timestamps_cache(timestamps)
    
    path = mock_config_paths["timestamps_path"]
    assert path.exists()
    
    # Test reading
    read_data = read_timestamps_cache()
    assert read_data["1"] == "2025-01-01T00:00:00.000Z"

def test_read_timestamps_cache_not_found(mock_config_paths):
    # Ensure file doesn't exist
    assert not mock_config_paths["timestamps_path"].exists()
    data = read_timestamps_cache()
    assert data == {}

def test_read_timestamps_cache_corrupted(mock_config_paths):
    # Create a corrupted JSON file
    path = mock_config_paths["timestamps_path"]
    path.parent.mkdir(exist_ok=True)
    path.write_text("not json")
    
    data = read_timestamps_cache()
    assert data == {}
