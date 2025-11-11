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
            epic_map[issue.iid] = relative_filepath.parent

        file_system_repo.write_issue_file(relative_filepath, issue)
        nodes_data.append({
            "id": issue.iid, "title": issue.title, "type": "Issue", "state": issue.state,
            "web_url": issue.web_url, "labels": issue.labels, "local_path": str(relative_filepath)
        })

    # Pass 2: Process Stories and their relationships
    for issue in issues_list:
        if "Type::Story" not in issue.labels:
            continue

        parent_epic_iid = None
        parent_epic_path = None

        try:
            for link in gitlab_client.get_issue_links(project_id, issue.iid):
                if link.iid in all_issues_map and "Type::Epic" in all_issues_map[link.iid].labels:
                    parent_epic_iid = link.iid
                    parent_epic_path = epic_map.get(parent_epic_iid)
                    break
        except gitlab.exceptions.GitlabHttpError as e:
            print(f"[WARN] Could not retrieve links for issue {issue.iid}: {e}")

        story_filename = f"story-{file_system_repo._slugify(issue.title)}.md"
        if parent_epic_path:
            relative_filepath = parent_epic_path / story_filename
            link_tuple = (parent_epic_iid, issue.iid, "contains")
            if link_tuple not in unique_links_set:
                unique_links_set.add(link_tuple)
                links_data.append({"source": parent_epic_iid, "target": issue.iid, "type": "contains"})
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
                    links_data.append(rel)

    project_map_data = {
        "doctrine": {"gemini_md_path": "/docs/spec/GEMINI.md", "gemini_md_commit_hash": "TODO"},
        "nodes": nodes_data,
        "links": links_data
    }
    
    file_system_repo.write_project_map(project_map_data)

    return {"status": "success", "map_data": project_map_data, "issues_found": len(nodes_data)}
