import os
import gitlab
from functools import lru_cache
from .config import GitlabConfig

@lru_cache(maxsize=1)
def get_gitlab_client():
    """
    Initializes and returns a memoized GitLab client instance using GitlabConfig.
    Raises ValueError if configuration is missing.
    Raises ConnectionError if authentication fails.
    """
    try:
        config = GitlabConfig()
        gl = gitlab.Gitlab(config.url, private_token=config.private_token)
        gl.auth()
        return gl
    except ValueError as e:
        # Re-raise the specific config error from the dataclass
        raise ValueError(f"GitLab configuration error: {e}") from e
    except gitlab.exceptions.GitlabError as e:
        raise ConnectionError(f"Error connecting to GitLab: {e}") from e

def get_project(project_id: str):
    """Gets a project object from GitLab by its ID."""
    gl = get_gitlab_client()
    return gl.projects.get(project_id)

def get_project_board(project_id: str):
    """Gets the configured board object from the project."""
    config = GitlabConfig()
    if not config.board_id:
        return None
    project = get_project(project_id)
    try:
        return project.boards.get(config.board_id)
    except gitlab.exceptions.GitlabGetError:
        # The board with the given ID was not found
        return None

def get_project_issues(project_id: str, **kwargs):
    """
    Lists all issues for a given project.
    Accepts any filter arguments supported by the python-gitlab library's
    issues.list() method, such as 'state', 'labels', or 'list_id'.
    """
    project = get_project(project_id)
    return project.issues.list(**kwargs)

def get_project_issue(project_id: str, issue_iid: int):
    """Gets a single issue from a project."""
    project = get_project(project_id)
    return project.issues.get(issue_iid)

def get_issue_links(project_id: str, issue_iid: int):
    """Lists all links for a given issue."""
    issue = get_project_issue(project_id, issue_iid)
    return issue.links.list(all=True)

def get_issue_notes(project_id: str, issue_iid: int):
    """Lists all notes (comments) for a given issue."""
    issue = get_project_issue(project_id, issue_iid)
    return issue.notes.list(all=True)

def get_project_labels(project_id: str):
    """Lists all labels for a given project."""
    project = get_project(project_id)
    return project.labels.list(all=True)

def create_project_label(project_id: str, label_data: dict):
    """Creates a new label in a project."""
    project = get_project(project_id)
    return project.labels.create(label_data)

def delete_project_label(project_id: str, label_name: str):
    """Deletes a label from a project."""
    project = get_project(project_id)
    project.labels.delete(label_name)

def create_project_issue(project_id: str, issue_data: dict):
    """Creates a new issue in a project."""
    project = get_project(project_id)
    return project.issues.create(issue_data)

def delete_project_issue(project_id: str, issue_iid: int):
    """Deletes an issue from a project."""
    project = get_project(project_id)
    project.issues.delete(issue_iid)

def create_issue_note(project_id: str, issue_iid: int, note_data: dict):
    """Creates a new note on an issue."""
    issue = get_project_issue(project_id, issue_iid)
    return issue.notes.create(note_data)

def create_issue_link(project_id: str, source_issue_iid: int, target_issue_iid: int, link_type: str = 'relates_to'):
    """Creates a link between two issues."""
    source_issue = get_project_issue(project_id, source_issue_iid)
    link_data = {
        'target_project_id': project_id,
        'target_issue_iid': target_issue_iid,
        'link_type': link_type
    }
    return source_issue.links.create(link_data)

def move_issue_in_board_list(project_id: str, issue_iid: int, move_before_id: int):
    """
    Moves an issue to a new position within a board list.

    Args:
        project_id: The ID of the project.
        issue_iid: The IID of the issue to move.
        move_before_id: The global ID of the issue to move it before.
    """
    gl = get_gitlab_client()
    project = gl.projects.get(project_id)
    issue = project.issues.get(issue_iid)
    issue.reorder(move_before_id=move_before_id)
    return issue
