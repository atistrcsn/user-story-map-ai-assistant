import pytest

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
    
    # Patch the constants in the module where they are defined
    mocker.patch('gemini_gitlab_workflow.config.PROJECT_MAP_PATH', str(project_map_path))
    mocker.patch('gemini_gitlab_workflow.config.DATA_DIR', str(data_dir))
    
    # The test will run after this yield, using the patched paths
    yield
    
    # Teardown (if any) can happen here, but tmp_path handles it automatically
