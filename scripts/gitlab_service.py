import os
import re
import gitlab
import json
import networkx as nx
import yaml
import shutil
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Module-level constants
CACHE_DIR = ".gemini_cache"
TIMESTAMPS_CACHE_PATH = os.path.join(CACHE_DIR, "timestamps.json")
DATA_DIR = "gitlab_data"

def _slugify(text):
    """Convert text to a URL-friendly slug."""
    text = text.lower()
    # Replace non-alphanumeric characters with a hyphen
    text = re.sub(r'[^a-z0-9]+', '-', text)
    # Collapse consecutive hyphens
    text = re.sub(r'--+', '-', text)
    return text.strip('-')

def _get_issue_filepath(issue):
    """Determines the file path for an issue based on its labels and title (Hybrid Model)."""
    labels = issue.labels
    title = issue.title

    # Check for Task type first - these do not get their own file
    if "Type::Task" in labels:
        return None

    path_parts = []
    issue_type = ""

    # Determine issue type and extract parent names from labels
    backbone_label = next((label for label in labels if label.startswith("Backbone::")), None)
    epic_label = next((label for label in labels if label.startswith("Epic::")), None)
    story_type_label = "Type::Story" in labels

    # Logic for path construction based on Hybrid Model
    if backbone_label:
        backbone_name = _slugify(backbone_label.split("::", 1)[1])
        path_parts.append(os.path.join("backbones", backbone_name))

    if epic_label:
        epic_name = _slugify(epic_label.split("::", 1)[1])
        path_parts.append(os.path.join("epics", epic_name))

    if story_type_label:
        # A story must be under an epic, which must be under a backbone
        if not epic_label or not backbone_label:
            return os.path.join("_unassigned", f"{_slugify(title)}.md")
        path_parts.append("stories")
        return os.path.join(*path_parts, f"{_slugify(title)}.md")
    
    if epic_label: # It's an Epic
        if not backbone_label:
            return os.path.join("_unassigned", f"{_slugify(title)}.md")
        return os.path.join(*path_parts, f"{_slugify(title)}.md")

    if backbone_label: # It's a Backbone
        return os.path.join(*path_parts, f"{_slugify(title)}.md")

    # Default to unassigned if no hierarchy labels are found
    return os.path.join("_unassigned", f"{_slugify(title)}.md")

def _generate_markdown_content(issue):
    """Generates the full Markdown content for an issue."""
    frontmatter = {
        "iid": issue.iid,
        "title": str(issue.title),
        "state": str(issue.state),
        "labels": list(issue.labels),
        "web_url": str(issue.web_url),
        "created_at": str(issue.created_at),
        "updated_at": str(issue.updated_at),
        "task_completion_status": issue.task_completion_status # Add task status
    }
    content = f"""---
{yaml.dump(frontmatter, sort_keys=False)}---

{issue.description or ''}
"""
    return content

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
    
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    os.makedirs(DATA_DIR)

    nodes_data = []
    links_data = []
    unique_links_set = set()

    for issue in issues:
        # Determine if it's a Task type - these do not get their own file or node in project_map
        if "Type::Task" in issue.labels:
            continue # Skip processing this issue as a separate entity

        # 1. Generate content and path
        markdown_content = _generate_markdown_content(issue)
        relative_filepath = _get_issue_filepath(issue)
        
        if relative_filepath: # Only write file if a path is returned (i.e., not a Task)
            full_filepath = os.path.join(DATA_DIR, relative_filepath)
            os.makedirs(os.path.dirname(full_filepath), exist_ok=True)
            with open(full_filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            # 2. Build node for project map
            node = {
                "id": issue.iid,
                "title": issue.title,
                "type": "Issue", # Default type, will be refined by labels
                "state": issue.state,
                "web_url": issue.web_url,
                "labels": issue.labels,
                "local_path": relative_filepath
            }
            nodes_data.append(node)

            # 3. Parse relationships for project map
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
    
    return {"status": "success", "map_data": project_map_data, "issues_found": len(nodes_data)}

def _get_issue_filepath_from_dict(issue_dict):
    """Determines the file path for an issue based on its labels and title from a dictionary."""
    labels = issue_dict.get("labels", [])
    title = issue_dict.get("title", "")

    if "Type::Task" in labels:
        return None

    path_parts = []

    backbone_label = next((label for label in labels if label.startswith("Backbone::")), None)
    epic_label = next((label for label in labels if label.startswith("Epic::")), None)
    story_type_label = "Type::Story" in labels

    if backbone_label:
        backbone_name = _slugify(backbone_label.split("::", 1)[1])
        path_parts.append(os.path.join("backbones", backbone_name))

    if epic_label:
        epic_name = _slugify(epic_label.split("::", 1)[1])
        path_parts.append(os.path.join("epics", epic_name))

    if story_type_label:
        if not epic_label or not backbone_label:
            return os.path.join("_unassigned", f"{_slugify(title)}.md")
        path_parts.append("stories")
        return os.path.join(*path_parts, f"{_slugify(title)}.md")
    
    if epic_label:
        if not backbone_label:
            return os.path.join("_unassigned", f"{_slugify(title)}.md")
        return os.path.join(*path_parts, f"{_slugify(title)}.md")

    if backbone_label:
        return os.path.join(*path_parts, f"{_slugify(title)}.md")

    return os.path.join("_unassigned", f"{_slugify(title)}.md")

def _generate_markdown_content_from_dict(issue_dict):
    """Generates the full Markdown content for an issue from a dictionary."""
    frontmatter = {
        "iid": issue_dict.get("iid", "NEW"), # Use NEW for newly generated issues
        "title": issue_dict.get("title", ""),
        "state": issue_dict.get("state", "opened"),
        "labels": issue_dict.get("labels", []),
        "web_url": issue_dict.get("web_url", "N/A"),
        "created_at": issue_dict.get("created_at", "N/A"),
        "updated_at": issue_dict.get("updated_at", "N/A"),
        "task_completion_status": issue_dict.get("task_completion_status", {"count": 0, "completed_count": 0})
    }
    content = f"""---
{yaml.dump(frontmatter, sort_keys=False)}---

{issue_dict.get("description", "")}
"""
    return content

def generate_local_artifacts(proposed_issues: list[dict], project_map_path: str) -> dict:
    """
    Generates local Markdown files for proposed issues and updates the project map.
    """
    new_nodes_data = []
    new_links_data = []
    
    # Ensure DATA_DIR exists
    os.makedirs(DATA_DIR, exist_ok=True)

    for issue_dict in proposed_issues:
        # 1. Generate content and path
        markdown_content = _generate_markdown_content_from_dict(issue_dict)
        relative_filepath = _get_issue_filepath_from_dict(issue_dict)
        
        if relative_filepath:
            full_filepath = os.path.join(DATA_DIR, relative_filepath)
            os.makedirs(os.path.dirname(full_filepath), exist_ok=True)
            with open(full_filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            # 2. Build node for project map
            node = {
                "id": issue_dict.get("iid", "NEW"),
                "title": issue_dict.get("title", ""),
                "type": "Issue", # Default type, will be refined by labels
                "state": issue_dict.get("state", "opened"),
                "web_url": issue_dict.get("web_url", "N/A"),
                "labels": issue_dict.get("labels", []),
                "local_path": relative_filepath
            }
            new_nodes_data.append(node)

            # 3. Parse relationships for project map (from description for new issues)
            # For newly proposed issues, relationships are typically defined in the description
            # or explicitly passed in the issue_dict. For simplicity, we'll assume they are
            # in the description for now, similar to existing issues.
            all_text_to_parse = [issue_dict.get("description", "")]
            # Note: For new issues, there are no existing comments to parse.

            # We need a temporary IID for new issues to link them in the local map.
            # This will be replaced by real GitLab IIDs during upload.
            temp_iid = f"NEW_{len(new_nodes_data)}" 
            node["id"] = temp_iid # Assign temporary IID for local map

            for text in all_text_to_parse:
                found_relationships = parse_relationships(temp_iid, text) # Use temp_iid
                for rel in found_relationships:
                    new_links_data.append(rel)

    # Load existing project map and merge new data
    project_map_data = {"doctrine": {}, "nodes": [], "links": []}
    if os.path.exists(project_map_path):
        with open(project_map_path, 'r') as f:
            project_map_data = yaml.safe_load(f)

    project_map_data["nodes"].extend(new_nodes_data)
    project_map_data["links"].extend(new_links_data)

    with open(project_map_path, 'w') as f:
        yaml.dump(project_map_data, f, sort_keys=False)

    return {"status": "success", "generated_count": len(new_nodes_data), "new_nodes": new_nodes_data}