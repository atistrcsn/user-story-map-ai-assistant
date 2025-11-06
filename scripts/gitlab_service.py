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

    if "Type::Task" in labels:
        return None

    backbone_label = next((label for label in labels if label.startswith("Backbone::")), None)
    epic_label = next((label for label in labels if label.startswith("Epic::")), None)
    story_type_label = "Type::Story" in labels

    if story_type_label and epic_label and backbone_label:
        backbone_name = _slugify(backbone_label.split("::", 1)[1])
        epic_name = _slugify(epic_label.split("::", 1)[1])
        story_name = _slugify(title)
        return os.path.join("backbones", backbone_name, "epics", "stories", f"{story_name}.md")
    
    if epic_label and backbone_label:
        backbone_name = _slugify(backbone_label.split("::", 1)[1])
        epic_name = _slugify(epic_label.split("::", 1)[1])
        return os.path.join("backbones", backbone_name, "epics", f"{epic_name}.md")

    if backbone_label:
        backbone_name = _slugify(backbone_label.split("::", 1)[1])
        return os.path.join("backbones", backbone_name, f"{_slugify(title)}.md")

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

    backbone_label = next((label for label in labels if label.startswith("Backbone::")), None)
    epic_label = next((label for label in labels if label.startswith("Epic::")), None)
    story_type_label = "Type::Story" in labels

    if story_type_label and epic_label and backbone_label:
        backbone_name = _slugify(backbone_label.split("::", 1)[1])
        epic_name = _slugify(epic_label.split("::", 1)[1])
        story_name = _slugify(title)
        return os.path.join("backbones", backbone_name, "epics", "stories", f"{story_name}.md")
    
    if epic_label and backbone_label:
        backbone_name = _slugify(backbone_label.split("::", 1)[1])
        epic_name = _slugify(epic_label.split("::", 1)[1])
        return os.path.join("backbones", backbone_name, "epics", f"{epic_name}.md")

    if backbone_label:
        backbone_name = _slugify(backbone_label.split("::", 1)[1])
        return os.path.join("backbones", backbone_name, f"{_slugify(title)}.md")

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

def upload_artifacts_to_gitlab(project_map: dict) -> dict:
    """
    Uploads new artifacts (labels, issues, links) from a project map to GitLab.
    """
    try:
        gl = get_gitlab_client()
        project_id = os.getenv("GITLAB_PROJECT_ID")
        if not project_id:
            raise ValueError("Error: GITLAB_PROJECT_ID must be set.")
        project = gl.projects.get(project_id)
    except (ValueError, ConnectionError) as e:
        return {"status": "error", "message": str(e)}

    labels_created_count = 0
    issues_created_count = 0
    links_created_count = 0
    
    # --- 1. Handle Labels ---
    try:
        existing_labels = [label.name for label in project.labels.list(all=True)]
        all_new_labels = set()
        for node in project_map.get("nodes", []):
            if node.get("id", "").startswith("NEW_"):
                for label in node.get("labels", []):
                    all_new_labels.add(label)
        
        labels_to_create = [label for label in all_new_labels if label not in existing_labels]
        
        for label_name in labels_to_create:
            project.labels.create({'name': label_name, 'color': '#F0AD4E'})
            labels_created_count += 1
    except gitlab.exceptions.GitlabError as e:
        return {"status": "error", "message": f"Failed to create labels: {e}"}

    # --- 2. Create Issues ---
    new_issue_id_map = {} # Maps temporary ID (e.g., "NEW_1") to actual GitLab IID
    try:
        nodes_to_create = [node for node in project_map.get("nodes", []) if node.get("id", "").startswith("NEW_")]
        for node in nodes_to_create:
            issue_data = {
                'title': node.get("title"),
                'description': node.get("description", ""),
                'labels': node.get("labels", [])
            }
            new_issue = project.issues.create(issue_data)
            new_issue_id_map[node["id"]] = new_issue.iid
            issues_created_count += 1
    except gitlab.exceptions.GitlabError as e:
        return {"status": "error", "message": f"Failed to create issues: {e}"}

    # --- 3. Create Links (Notes) ---
    try:
        for link in project_map.get("links", []):
            source_id_str = str(link.get("source"))
            target_id = link.get("target")
            
            if source_id_str.startswith("NEW_") and isinstance(target_id, int):
                source_new_iid = new_issue_id_map.get(source_id_str)
                if not source_new_iid:
                    continue

                target_issue = project.issues.get(target_id)
                
                if link["type"] == "blocks":
                    note_body = f"/blocked by #{source_new_iid}"
                    target_issue.notes.create({'body': note_body})
                    links_created_count += 1
    except gitlab.exceptions.GitlabError as e:
        return {"status": "error", "message": f"Failed to create links: {e}"}

    return {
        "status": "success",
        "labels_created": labels_created_count,
        "issues_created": issues_created_count,
        "links_created": links_created_count
    }
