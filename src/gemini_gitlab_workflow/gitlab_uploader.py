import time
import gitlab
import logging
from . import gitlab_client
from .config import GitlabConfig, PROJECT_MAP_PATH, DATA_DIR
from pathlib import Path
import re
from ruamel.yaml import YAML

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GitlabUploader:
    """
    Handles the entire process of uploading artifacts from the local project map
    to GitLab, including creating issues, labels, links, and reordering stories.
    """
    def __init__(self, project_id: str, project_map: dict):
        self.project_id = project_id
        self.project_map = project_map
        self.config = GitlabConfig()
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.created_label_names = []
        self.created_issues = [] # Will store full issue objects
        self.new_issue_id_map = {} # Maps "NEW_..." to a final GitLab IID
        self.reorder_list = [] # List of (story_issue, epic_issue) tuples
        self.links_created_count = 0

    def upload(self) -> dict:
        """Main orchestration method."""
        try:
            self._create_labels()
            self._create_issues()
            self._create_links()
            self._update_project_map_iids()
            self._reorder_stories_on_board()
        except gitlab.exceptions.GitlabError as e:
            logging.error(f"A GitLab API error occurred: {e}")
            self._rollback()
            return {"status": "error", "message": f"Failed to upload artifacts: {e}"}
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            self._rollback()
            return {"status": "error", "message": f"An unexpected error occurred: {e}"}

        return {
            "status": "success",
            "labels_created": len(self.created_label_names),
            "issues_created": len(self.created_issues),
            "issue_links_created": self.links_created_count,
            "project_map_updated": True,
            "stories_reordered": len(self.reorder_list)
        }

    def _rollback(self):
        """Rolls back created GitLab artifacts in case of an error."""
        logging.info("--- Initiating Rollback ---")
        # Issues are deleted directly via their objects, which are project-specific
        for issue in reversed(self.created_issues):
            try:
                logging.info(f"Deleting issue #{issue.iid} from project {self.project_id}...")
                # The issue object is already scoped to the project, no need to pass project_id again
                issue.delete()
            except gitlab.exceptions.GitlabError as e:
                logging.error(f"Failed to rollback issue #{issue.iid}: {e}")
        
        for label_name in reversed(self.created_label_names):
            try:
                logging.info(f"Deleting label '{label_name}' from project {self.project_id}...")
                gitlab_client.delete_project_label(self.project_id, label_name)
            except gitlab.exceptions.GitlabError as e:
                logging.error(f"Failed to rollback label '{label_name}': {e}")
        logging.info("--- Rollback Complete ---")

    def _create_labels(self):
        """Creates any new labels in GitLab that don't already exist."""
        logging.info("Step 1: Creating labels...")
        existing_labels = [label.name for label in gitlab_client.get_project_labels(self.project_id)]
        all_new_labels = set(
            label
            for node in self.project_map.get("nodes", [])
            if str(node.get("id", "")).startswith("NEW_")
            for label in node.get("labels", [])
            if not label.startswith("Epic::")
        )
        labels_to_create = [label for label in all_new_labels if label not in existing_labels]
        
        for label_name in labels_to_create:
            logging.info(f"  - Creating label: {label_name}")
            gitlab_client.create_project_label(self.project_id, {'name': label_name, 'color': '#F0AD4E'})
            self.created_label_names.append(label_name)
            time.sleep(0.1)
        logging.info(f"Created {len(self.created_label_names)} new labels.")

    def _create_issues(self):
        """Creates new issues in GitLab and prepares the reorder list."""
        logging.info("Step 2: Creating issues...")
        nodes_to_create = [node for node in self.project_map.get("nodes", []) if str(node.get("id", "")).startswith("NEW_")]
        
        id_to_node_map = {str(node['id']): node for node in self.project_map.get("nodes", [])}

        for node in nodes_to_create:
            description = self._read_description_from_md_file(node.get("local_path", ""))
            issue_data = {
                'title': node.get("title"),
                'description': description,
                'labels': [label for label in node.get("labels", []) if not label.startswith("Epic::")]
            }
            new_issue = gitlab_client.create_project_issue(self.project_id, issue_data)
            logging.info(f"  - Created issue #{new_issue.iid}: {new_issue.title}")
            self.created_issues.append(new_issue)
            self.new_issue_id_map[node["id"]] = new_issue.iid
            
            if self.config.board_id and "Type::Story" in node.get("labels", []):
                parent_epic_link = next((link for link in self.project_map.get("links", []) if link.get("type") == "contains" and str(link.get("target")) == str(node["id"])), None)
                if parent_epic_link:
                    epic_iid = self._resolve_iid(parent_epic_link.get("source"))
                    if epic_iid:
                        epic_issue = gitlab_client.get_project_issue(self.project_id, epic_iid)
                        self.reorder_list.append((new_issue, epic_issue))

            time.sleep(0.1)
        logging.info(f"Created {len(self.created_issues)} new issues.")

    def _create_links(self):
        """Creates issue links (e.g., 'contains', 'blocks') in GitLab."""
        logging.info("Step 3: Creating issue links...")
        links_to_create = [
            link for link in self.project_map.get("links", [])
            if str(link.get("source", "")).startswith("NEW_") or str(link.get("target", "")).startswith("NEW_")
        ]
        
        for link in links_to_create:
            source_iid = self._resolve_iid(link.get("source"))
            target_iid = self._resolve_iid(link.get("target"))
            link_type = link.get("type")

            if not (source_iid and target_iid and link_type):
                continue

            try:
                if link_type == "contains":
                    gitlab_client.create_issue_link(self.project_id, source_iid, target_iid)
                    self.links_created_count += 1
                    logging.info(f"  - Linked epic #{source_iid} to story #{target_iid}")
                
                elif link_type == "blocks":
                    # Per project convention for GitLab CE, "blocking" is handled by comments,
                    # not native links which are a premium feature.
                    # gitlab_client.create_issue_link(self.project_id, source_iid, target_iid, link_type='blocks')
                    
                    # Add a "Blocked by" comment to the target issue
                    note_body = f"Blocked by #{source_iid}"
                    gitlab_client.create_issue_note(self.project_id, target_iid, {'body': note_body})
                    
                    # We still consider this a "link" in the context of our project map
                    self.links_created_count += 1
                    logging.info(f"  - Created 'blocks' relationship via comment on issue #{target_iid} (blocked by #{source_iid})")

                time.sleep(0.1)

            except gitlab.exceptions.GitlabError as e:
                if hasattr(e, 'response_code') and e.response_code == 409:
                    logging.warning(f"Link from #{source_iid} to #{target_iid} already exists. Skipping.")
                else:
                    raise
        logging.info(f"Created {self.links_created_count} new issue links.")

    def _update_project_map_iids(self):
        """Updates the 'NEW_' IIDs in project_map.yaml with real GitLab IIDs."""
        if not self.new_issue_id_map:
            logging.info("No new issues were created, skipping project map update.")
            return
            
        logging.info("Step 4: Updating project_map.yaml with new IIDs...")
        with open(PROJECT_MAP_PATH, 'r') as f:
            data = self.yaml.load(f)

        def recursive_update(node):
            if isinstance(node, dict):
                if 'id' in node and node['id'] in self.new_issue_id_map:
                    node['id'] = self.new_issue_id_map[node['id']]
                if 'source' in node and node['source'] in self.new_issue_id_map:
                    node['source'] = self.new_issue_id_map[node['source']]
                if 'target' in node and node['target'] in self.new_issue_id_map:
                    node['target'] = self.new_issue_id_map[node['target']]
                
                for value in node.values():
                    recursive_update(value)
            elif isinstance(node, list):
                for item in node:
                    recursive_update(item)

        recursive_update(data)
        
        with open(PROJECT_MAP_PATH, 'w') as f:
            self.yaml.dump(data, f)
        logging.info("Project map updated successfully.")

    # ---------------------------------------------------------------------------
    # KRITIKUS DOKUMENTÁCIÓ A REGRESSZIÓ MEGELŐZÉSÉRE
    # ---------------------------------------------------------------------------
    # FIGYELEM: Issue-k újrarendezése egy GitLab Board List-en belül
    # KIZÁRÓLAG a BoardList.reorder() metódussal történhet.
    #
    # TILOS a ProjectIssue.move() metódust használni erre a célra!
    #
    # A `move()` metódus a issue-k globális sorrendjét vagy a projektek
    # közötti mozgatását kezeli, és inkonzisztens viselkedést vagy hibát
    # okoz, ha egy board listán belüli sorrend módosítására használjuk.
    #
    # A helyes implementáció a `gitlab_client.reorder_issues_in_board_list()`
    # függvényben van enkapszulálva. MINDIG EZT A FÜGGVÉNYT KELL HASZNÁLNI.
    # ---------------------------------------------------------------------------
    def _reorder_stories_on_board(self):
        """
        Reorders newly created stories under their parent epics on a GitLab board
        by calling the safe, encapsulated reorder function in gitlab_client.
        """
        if not self.config.board_id:
            logging.info("No board_id configured. Skipping story reordering.")
            return
        if not self.reorder_list:
            logging.info("No stories to reorder.")
            return

        logging.info("Step 5: Reordering stories on board...")
        board = gitlab_client.get_project_board(self.project_id)
        if not board:
            logging.warning(f"Board with ID {self.config.board_id} not found in project {self.project_id}. Skipping reordering.")
            return
            
        board_lists = board.lists.list(all=True)
        
        for story_issue, epic_issue in self.reorder_list:
            backbone_label = next((l for l in story_issue.labels if l.startswith("Backbone::")), None)
            if not backbone_label:
                logging.warning(f"Story #{story_issue.iid} has no 'Backbone::' label. Cannot determine target list.")
                continue

            target_list_obj = next((bl for bl in board_lists if bl.label and bl.label['name'] == backbone_label), None)
            if not target_list_obj:
                logging.warning(f"No board list found for label '{backbone_label}'. Skipping reordering for story #{story_issue.iid}.")
                continue

            # Ensure the epic has the correct backbone label so it appears in the same list
            if backbone_label not in epic_issue.labels:
                logging.info(f"Epic #{epic_issue.iid} is missing label '{backbone_label}'. Adding it now.")
                epic_issue.labels.append(backbone_label)
                epic_issue.save()
                time.sleep(0.1)

            try:
                logging.info(f"  - Reordering story #{story_issue.iid} to be after epic #{epic_issue.iid} in list '{target_list_obj.label['name']}'.")
                
                # Correctly call the new client function with the story's IID and the epic's global ID.
                gitlab_client.move_issue_in_board_list(
                    project_id=self.project_id,
                    issue_iid=story_issue.iid,
                    move_before_id=epic_issue.id  # Use the global ID as required
                )
                
                logging.info(f"  - Successfully reordered story #{story_issue.iid}.")
                time.sleep(0.1)

            except gitlab.exceptions.GitlabError as e:
                logging.error(f"Failed to reorder story #{story_issue.iid}: {e}")
            except Exception as e:
                logging.error(f"An unexpected error occurred during reordering of story #{story_issue.iid}: {e}", exc_info=True)

    def _read_description_from_md_file(self, local_path: str) -> str:
        """Reads the description content from a markdown file, skipping the frontmatter."""
        try:
            full_path = DATA_DIR / local_path
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            match = re.search(r'---\s*\n.*?\n---\s*\n(.*)', content, re.DOTALL)
            return match.group(1).strip() if match else content
        except (FileNotFoundError, Exception) as e:
            logging.warning(f"Could not read description from {local_path}: {e}")
            return ""

    def _resolve_iid(self, issue_id) -> int | None:
        """
        Resolves an ID from the project map into a usable IID.
        - If it's a "NEW_..." string, it looks up the IID of the newly created issue.
        - If it's an integer, it's assumed to be a valid IID already.
        """
        if issue_id is None: return None
        
        if isinstance(issue_id, str) and issue_id.startswith("NEW_"):
            return self.new_issue_id_map.get(issue_id)
        
        try:
            # If it's an integer, we assume it's already the correct IID.
            return int(issue_id)
        except (ValueError, TypeError):
            logging.warning(f"Could not resolve issue ID: {issue_id}")
            return None

def upload_artifacts_to_gitlab(project_id: str, project_map: dict) -> dict:
    """
    Initializes the uploader and starts the upload process.
    This function serves as the main entry point.
    """
    uploader = GitlabUploader(project_id, project_map)
    return uploader.upload()