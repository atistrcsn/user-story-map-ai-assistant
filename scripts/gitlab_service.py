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
    """
    Determines the canonical file path for an issue based on its title and labels.
    This function now primarily handles Epics and other top-level issues.
    The file path for Stories is determined dynamically in `build_project_map`
    by resolving their parent Epic via issue links.
    """
    print(f"[DIAG] get_issue_filepath called with title: '{title}', labels: {labels}")
    
    is_epic = "Type::Epic" in labels
    is_story = "Type::Story" in labels
    is_task = "Type::Task" in labels

    if is_task:
        return None  # Tasks are not standalone files

    # Generate a base filename
    filename = f"{_slugify(title)}.md"
    if is_epic:
        filename = "epic.md"

    backbone_label = next((label for label in labels if label.startswith("Backbone::")), None)
    
    # If there's no backbone, it's unassigned for now. Stories will be reassigned later.
    if not backbone_label:
        return os.path.join("_unassigned", filename)

    backbone_name = _slugify(backbone_label.split("::", 1)[1])

    # If it's an Epic, its path is determined by its backbone.
    if is_epic:
        epic_name = _slugify(title) # The directory name for an epic is its slugified title
        final_path = os.path.join("backbones", backbone_name, epic_name, filename)
        print(f"[DIAG] Path for Epic '{title}': {final_path}")
        return final_path

    # If it's a story or another backbone-level item, place it directly under the backbone for now.
    # Stories will be moved to their epic's directory later in the process.
    final_path = os.path.join("backbones", backbone_name, filename)
    print(f"[DIAG] Path for non-Epic item '{title}': {final_path}")
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

    issues_list = project.issues.list(all=True) # Get the full list once
    
    os.makedirs(DATA_DIR, exist_ok=True)

    nodes_data = []
    links_data = []
    unique_links_set = set()
    gitlab_managed_files = set()
    
    # Create a map of all issues by IID for quick lookups
    all_issues_map = {i.iid: i for i in issues_list}
    
    # Create a map for epic data: {epic_iid: epic_local_path}
    epic_map = {}

    # --- Pass 1: Process Epics and other non-Story items ---
    print("\n--- Pass 1: Processing Epics and other items ---")
    for issue in issues_list:
        if "Type::Story" in issue.labels:
            continue # Skip stories for now

        relative_filepath = get_issue_filepath(issue.title, issue.labels)
        if not relative_filepath:
            continue # Skip tasks or other non-file items

        if "Type::Epic" in issue.labels:
            epic_map[issue.iid] = os.path.dirname(relative_filepath)
            print(f"[DIAG] Mapped Epic {issue.iid} to path: {epic_map[issue.iid]}")

        # Write file and create node for the epic/other item
        full_filepath = os.path.join(DATA_DIR, relative_filepath)
        gitlab_managed_files.add(full_filepath)
        os.makedirs(os.path.dirname(full_filepath), exist_ok=True)
        with open(full_filepath, 'w', encoding='utf-8') as f:
            f.write(_generate_markdown_content(issue))

        node = {"id": issue.iid, "title": issue.title, "type": "Issue", "state": issue.state, "web_url": issue.web_url, "labels": issue.labels, "local_path": relative_filepath}
        nodes_data.append(node)

    # --- Pass 2: Process Stories and their relationships ---
    print("\n--- Pass 2: Processing Stories and their relationships ---")
    for issue in issues_list:
        if "Type::Story" not in issue.labels:
            continue # Only process stories in this pass

        parent_epic_iid = None
        parent_epic_path = None

        # Find parent epic through issue links
        try:
            project_issue = project.issues.get(issue.iid)
            print(f"[DIAG] Checking links for Story {issue.iid} ({issue.title})...")
            for link in project_issue.links.list():
                linked_issue_iid = link.iid
                if linked_issue_iid in all_issues_map and "Type::Epic" in all_issues_map[linked_issue_iid].labels:
                    parent_epic_iid = linked_issue_iid
                    parent_epic_path = epic_map.get(parent_epic_iid)
                    print(f"[DIAG] Story {issue.iid} is linked to Epic {parent_epic_iid} with path {parent_epic_path}")
                    break
        except gitlab.exceptions.GitlabHttpError as e:
            print(f"[WARN] Could not retrieve links for issue {issue.iid}, or a linked issue was not found: {e}")
        except Exception as e:
            print(f"[WARN] An unexpected error occurred while retrieving links for issue {issue.iid}: {e}")

        # Determine file path for the story
        story_filename = f"story-{_slugify(issue.title)}.md"
        if parent_epic_path:
            relative_filepath = os.path.join(parent_epic_path, story_filename)
            link_tuple = (parent_epic_iid, issue.iid, "contains")
            if link_tuple not in unique_links_set:
                unique_links_set.add(link_tuple)
                links_data.append({"source": parent_epic_iid, "target": issue.iid, "type": "contains"})
        else:
            backbone_label = next((label for label in issue.labels if label.startswith("Backbone::")), None)
            if backbone_label:
                backbone_name = _slugify(backbone_label.split("::", 1)[1])
                relative_filepath = os.path.join("backbones", backbone_name, story_filename)
            else:
                relative_filepath = os.path.join("_unassigned", story_filename)
        
        print(f"[DIAG] Final path for Story {issue.iid}: {relative_filepath}")

        # Write file and create node for the story
        full_filepath = os.path.join(DATA_DIR, relative_filepath)
        gitlab_managed_files.add(full_filepath)
        os.makedirs(os.path.dirname(full_filepath), exist_ok=True)
        with open(full_filepath, 'w', encoding='utf-8') as f:
            f.write(_generate_markdown_content(issue))

        node = {"id": issue.iid, "title": issue.title, "type": "Issue", "state": issue.state, "web_url": issue.web_url, "labels": issue.labels, "local_path": relative_filepath}
        nodes_data.append(node)

    # --- Pass 3: Process text-based relationships for all issues ---
    print("\n--- Pass 3: Processing text-based relationships ---")
    for issue in issues_list:
        all_text_to_parse = [issue.description or ""]
        try:
            # We need the project-level issue object to call .notes.list()
            project_issue = project.issues.get(issue.iid)
            for comment in project_issue.notes.list(all=True):
                all_text_to_parse.append(comment.body)
        except gitlab.exceptions.GitlabHttpError as e:
            print(f"[WARN] Could not retrieve notes for issue {issue.iid}: {e}")
        except Exception as e:
            print(f"[WARN] An unexpected error occurred while retrieving notes for issue {issue.iid}: {e}")

        for text in all_text_to_parse:
            found_relationships = parse_relationships(issue.iid, text)
            for rel in found_relationships:
                link_tuple = (rel["source"], rel["target"], rel["type"])
                if link_tuple not in unique_links_set:
                    unique_links_set.add(link_tuple)
                    links_data.append(rel)

    project_map_data = {"doctrine": {"gemini_md_path": "/docs/spec/GEMINI.md", "gemini_md_commit_hash": "TODO"}, "nodes": nodes_data, "links": links_data}
    return {"status": "success", "map_data": project_map_data, "issues_found": len(nodes_data)}

def upload_artifacts_to_gitlab(project_map: dict) -> dict:
    """
    Uploads new artifacts (labels, issues, links) from a project map to GitLab.
    This now includes creating 'relates_to' issue links for Epic-Story hierarchy.
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
    notes_with_links_count = 0
    issue_links_created_count = 0
    
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

    # --- 3. Create Links (as Notes for /blocking etc.) ---
    try:
        blocking_links = [link for link in project_map.get("links", []) if link.get("type") == "blocks"]
        for link in blocking_links:
            source_id_str = str(link.get("source"))
            target_id = link.get("target")
            
            if source_id_str.startswith("NEW_") and isinstance(target_id, int):
                source_new_iid = new_issue_id_map.get(source_id_str)
                if not source_new_iid:
                    continue

                target_issue = project.issues.get(target_id)
                note_body = f"/blocked by #{source_new_iid}"
                target_issue.notes.create({'body': note_body})
                notes_with_links_count += 1
    except gitlab.exceptions.GitlabError as e:
        return {"status": "error", "message": f"Failed to create links in notes: {e}"}

    # --- 4. Create Issue Links (for Epic-Story hierarchy) ---
    try:
        contains_links = [link for link in project_map.get("links", []) if link.get("type") == "contains"]
        for link in contains_links:
            source_id = link.get("source")
            target_id = link.get("target")

            # Resolve IIDs for both source (Epic) and target (Story)
            source_iid = new_issue_id_map.get(str(source_id), source_id)
            target_iid = new_issue_id_map.get(str(target_id), target_id)

            if not all(isinstance(i, int) for i in [source_iid, target_iid]):
                print(f"[WARN] Skipping link creation for source '{source_id}' -> target '{target_id}' due to invalid IID.")
                continue

            # Get the source issue object and create the link to the target
            source_issue = project.issues.get(source_iid)
            source_issue.links.create({'target_project_id': project.id, 'target_issue_iid': target_iid})
            issue_links_created_count += 1
            print(f"[INFO] Created 'relates_to' link from Epic #{source_iid} to Story #{target_iid}")

    except gitlab.exceptions.GitlabError as e:
        return {"status": "error", "message": f"Failed to create issue links: {e}"}

    return {
        "status": "success",
        "labels_created": labels_created_count,
        "issues_created": issues_created_count,
        "notes_with_links_created": notes_with_links_count,
        "issue_links_created": issue_links_created_count
    }