import os
import re
import gitlab
import json
import networkx as nx
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
        raise ValueError("Error: GITLAB_URL and GITLAB_PRIVATE_TOKEN must be set.")

    try:
        gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_private_token)
        gl.auth()
        return gl
    except gitlab.exceptions.GitlabError as e:
        raise ConnectionError(f"Error connecting to GitLab: {e}") from e

def parse_relationships(current_issue_iid: int, text: str) -> list[dict]:
    relationships = []
    blocking_pattern = re.compile(r"/blocking\s+#(\d+)", re.IGNORECASE)
    for match in blocking_pattern.finditer(text):
        target_iid = int(match.group(1))
        relationships.append({"source": current_issue_iid, "target": target_iid, "type": "blocks"})

    blocked_by_pattern = re.compile(r"/blocked by\s+#(\d+)", re.IGNORECASE)
    for match in blocked_by_pattern.finditer(text):
        source_iid = int(match.group(1))
        relationships.append({"source": source_iid, "target": current_issue_iid, "type": "blocks"})

    return relationships

def smart_sync() -> dict:
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

def build_project_map() -> dict:
    try:
        gl = get_gitlab_client()
        project_id = os.getenv("GITLAB_PROJECT_ID")
        if not project_id:
            raise ValueError("Error: GITLAB_PROJECT_ID must be set.")
        project = gl.projects.get(project_id)
    except (ValueError, ConnectionError) as e:
        return {"status": "error", "message": str(e)}

    issues = project.issues.list(all=True)
    
    nodes_data = []
    links_data = []
    unique_links_set = set()

    for issue in issues:
        node = {
            "id": issue.iid,
            "title": issue.title,
            "type": "Issue",
            "state": issue.state,
            "web_url": issue.web_url,
            "labels": issue.labels,
        }
        nodes_data.append(node)

        # Parse relationships from description and comments
        all_text_to_parse = [issue.description or ""]
        for comment in issue.notes.list(all=True):
            all_text_to_parse.append(comment.body)

        for text in all_text_to_parse:
            found_relationships = parse_relationships(issue.iid, text)
            for rel in found_relationships:
                link_tuple = (rel["source"], rel["target"], rel["type"])
                if link_tuple not in unique_links_set:
                    unique_links_set.add(link_tuple)
                    links_data.append(rel)

    project_map_data = {
        "doctrine": {
            "gemini_md_path": "/docs/spec/GEMINI.md",
            "gemini_md_commit_hash": "TODO"
        },
        "nodes": nodes_data,
        "links": links_data
    }
    
    return {"status": "success", "map_data": project_map_data, "issues_found": len(issues)}
