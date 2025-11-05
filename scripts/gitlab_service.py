import os
import re
import gitlab
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Module-level constants for cache paths
CACHE_DIR = ".gemini_cache"
TIMESTAMPS_CACHE_PATH = os.path.join(CACHE_DIR, "timestamps.json")

def get_gitlab_client():
    gitlab_url = os.getenv("GITLAB_URL")
    gitlab_private_token = os.getenv("GITLAB_PRIVATE_TOKEN")

    if not gitlab_url or not gitlab_private_token:
        # In a service, we should raise an exception rather than exit
        raise ValueError("Error: GITLAB_URL and GITLAB_PRIVATE_TOKEN must be set.")

    try:
        gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_private_token)
        gl.auth()
        return gl
    except gitlab.exceptions.GitlabError as e:
        # Let the caller handle the exception
        raise ConnectionError(f"Error connecting to GitLab: {e}") from e

def parse_relationships(current_issue_iid: int, text: str) -> list[dict]:
    """Parses text to find GitLab issue relationships (e.g., '/blocked by #<IID>', '/blocking #<IID>')."""
    relationships = []

    # Pattern for /blocking #<IID>
    blocking_pattern = re.compile(r"/blocking\s+#(\d+)", re.IGNORECASE)
    for match in blocking_pattern.finditer(text):
        target_iid = int(match.group(1))
        relationships.append({"source": current_issue_iid, "target": target_iid, "type": "blocks"})

    # Pattern for /blocked by #<IID>
    blocked_by_pattern = re.compile(r"/blocked by\s+#(\d+)", re.IGNORECASE)
    for match in blocked_by_pattern.finditer(text):
        source_iid = int(match.group(1))
        relationships.append({"source": source_iid, "target": current_issue_iid, "type": "blocks"})

    return relationships

def smart_sync() -> dict:
    """
    Performs an intelligent synchronization of GitLab issues.
    Only fetches issues that have been updated since the last sync.
    Returns a dictionary with the sync status and updated issues.
    """
    try:
        gl = get_gitlab_client()
        project_id = os.getenv("GITLAB_PROJECT_ID")
        if not project_id:
            raise ValueError("Error: GITLAB_PROJECT_ID must be set.")
        
        project = gl.projects.get(project_id)
    except (ValueError, ConnectionError) as e:
        return {"status": "error", "message": str(e)}

    os.makedirs(CACHE_DIR, exist_ok=True)

    last_timestamps = {}
    if os.path.exists(TIMESTAMPS_CACHE_PATH):
        with open(TIMESTAMPS_CACHE_PATH, 'r') as f:
            try:
                last_timestamps = json.load(f)
            except json.JSONDecodeError:
                # If cache is corrupt, we'll just perform a full sync
                pass

    all_issues_from_gitlab = project.issues.list(all=True, as_list=False)
    current_timestamps = {str(issue.iid): issue.updated_at for issue in all_issues_from_gitlab}
    
    updated_issue_iids = []
    for iid, updated_at_str in current_timestamps.items():
        if iid not in last_timestamps or last_timestamps[iid] < updated_at_str:
            updated_issue_iids.append(int(iid))

    updated_issues = []
    if updated_issue_iids:
        for iid in updated_issue_iids:
            issue = project.issues.get(iid)
            updated_issues.append({"iid": issue.iid, "title": issue.title})

    with open(TIMESTAMPS_CACHE_PATH, 'w') as f:
        json.dump(current_timestamps, f, indent=2)
        
    return {
        "status": "success",
        "updated_count": len(updated_issues),
        "updated_issues": updated_issues,
        "total_issues": len(current_timestamps)
    }