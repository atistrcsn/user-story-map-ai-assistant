import pytest
import os

@pytest.fixture(autouse=True)
def isolated_filesystem(mocker, tmp_path):
    """
    Automatically mocks all file paths to ensure tests run in an isolated
    temporary directory. This prevents tests from polluting the project's
    actual file system.
    """
    # Create dedicated temporary directories for the test run
    project_map_path = tmp_path / "project_map.yaml"
    data_dir = tmp_path / "gitlab_data"
    cache_dir = tmp_path / ".gemini_cache"
    timestamps_cache_path = cache_dir / "timestamps.json"
    
    # Ensure cache directory exists
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Patch the constants in the module where they are defined
    mocker.patch('gemini_gitlab_workflow.config.PROJECT_MAP_PATH', str(project_map_path))
    mocker.patch('gemini_gitlab_workflow.config.DATA_DIR', str(data_dir))
    mocker.patch('gemini_gitlab_workflow.config.CACHE_DIR', str(cache_dir))
    mocker.patch('gemini_gitlab_workflow.config.TIMESTAMPS_CACHE_PATH', str(timestamps_cache_path))
        
    # The test will run after this yield, using the patched paths
    yield
    
    # Teardown (if any) can happen here, but tmp_path handles it automatically

@pytest.fixture(autouse=True)
def mock_env_vars(mocker):
    """
    Automatically mocks essential environment variables for GitLab API interaction.
    """
    mocker.patch.dict(os.environ, {
        "GGW_GITLAB_URL": "http://mock-gitlab.com",
        "GGW_GITLAB_PRIVATE_TOKEN": "mock-token",
        "GGW_GITLAB_PROJECT_ID": "12345"
    })
