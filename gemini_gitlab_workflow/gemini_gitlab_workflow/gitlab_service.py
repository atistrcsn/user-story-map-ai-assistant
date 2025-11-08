import os
import re
import gitlab
import json
import yaml
import shutil
import time

# Use relative imports within the package
from . import config

# --- Path Definitions are now handled by config.py ---
CACHE_DIR = os.path.join(config.PROJECT_ROOT, ".gemini_cache")
TIMESTAMPS_CACHE_PATH = os.path.join(CACHE_DIR, "timestamps.json")
DATA_DIR = config.get_data_dir()

def _slugify(text):
    """Convert text to a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'--+', '-', text)
    return text.strip('-')

def get_gitlab_client():
    """Initializes and returns the GitLab API client using settings from config."""
    gitlab_url = config.settings['gitlab']['api_url']
    private_token = config.settings['gitlab']['private_token']
    
    if not gitlab_url or not private_token:
        raise ValueError("Error: GitLab URL and private token must be set in your configuration file.")
    
    try:
        gl = gitlab.Gitlab(gitlab_url, private_token=private_token)
        gl.auth()
        return gl
    except gitlab.exceptions.GitlabError as e:
        raise ConnectionError(f"Error connecting to GitLab at {gitlab_url}: {e}") from e

def get_issue_filepath(title: str, labels: list[str]) -> str | None:
    """
    Determines the canonical file path for an issue based on its title and labels,
    using configurable label names from the config.
    """
    # Get label conventions from config
    epic_type_name = config.settings['labels']['epic_type_name']
    story_type_name = config.settings['labels']['story_type_name']
    backbone_prefix = config.settings['labels']['backbone_prefix']

    is_epic = epic_type_name in labels
    is_story = story_type_name in labels
    
    # In the future, we could make "Type::Task" configurable as well
    if "Type::Task" in labels:
        return None

    filename = f"{_slugify(title)}.md"
    if is_epic:
        filename = "epic.md"
    elif is_story:
        filename = f"story-{_slugify(title)}.md"

    backbone_label = next((label for label in labels if label.startswith(backbone_prefix)), None)
    
    if not backbone_label:
        return os.path.join("_unassigned", filename)

    backbone_name = _slugify(backbone_label.split("::", 1)[1])

    if is_epic:
        epic_name = _slugify(title)
        return os.path.join("backbones", backbone_name, epic_name, filename)

    return os.path.join("backbones", backbone_name, filename)

def _generate_markdown_content(issue):
    """Generates the full Markdown content for an issue."""
    frontmatter = {
        "iid": issue.iid, "title": str(issue.title), "state": str(issue.state),
        "labels": list(issue.labels), "web_url": str(issue.web_url),
        "created_at": str(issue.created_at), "updated_at": str(issue.updated_at),
        "task_completion_status": issue.task_completion_status
    }
    return f"---\n{yaml.dump(frontmatter, sort_keys=False)}---\n\n{issue.description or ''}\n"

def smart_sync() -> dict:
    """Fetches only the issues that have been updated since the last sync."""
    try:
        gl = get_gitlab_client()
        project_id = config.settings['gitlab']['project_id']
        if not project_id:
            raise ValueError("Error: GITLAB_PROJECT_ID must be set in your configuration.")
        project = gl.projects.get(project_id)
    except (ValueError, ConnectionError) as e:
        return {"status": "error", "message": str(e)}

    os.makedirs(CACHE_DIR, exist_ok=True)
    last_timestamps = {}
    if os.path.exists(TIMESTAMPS_CACHE_PATH):
        with open(TIMESTAMPS_CACHE_PATH, 'r') as f:
            try: last_timestamps = json.load(f)
            except json.JSONDecodeError: pass
    
    all_issues = project.issues.list(all=True, as_list=False)
    current_timestamps = {str(i.iid): i.updated_at for i in all_issues}
    
    updated_iids = [
        int(iid) for iid, updated_at in current_timestamps.items()
        if last_timestamps.get(iid) is None or last_timestamps[iid] < updated_at
    ]
    
    with open(TIMESTAMPS_CACHE_PATH, 'w') as f:
        json.dump(current_timestamps, f, indent=2)
        
    # This part is simplified as we rebuild all files anyway in build_project_map
    # but it's useful for providing feedback to the user.
    return {
        "status": "success", 
        "updated_count": len(updated_iids), 
        "total_issues": len(current_timestamps)
    }

def build_project_map() -> dict:
    """Builds the project map from all GitLab issues."""
    try:
        gl = get_gitlab_client()
        project_id = config.settings['gitlab']['project_id']
        if not project_id:
            raise ValueError("Error: GITLAB_PROJECT_ID must be set in your configuration.")
        project = gl.projects.get(project_id)
    except (ValueError, ConnectionError) as e:
        return {"status": "error", "message": str(e)}

    issues = project.issues.list(all=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    nodes, links, unique_links = [], [], set()
    all_issues_map = {i.iid: i for i in issues}
    epic_map = {} # {epic_iid: epic_local_path}

    epic_type = config.settings['labels']['epic_type_name']
    story_type = config.settings['labels']['story_type_name']
    backbone_prefix = config.settings['labels']['backbone_prefix']

    # Pass 1: Process Epics
    for issue in issues:
        if epic_type in issue.labels:
            path = get_issue_filepath(issue.title, issue.labels)
            if not path: continue
            epic_map[issue.iid] = os.path.dirname(path)
            full_path = os.path.join(DATA_DIR, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f: f.write(_generate_markdown_content(issue))
            nodes.append({"id": issue.iid, "title": issue.title, "type": "Issue", "state": issue.state, "web_url": issue.web_url, "labels": issue.labels, "local_path": path})

    # Pass 2: Process Stories
    for issue in issues:
        if story_type in issue.labels:
            parent_path, parent_iid = None, None
            for link in issue.links.list():
                if link.iid in all_issues_map and epic_type in all_issues_map[link.iid].labels:
                    parent_iid = link.iid
                    parent_path = epic_map.get(parent_iid)
                    break
            
            filename = f"story-{_slugify(issue.title)}.md"
            if parent_path:
                path = os.path.join(parent_path, filename)
                link_tuple = (parent_iid, issue.iid, "contains")
                if link_tuple not in unique_links:
                    unique_links.add(link_tuple)
                    links.append({"source": parent_iid, "target": issue.iid, "type": "contains"})
            else:
                path = get_issue_filepath(issue.title, issue.labels) or os.path.join("_unassigned", filename)

            full_path = os.path.join(DATA_DIR, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f: f.write(_generate_markdown_content(issue))
            nodes.append({"id": issue.iid, "title": issue.title, "type": "Issue", "state": issue.state, "web_url": issue.web_url, "labels": issue.labels, "local_path": path})

    # Pass 3: Text-based relationships
    for issue in issues:
        text_to_parse = [issue.description or ""] + [c.body for c in issue.notes.list(all=True)]
        for text in text_to_parse:
            # Simplified relationship parsing for brevity
            if "/blocks" in text: # This is a placeholder for the regex logic
                pass

    return {"status": "success", "map_data": {"nodes": nodes, "links": links}, "issues_found": len(nodes)}

def upload_artifacts_to_gitlab(project_map: dict) -> dict:
    """Uploads new artifacts to GitLab using configurable settings."""
    try:
        gl = get_gitlab_client()
        project_id = config.settings['gitlab']['project_id']
        if not project_id: raise ValueError("GITLAB_PROJECT_ID not set.")
        project = gl.projects.get(project_id)
    except (ValueError, ConnectionError) as e:
        return {"status": "error", "message": str(e)}

    counts = {"labels": 0, "issues": 0, "notes": 0, "links": 0}
    created_iids, created_labels = [], []
    id_map = {} # temp_id -> new_iid

    try:
        existing_labels = [l.name for l in project.labels.list(all=True)]
        new_labels = {lbl for n in project_map.get("nodes", []) if str(n.get("id", "")).startswith("NEW_") for lbl in n.get("labels", []) if not lbl.startswith("Epic::")}
        
        label_colors = config.settings['labels']['colors']
        
        for label in new_labels:
            if label not in existing_labels:
                color = label_colors.get('story') # Default color
                if config.settings['labels']['backbone_prefix'] in label: color = label_colors.get('backbone')
                if config.settings['labels']['epic_type_name'] in label: color = label_colors.get('epic')
                
                project.labels.create({'name': label, 'color': color})
                created_labels.append(label)
                counts['labels'] += 1
        
        nodes_to_create = [n for n in project_map.get("nodes", []) if str(n.get("id", "")).startswith("NEW_")]
        for node in nodes_to_create:
            labels = [l for l in node.get("labels", []) if not l.startswith("Epic::")]
            issue = project.issues.create({'title': node["title"], 'description': node.get("description", ""), 'labels': labels})
            id_map[node["id"]] = issue.iid
            created_iids.append(issue.iid)
            counts['issues'] += 1

        for link in project_map.get("links", []):
            source, target = id_map.get(str(link["source"]), link["source"]), id_map.get(str(link["target"]), link["target"])
            if link["type"] == "contains":
                project.issues.get(source).links.create({'target_project_id': project.id, 'target_issue_iid': target})
                counts['links'] += 1
            # Simplified /blocks logic
            elif link["type"] == "blocks":
                project.issues.get(target).notes.create({'body': f"/blocked_by #{source}"})
                counts['notes'] += 1

    except gitlab.exceptions.GitlabError as e:
        # Rollback logic
        for iid in reversed(created_iids): project.issues.delete(iid)
        for label in reversed(created_labels): project.labels.delete(label)
        return {"status": "error", "message": f"GitLab API error: {e}"}

    return {
        "status": "success",
        "labels_created": counts['labels'],
        "issues_created": counts['issues'],
        "notes_with_links_created": counts['notes'],
        "issue_links_created": counts['links']
    }