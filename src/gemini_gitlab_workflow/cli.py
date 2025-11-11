from dotenv import load_dotenv
load_dotenv()

import typer
import yaml
import os
import glob
from gemini_gitlab_workflow import gitlab_service
from gemini_gitlab_workflow import ai_service
from gemini_gitlab_workflow.sanitizer import Sanitizer
from rich.console import Console
from rich.pretty import pprint
import re
from gemini_gitlab_workflow import config
import unicodedata
from pathlib import Path

app = typer.Typer()
sanitizer = Sanitizer() # Instantiate the sanitizer globally or pass it around

@app.command()
def init():
    """
    Initializes the current directory for use with ggw by creating a .env file.
    """
    console = Console()
    env_path = config.PROJECT_ROOT / ".env"

    if os.path.exists(env_path):
        console.print(f"[bold yellow]Warning:[/] '.env' file already exists at {env_path}. No changes were made.")
        raise typer.Exit()

    env_content = """# GitLab API Configuration
GGW_GITLAB_URL="https://gitlab.com"
GGW_GITLAB_PRIVATE_TOKEN=""
GGW_GITLAB_PROJECT_ID=""

# Gemini API Configuration
GEMINI_WORKER_API_KEY=""

# Optional: Specify the directory for GitLab data relative to the project root.
# Defaults to "gitlab_data" if not set.
# GGW_DATA_DIR="gitlab_data"
"""
    try:
        with open(env_path, "w") as f:
            f.write(env_content)
        console.print(f"[green]✓[/] Successfully created '.env' file at {env_path}")
        console.print("Please edit the '.env' file to add your GitLab and Gemini API credentials.")
    except IOError as e:
        console.print(f"[bold red]Error:[/] Failed to create '.env' file: {e}")
        raise typer.Exit(1)

def _get_context_from_docs() -> list[dict]:
    """Gathers context from all markdown files in the docs directory."""
    sources = []
    for filepath in glob.glob(f"{config.DOCS_DIR}/**/*.md", recursive=True):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                summary = f.readline().strip().replace('#', '').strip()
            sources.append({"path": filepath, "summary": summary})
        except Exception:
            continue
    return sources

def _get_context_from_project_map() -> list[dict]:
    """
    Gathers context from the project_map.yaml file, including only issues
    that have a real, numeric GitLab IID.
    """
    sources = []
    if not os.path.exists(config.PROJECT_MAP_PATH):
        return sources
    
    with open(config.PROJECT_MAP_PATH, 'r') as f:
        project_map = yaml.safe_load(f)
    
    for node in project_map.get("nodes", []):
        # Only include nodes that have a numeric IID (i.e., they exist on GitLab)
        if isinstance(node.get("id"), int):
            summary = node.get("title", "No title")
            relative_path = node.get("local_path")
            if relative_path:
                # Always construct an absolute path
                path = config.DATA_DIR / relative_path
                sources.append({"path": path, "summary": summary})
        
    return sources

def _slugify(text):
    """Convert text to a URL-friendly slug, handling accented characters."""
    text = str(text) # Ensure text is string
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'--+', '-', text)
    return text.strip('-')

# ... (rest of _get_context functions)

def _generate_local_files(plan: dict, console: Console):
    """
    Generates local .md files and updates project_map.yaml based on the AI plan.
    This function uses a two-pass approach to correctly place new stories
    under their corresponding new epics and create the 'contains' link.
    """
    console.print("\n[bold green]Plan approved. Generating local files...[/bold green]")
    
    if not os.path.exists(config.PROJECT_MAP_PATH):
        project_map = {"nodes": [], "links": []}
    else:
        with open(config.PROJECT_MAP_PATH, 'r') as f:
            project_map = yaml.safe_load(f)

    existing_titles = {node['title'] for node in project_map.get("nodes", [])}
    new_nodes, new_links, skipped_count = [], [], 0
    
    proposed_issues = plan.get("proposed_issues", [])
    if not proposed_issues:
        console.print("[yellow]Warning: No new issues proposed in the plan.[/yellow]")
        return

    # --- Pass 1: Map out new epics: their paths and temporary IDs ---
    new_epic_map = {} # Maps 'Epic::<name>' label to a dict with {'path': ..., 'id': ...}
    for issue in proposed_issues:
        labels = issue.get("labels", [])
        if "Type::Epic" in labels:
            epic_dir_path_str = gitlab_service.get_issue_filepath(issue.get("title"), labels)
            if epic_dir_path_str:
                temp_epic_label = next((l for l in labels if l.startswith("Epic::")), None)
                if temp_epic_label:
                    new_epic_map[temp_epic_label] = {
                        "path": Path(os.path.dirname(epic_dir_path_str)),
                        "id": issue["id"]
                    }

    # --- Pass 2: Generate all files, creating 'contains' links for stories ---
    for issue in proposed_issues:
        title = issue["title"]
        if title in existing_titles:
            console.print(f"[yellow]Warning: Issue '{title}' already exists. Skipping.[/yellow]")
            skipped_count += 1
            continue

        temp_id = issue["id"]
        labels = issue.get("labels", [])
        relative_filepath = None

        # If it's a story, try to find its parent epic's path and ID from our map
        if "Type::Story" in labels:
            temp_epic_label = next((l for l in labels if l.startswith("Epic::")), None)
            if temp_epic_label and temp_epic_label in new_epic_map:
                parent_epic_info = new_epic_map[temp_epic_label]
                parent_epic_path = parent_epic_info["path"]
                parent_epic_id = parent_epic_info["id"]

                story_filename = f"story-{_slugify(title)}.md"
                relative_filepath = parent_epic_path / story_filename
                console.print(f"[DIAG] Story '{title}' mapped to new Epic path: {relative_filepath}")
                
                # CRITICAL FIX: Create the 'contains' link
                new_links.append({"source": parent_epic_id, "target": temp_id, "type": "contains"})
                console.print(f"[DIAG] Created 'contains' link from Epic '{parent_epic_id}' to Story '{temp_id}'")


        # If path wasn't determined above, use the default logic
        if not relative_filepath:
            relative_filepath_str = gitlab_service.get_issue_filepath(title, labels)
            if relative_filepath_str:
                relative_filepath = Path(relative_filepath_str)

        if not relative_filepath: # Fallback for unassigned items
            relative_filepath = Path("_unassigned") / f"{_slugify(title)}.md"

        # Create file and node
        frontmatter = {"iid": temp_id, "title": title, "state": "opened", "labels": labels}
        markdown_content = f"---\n{yaml.dump(frontmatter, sort_keys=False)}---\n\n{issue.get('description', '')}\n"
        full_filepath = config.DATA_DIR / relative_filepath
        full_filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(full_filepath, 'w', encoding='utf-8') as f: f.write(markdown_content)
        console.print(f"  - Created file: {full_filepath}")

        new_node = {"id": temp_id, "title": title, "type": "Issue", "state": "opened", "labels": labels, "local_path": str(relative_filepath), "description": issue.get('description', '')}
        new_nodes.append(new_node)
        
        # Handle dependencies (unchanged)
        dependencies = issue.get("dependencies", {})
        if dependencies and "blocks" in dependencies:
            target_ids = dependencies["blocks"]
            if not isinstance(target_ids, list): target_ids = [target_ids]
            for target_id in target_ids: new_links.append({"source": temp_id, "target": target_id, "type": "blocks"})
        if dependencies and "is_blocked_by" in dependencies:
            blocker_ids = dependencies["is_blocked_by"]
            if not isinstance(blocker_ids, list): blocker_ids = [blocker_ids]
            for blocker_id in blocker_ids: new_links.append({"source": blocker_id, "target": temp_id, "type": "blocks"})

    if skipped_count == len(proposed_issues):
        console.print("[bold yellow]All proposed issues already exist. No changes made.[/bold yellow]")
        return

    project_map["nodes"].extend(new_nodes)
    if "links" not in project_map: project_map["links"] = []
    project_map["links"].extend(new_links)

    with open(config.PROJECT_MAP_PATH, 'w') as f: yaml.dump(project_map, f, sort_keys=False)
    console.print(f"[green]✓ Project map updated with {len(new_nodes)} new issues and {len(new_links)} new links.[/green]")


@app.command("create-feature")
def create_feature(
    feature_description: str = typer.Argument(..., help="A high-level description of the new feature."),
    mock_ai: bool = typer.Option(False, "--mock-ai", help="Use a mocked AI response for testing.")
):
    """
    Initiates the AI-assisted workflow to create a new feature by generating local story map files.
    Use the `gemini-cli upload story-map` command to push these changes to GitLab.
    """
    console = Console()
    
    console.print(f"[bold]Starting AI-assisted creation for feature:[/bold] '{feature_description}'")
    
    # Step 1: Smart Sync and build project map
    with console.status("[bold green]Performing smart sync and rebuilding project map...[/bold green]"):
        # First, ensure the cache is up-to-date
        gitlab_service.smart_sync()
        
        # Always rebuild the map and local files to ensure consistency
        build_result = gitlab_service.build_project_map()
        if build_result["status"] == "error":
            console.print(f"[bold red]Error rebuilding project map:[/bold red] {build_result['message']}")
            raise typer.Exit(1)
        with open(config.PROJECT_MAP_PATH, 'w') as f:
            yaml.dump(build_result["map_data"], f, sort_keys=False)
    console.print("[green]✓ Project map is up-to-date and local files are consistent.[/green]")

    # Step 2: Gather context
    with console.status("[bold green]Gathering context sources...[/bold green]"):
        all_sources = _get_context_from_docs() + _get_context_from_project_map()
    console.print(f"Found {len(all_sources)} potential context sources.")

    # Step 3: AI Pre-filtering
    with console.status("[bold green]Sending to AI for pre-filtering analysis...[/bold green]"):
        relevant_files = ai_service.get_relevant_context_files(feature_description, all_sources, mock_ai)
    if relevant_files:
        console.print(f"[green]✓ AI identified {len(relevant_files)} relevant files:[/green]")
        for file_path in relevant_files:
            console.print(f"  - {file_path}")
    else:
        console.print("[yellow]Warning: AI could not identify relevant context files.[/yellow]")

    # Step 4: Read relevant content
    context_content = ""
    if relevant_files:
        with console.status("[bold green]Reading content of relevant files...[/bold green]"):
            contents = []
            for file_path_str in relevant_files:
                # --- Robust Path Resolution (v3 using pathlib) ---
                file_path = Path(file_path_str)
                
                # If the path is not absolute, resolve it relative to the project root.
                if not file_path.is_absolute():
                    absolute_path = config.PROJECT_ROOT / file_path
                else:
                    absolute_path = file_path

                # Security check: ensure the final path is within the project directory.
                try:
                    safe_path = absolute_path.resolve(strict=True)
                    if not safe_path.is_relative_to(config.PROJECT_ROOT.resolve(strict=True)):
                        console.print(f"[yellow]Warning: Skipping file outside project directory: {file_path_str}[/yellow]")
                        continue
                except (FileNotFoundError, RuntimeError): # RuntimeError for symlink loops
                     console.print(f"[yellow]Warning: Skipping invalid or non-existent file path: {file_path_str}[/yellow]")
                     continue

                try:
                    with open(safe_path, 'r', encoding='utf-8') as f:
                        # Use the original file_path for the log message for consistency
                        contents.append(f"---\nFile: {file_path_str}\nContent: {f.read()}\n---")
                except FileNotFoundError:
                    # Use the original file_path in the warning message
                    console.print(f"[yellow]Warning: Could not find file {file_path_str}. Skipping.[/yellow]")
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not read file {file_path_str} due to {e}. Skipping.[/yellow]")
            context_content = "\n".join(contents)
    
    # Step 5: AI Deep Analysis
    with console.status("[bold green]Sending to AI for deep analysis to generate plan...[/bold green]"):
        # Gather existing issues (title and labels) to help AI avoid duplicates and reuse epics
        existing_issues_context = []
        if os.path.exists(config.PROJECT_MAP_PATH):
            with open(config.PROJECT_MAP_PATH, 'r') as f:
                project_map = yaml.safe_load(f)
                if project_map and "nodes" in project_map:
                    for node in project_map["nodes"]:
                        existing_issues_context.append({
                            "title": node.get("title"),
                            "labels": node.get("labels", []),
                            "state": node.get("state")
                        })

        # Anonymize context before sending to AI
        anonymized_feature_description = sanitizer.anonymize_text(feature_description)
        anonymized_context_content = sanitizer.anonymize_text(context_content)
        
        anonymized_existing_issues = []
        for issue in existing_issues_context:
            anonymized_issue = {
                "title": sanitizer.anonymize_text(issue.get("title", "")),
                "labels": [sanitizer.anonymize_text(label) for label in issue.get("labels", [])],
                "state": issue.get("state")
            }
            anonymized_existing_issues.append(anonymized_issue)

        plan = ai_service.generate_implementation_plan(
            anonymized_feature_description, anonymized_context_content, anonymized_existing_issues, mock_ai
        )

    # Deanonymize the response from AI
    if plan and plan.get("proposed_issues"):
        for issue in plan["proposed_issues"]:
            issue["title"] = sanitizer.deanonymize_text(issue.get("title", ""))
            issue["description"] = sanitizer.deanonymize_text(issue.get("description", ""))
            issue["labels"] = [sanitizer.deanonymize_text(label) for label in issue.get("labels", [])]

    console.print("\n[bold green]✓ AI generated the following implementation plan:[/bold green]")
    
    if not plan or not plan.get("proposed_issues"):
        console.print("[green]✓ The AI has determined that this feature is already covered by existing issues. No new plan was generated.[/green]")
        return # Exit successfully, as no new plan is needed
        
    pprint(plan)

    # Step 6: Structured Dialogue (User Confirmation)
    console.print("\n")
    approved = typer.confirm("Do you approve this implementation plan?", abort=True)
    
    if approved:
        # Step 7: Local Generation
        _generate_local_files(plan, console)
    
    console.print("\n[bold]Workflow finished.[/bold]")


sync_app = typer.Typer()
app.add_typer(sync_app, name="sync", help="Synchronize data from GitLab.")

@sync_app.command("map")
def sync_map():
    """Synchronize GitLab issues and build the project map."""
    console = Console()
    with console.status("[bold green]Synchronizing with GitLab and building project map...[/bold green]"):
        result = gitlab_service.build_project_map()

    if result["status"] == "error":
        console.print(f"[bold red]Error building project map:[/bold red] {result['message']}")
        raise typer.Exit(1)

    map_data = result["map_data"]
    with open(config.PROJECT_MAP_PATH, 'w') as f:
        yaml.dump(map_data, f, sort_keys=False)

    console.print(f"[green]✓ Project map successfully built with {result['issues_found']} issues and saved to {config.PROJECT_MAP_PATH}.[/green]")


upload_app = typer.Typer()
app.add_typer(upload_app, name="upload", help="Upload artifacts to GitLab.")

@upload_app.command("story-map")
def upload_story_map():
    """
    Uploads the locally generated story map (from project_map.yaml) to GitLab.
    """
    console = Console()
    console.print("[bold]Initiating upload of story map to GitLab...[/bold]")

    if not os.path.exists(config.PROJECT_MAP_PATH):
        console.print(f"[bold red]Error:[/bold red] {config.PROJECT_MAP_PATH} not found. Please generate a story map first using 'gemini-cli create-feature'.")
        raise typer.Exit(1)

    try:
        with open(config.PROJECT_MAP_PATH, 'r') as f:
            project_map = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to read {config.PROJECT_MAP_PATH}: {e}")
        raise typer.Exit(1)

    with console.status("[bold green]Uploading artifacts to GitLab...[/bold green]"):
        upload_result = gitlab_service.upload_artifacts_to_gitlab(project_map)

    if upload_result["status"] == "success":
        console.print("[green]✓ Story map successfully uploaded to GitLab![/green]")
        console.print(f"  Labels created: {upload_result['labels_created']}")
        console.print(f"  Issues created: {upload_result['issues_created']}")
        console.print(f"  Notes with links created: {upload_result['notes_with_links_created']}")
        console.print(f"  Issue links created: {upload_result['issue_links_created']}")
    else:
        console.print(f"[bold red]Error uploading story map:[/bold red] {upload_result['message']}")
        raise typer.Exit(1)

    console.print("\n[bold]Upload workflow finished.[/bold]")

if __name__ == "__main__":
    app()