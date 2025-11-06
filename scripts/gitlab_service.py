import os
import re
import gitlab
import json
import yaml
import shutil
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Absolute Path Definitions ---
# Define the project root by going up one level from the script's directory (/scripts)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Define absolute paths for data and cache directories
CACHE_DIR = os.path.join(PROJECT_ROOT, ".gemini_cache")
TIMESTAMPS_CACHE_PATH = os.path.join(CACHE_DIR, "timestamps.json")
DATA_DIR = os.path.join(PROJECT_ROOT, "gitlab_data")
# --- End of Path Definitions ---

def _slugify(text):
    """Convert text to a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'--+', '-', text)
    return text.strip('-')

    for issue in issues:
        print(f"[DIAG] Processing issue: {issue.title}")
        print(f"[DIAG] Issue labels from GitLab: {issue.labels}")
        markdown_content = _generate_markdown_content(issue)
        relative_filepath = get_issue_filepath(issue.title, issue.labels)
        if not relative_filepath:
            relative_filepath = os.path.join("_unassigned", f"{_slugify(issue.title)}.md")
        
        full_filepath = os.path.join(DATA_DIR, relative_filepath)
        gitlab_managed_files.add(full_filepath)

        os.makedirs(os.path.dirname(full_filepath), exist_ok=True)
        with open(full_filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        node = {"id": issue.iid, "title": issue.title, "type": "Issue", "state": issue.state, "web_url": issue.web_url, "labels": issue.labels, "local_path": relative_filepath}
        nodes_data.append(node)
        print(f"[DIAG] Final relative_filepath in build_project_map: {relative_filepath}")

def get_issue_filepath(title: str, labels: list[str]) -> str | None:
    print(f"[DIAG] get_issue_filepath called with title: {title}, labels: {labels}")
    """
    Determines the canonical file path for an issue based on its title and labels.
    This is the single source of truth for generating issue file paths.
    An Epic is treated as a directory containing an 'epic.md' file for its own description.
    """
    is_story = "Type::Story" in labels
    is_task = "Type::Task" in labels
    print(f"[DIAG] Inside get_issue_filepath: is_story={is_story}, is_task={is_task}")

    if is_task:
        return None # Tasks are handled separately

    # Determine filename first, based SOLELY on whether it's a story.
    filename = f"story-{_slugify(title)}.md" if is_story else f"{_slugify(title)}.md"
    print(f"[DIAG] Inside get_issue_filepath: generated filename={filename}")

    backbone_label = next((label for label in labels if label.startswith("Backbone::")), None)
    epic_label = next((label for label in labels if label.startswith("Epic::")), None)
    
    if not backbone_label:
        return os.path.join("_unassigned", filename)

    backbone_name = _slugify(backbone_label.split("::", 1)[1])

    if epic_label:
        epic_name = _slugify(epic_label.split("::", 1)[1])
        if not is_story: # It's an Epic
            # The Epic's own file is special ('epic.md') and not prefixed.
            final_path = os.path.join("backbones", backbone_name, epic_name, "epic.md")
            print(f"[DIAG] Inside get_issue_filepath: final_path (Epic)={final_path}")
            return final_path
        else: # It's a Story belonging to an Epic
            final_path = os.path.join("backbones", backbone_name, epic_name, filename)
            print(f"[DIAG] Inside get_issue_filepath: final_path (Story with Epic)={final_path}")
            return final_path

    # It's a story without an epic, or another backbone-level issue. The filename is already correctly prefixed.
    final_path = os.path.join("backbones", backbone_name, filename)
    print(f"[DIAG] Inside get_issue_filepath: final_path (Backbone-level)={final_path}")
    return final_path

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
        "task_completion_status": issue.task_completion_status
    }
    content = f"---\n{yaml.dump(frontmatter, sort_keys=False)}---\n\n{issue.description or ''}\n"
    return content
# ... (rest of the file) ...
# In build_project_map function:
    for issue in issues:
        markdown_content = _generate_markdown_content(issue)
        relative_filepath = get_issue_filepath(issue.title, issue.labels)
        if not relative_filepath:
            relative_filepath = os.path.join("_unassigned", f"{_slugify(issue.title)}.md")
        
        full_filepath = os.path.join(DATA_DIR, relative_filepath)
        gitlab_managed_files.add(full_filepath)

        os.makedirs(os.path.dirname(full_filepath), exist_ok=True)
        with open(full_filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        node = {"id": issue.iid, "title": issue.title, "type": "Issue", "state": issue.state, "web_url": issue.web_url, "labels": issue.labels, "local_path": relative_filepath}
        nodes_data.append(node)

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
    updated_issue_iids = [int(iid) for iid, updated_at_str in current_timestamps.items() if iid not in last_timestamps or last_timestamps[iid] < updated_at_str]
    updated_issues = [project.issues.get(iid) for iid in updated_issue_iids]
    with open(TIMESTAMPS_CACHE_PATH, 'w') as f:
        json.dump(current_timestamps, f, indent=2)
    return {"status": "success", "updated_count": len(updated_issues), "updated_issues": [{"iid": i.iid, "title": i.title} for i in updated_issues], "total_issues": len(current_timestamps)}

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
    
    # Ensure the data directory exists without deleting it
    os.makedirs(DATA_DIR, exist_ok=True)

    nodes_data = []
    links_data = []
    unique_links_set = set()

    # Keep track of all file paths managed by GitLab issues
    gitlab_managed_files = set()

    for issue in issues:
        markdown_content = _generate_markdown_content(issue)
        relative_filepath = get_issue_filepath(issue.title, issue.labels)
        if not relative_filepath:
            relative_filepath = os.path.join("_unassigned", f"{_slugify(issue.title)}.md")
        
        full_filepath = os.path.join(DATA_DIR, relative_filepath)
        gitlab_managed_files.add(full_filepath)

        os.makedirs(os.path.dirname(full_filepath), exist_ok=True)
        with open(full_filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        node = {"id": issue.iid, "title": issue.title, "type": "Issue", "state": issue.state, "web_url": issue.web_url, "labels": issue.labels, "local_path": relative_filepath}
        nodes_data.append(node)
        
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

    # Future enhancement: Prune local files that are no longer on GitLab
    # For now, we just update/create.

    project_map_data = {"doctrine": {"gemini_md_path": "/docs/spec/GEMINI.md", "gemini_md_commit_hash": "TODO"}, "nodes": nodes_data, "links": links_data}
    return {"status": "success", "map_data": project_map_data, "issues_found": len(nodes_data)}

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
            if str(node.get("id", "")).startswith("NEW_"):
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
        nodes_to_create = [node for node in project_map.get("nodes", []) if str(node.get("id", "")).startswith("NEW_")]
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