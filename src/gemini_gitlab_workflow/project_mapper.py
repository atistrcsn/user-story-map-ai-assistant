from pathlib import Path
import gitlab
import re
from . import gitlab_client, file_system_repo

def _parse_relationships(current_issue_iid: int, text: str) -> list[dict]:
    """Parses blocking/blocked by relationships from issue description or comments."""
    relationships = []
    # Using a simplified regex for demonstration
    blocking_pattern = re.compile(r"/blocking\s+#(\d+)", re.IGNORECASE)
    for match in blocking_pattern.finditer(text):
        target_iid = int(match.group(1))
        relationships.append({"source": current_issue_iid, "target": target_iid, "type": "blocks"})
    
    blocked_by_pattern = re.compile(r"/blocked by\s+#(\d+)", re.IGNORECASE)
    for match in blocked_by_pattern.finditer(text):
        source_iid = int(match.group(1))
        relationships.append({"source": source_iid, "target": current_issue_iid, "type": "blocks"})
        
    return relationships

def build_project_map(project_id: str) -> dict:
    """
    Builds a map of the GitLab project, fetches all issues,
    and organizes them into a local file structure.
    """
    try:
        issues_list = gitlab_client.get_project_issues(project_id, all=True)
    except (ValueError, ConnectionError, gitlab.exceptions.GitlabError) as e:
        return {"status": "error", "message": str(e)}

    nodes_data = []
    links_data = []
    unique_links_set = set()
    
    all_issues_map = {i.iid: i for i in issues_list}
    epic_map = {}

    # Pass 1: Process Epics and other non-Story items
    for issue in issues_list:
        if "Type::Story" in issue.labels:
            continue

        relative_filepath = file_system_repo.get_issue_filepath(issue.title, issue.labels)
        if not relative_filepath:
            continue

        if "Type::Epic" in issue.labels:
            # Store the issue title along with the path for the fallback mechanism
            epic_map[issue.iid] = {"path": relative_filepath.parent, "title": issue.title}

        file_system_repo.write_issue_file(relative_filepath, issue)
        nodes_data.append({
            "id": issue.iid, "title": issue.title, "type": "Issue", "state": issue.state,
            "web_url": issue.web_url, "labels": issue.labels, "local_path": str(relative_filepath)
        })

    # Create a reverse map from title to IID for the Epic label fallback
    epic_title_to_iid_map = {
        details["title"].lower(): iid for iid, details in epic_map.items()
    }

    # Pass 2: Process Stories and their relationships
    for issue in issues_list:
        if "Type::Story" not in issue.labels:
            continue

        parent_epic_iid = None
        parent_epic_path = None

        # Modern Approach: Check for "relates_to" issue links first
        try:
            for link in gitlab_client.get_issue_links(project_id, issue.iid):
                if link.iid in all_issues_map and "Type::Epic" in all_issues_map[link.iid].labels:
                    parent_epic_iid = link.iid
                    parent_epic_path = epic_map.get(parent_epic_iid, {}).get("path")
                    break
        except gitlab.exceptions.GitlabHttpError as e:
            print(f"[WARN] Could not retrieve links for issue {issue.iid}: {e}")

        # Backwards Compatibility: If no link found, check for legacy "Epic::" label
        if not parent_epic_iid:
            for label in issue.labels:
                if label.startswith("Epic::"):
                    epic_title = label.split("::", 1)[1].strip().lower()
                    found_iid = epic_title_to_iid_map.get(epic_title)
                    if found_iid:
                        parent_epic_iid = found_iid
                        parent_epic_path = epic_map.get(found_iid, {}).get("path")
                        print(f"[INFO] Found legacy epic link for Story #{issue.iid} -> Epic '{epic_title}' (#{parent_epic_iid})")
                        break
        
        story_filename = f"story-{file_system_repo._slugify(issue.title)}.md"
        if parent_epic_path:
            relative_filepath = parent_epic_path / story_filename
            # Ensure IDs are integers and link is unique before adding
            link_tuple = (int(parent_epic_iid), int(issue.iid), "contains")
            if link_tuple not in unique_links_set:
                unique_links_set.add(link_tuple)
                links_data.append({"source": int(parent_epic_iid), "target": int(issue.iid), "type": "contains"})
        else:
            relative_filepath = file_system_repo.get_issue_filepath(issue.title, issue.labels)

        file_system_repo.write_issue_file(relative_filepath, issue)
        nodes_data.append({
            "id": issue.iid, "title": issue.title, "type": "Issue", "state": issue.state,
            "web_url": issue.web_url, "labels": issue.labels, "local_path": str(relative_filepath)
        })

    # Pass 3: Process text-based relationships
    for issue in issues_list:
        all_text_to_parse = [issue.description or ""]
        try:
            for note in gitlab_client.get_issue_notes(project_id, issue.iid):
                all_text_to_parse.append(note.body)
        except gitlab.exceptions.GitlabHttpError as e:
            print(f"[WARN] Could not retrieve notes for issue {issue.iid}: {e}")

        for text in all_text_to_parse:
            for rel in _parse_relationships(issue.iid, text):
                link_tuple = (rel["source"], rel["target"], rel["type"])
                if link_tuple not in unique_links_set:
                    unique_links_set.add(link_tuple)
                    links_data.append({
                        "source": int(rel["source"]),
                        "target": int(rel["target"]),
                        "type": rel["type"]
                    })

    project_map_data = {
        "doctrine": {"gemini_md_path": "/docs/spec/GEMINI.md", "gemini_md_commit_hash": "TODO"},
        "nodes": nodes_data,
        "links": links_data
    }
    
    file_system_repo.write_project_map(project_map_data)

    return {"status": "success", "map_data": project_map_data, "issues_found": len(nodes_data)}
