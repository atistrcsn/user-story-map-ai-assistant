import time
import gitlab
from . import gitlab_client
from . import config
from pathlib import Path
import re

def _read_description_from_md_file(local_path: str) -> str:
    """Reads the description content from a markdown file, skipping the frontmatter."""
    try:
        full_path = config.DATA_DIR / local_path
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Use regex to find content after the second '---'
        match = re.search(r'---\s*\n.*?\n---\s*\n(.*)', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return content # Fallback to full content if frontmatter is not found
    except (FileNotFoundError, Exception) as e:
        print(f"[WARN] Could not read description from {local_path}: {e}")
        return ""

def _resolve_iid(issue_id, new_issue_id_map):
    """Resolves a raw issue ID from the project map to a GitLab IID."""
    if issue_id is None:
        return None
    issue_id_str = str(issue_id)
    if issue_id_str.startswith("NEW_"):
        return new_issue_id_map.get(issue_id_str)
    try:
        return int(issue_id_str)
    except (ValueError, TypeError):
        return None

def upload_artifacts_to_gitlab(project_id: str, project_map: dict) -> dict:
    """
    Uploads new artifacts (labels, issues, links) from a project map to GitLab.
    """
    labels_created_count = 0
    issues_created_count = 0
    notes_with_links_count = 0
    issue_links_created_count = 0

    created_label_names = []
    created_issue_iids = []
    new_issue_id_map = {}

    try:
        # 1. Handle Labels
        existing_labels = [label.name for label in gitlab_client.get_project_labels(project_id)]
        all_new_labels = set()
        for node in project_map.get("nodes", []):
            if str(node.get("id", "")).startswith("NEW_"):
                for label in node.get("labels", []):
                    if not label.startswith("Epic::"):
                        all_new_labels.add(label)
        
        labels_to_create = [label for label in all_new_labels if label not in existing_labels]
        
        for label_name in labels_to_create:
            gitlab_client.create_project_label(project_id, {'name': label_name, 'color': '#F0AD4E'})
            created_label_names.append(label_name)
            labels_created_count += 1
            time.sleep(0.1)

        # 2. Create Issues
        nodes_to_create = [node for node in project_map.get("nodes", []) if str(node.get("id", "")).startswith("NEW_")]
        for node in nodes_to_create:
            description = _read_description_from_md_file(node.get("local_path", ""))
            issue_data = {
                'title': node.get("title"),
                'description': description,
                'labels': [label for label in node.get("labels", []) if not label.startswith("Epic::")]
            }
            new_issue = gitlab_client.create_project_issue(project_id, issue_data)
            new_issue_id_map[node["id"]] = new_issue.iid
            created_issue_iids.append(new_issue.iid)
            issues_created_count += 1
            time.sleep(0.1)

        # 3. Create Links (as Notes for /blocked by)
        blocking_links = [link for link in project_map.get("links", []) if link.get("type") == "blocks"]
        for link in blocking_links:
            is_new_link = str(link.get("source")).startswith("NEW_") or str(link.get("target")).startswith("NEW_")
            if not is_new_link:
                continue

            source_iid = _resolve_iid(link.get("source"), new_issue_id_map)
            target_iid = _resolve_iid(link.get("target"), new_issue_id_map)

            # Ensure both IDs are resolved before creating the note.
            if source_iid and target_iid:
                note_body = f"/blocked by #{source_iid}"
                gitlab_client.create_issue_note(project_id, target_iid, {'body': note_body})
                notes_with_links_count += 1
                time.sleep(0.1)

        # 4. Create Issue Links (Hierarchy)
        contains_links = [l for l in project_map.get("links", []) if l.get("type") == "contains"]
        for link in contains_links:
            source_id = _resolve_iid(link.get("source"), new_issue_id_map)
            target_id = _resolve_iid(link.get("target"), new_issue_id_map)

            if source_id and target_id:
                try:
                    gitlab_client.create_issue_link(project_id, source_id, target_id)
                    issue_links_created_count += 1
                    time.sleep(0.1)
                except gitlab.exceptions.GitlabError as e:
                    if hasattr(e, 'response_code') and e.response_code == 409 and "already assigned" in str(e):
                        print(f"INFO: Link from issue #{source_id} to #{target_id} already exists. Skipping.")
                    else:
                        raise

    except gitlab.exceptions.GitlabError as e:
        # Rollback Logic
        for iid in reversed(created_issue_iids):
            try:
                gitlab_client.delete_project_issue(project_id, iid)
            except gitlab.exceptions.GitlabError as rollback_e:
                print(f"[ERROR] Failed to rollback issue #{iid}: {rollback_e}")
        for label_name in reversed(created_label_names):
            try:
                gitlab_client.delete_project_label(project_id, label_name)
            except gitlab.exceptions.GitlabError as rollback_e:
                print(f"[ERROR] Failed to rollback label '{label_name}': {rollback_e}")
        return {"status": "error", "message": f"Failed to upload artifacts: {e}"}

    return {
        "status": "success",
        "labels_created": labels_created_count,
        "issues_created": issues_created_count,
        "notes_with_links_created": notes_with_links_count,
        "issue_links_created": issue_links_created_count
    }
