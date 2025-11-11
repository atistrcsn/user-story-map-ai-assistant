import os
import gitlab
from functools import lru_cache

@lru_cache(maxsize=1)
def get_gitlab_client():
    """
    Initializes and returns a memoized GitLab client instance.
    Raises ValueError if configuration is missing.
    Raises ConnectionError if authentication fails.
    """
    gitlab_url = os.getenv("GGW_GITLAB_URL")
    gitlab_private_token = os.getenv("GGW_GITLAB_PRIVATE_TOKEN")
    if not gitlab_url or not gitlab_private_token:
        raise ValueError("Error: GGW_GITLAB_URL and GGW_GITLAB_PRIVATE_TOKEN must be set.")
    try:
        gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_private_token)
        gl.auth()
        return gl
    except gitlab.exceptions.GitlabError as e:
        raise ConnectionError(f"Error connecting to GitLab: {e}") from e

def get_project(project_id: str):
    """Gets a project object from GitLab."""
    gl = get_gitlab_client()
    return gl.projects.get(project_id)

def get_project_issues(project_id: str, **kwargs):
    """Lists all issues for a given project."""
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
