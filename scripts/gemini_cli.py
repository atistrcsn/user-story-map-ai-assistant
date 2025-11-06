import typer
import yaml
import os
import glob
import gitlab_service
import ai_service
from rich.console import Console
from rich.pretty import pprint
import re
import unicodedata

app = typer.Typer()

# --- Absolute Path Definitions ---
# Define the project root by going up one level from the script's directory (/scripts)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Define absolute paths for all key locations
PROJECT_MAP_PATH = os.path.join(PROJECT_ROOT, "project_map.yaml")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
DATA_DIR = os.path.join(PROJECT_ROOT, "gitlab_data")
# --- End of Path Definitions ---

def _get_context_from_docs() -> list[dict]:
    """Gathers context from all markdown files in the docs directory."""
    sources = []
    for filepath in glob.glob(f"{DOCS_DIR}/**/*.md", recursive=True):
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
    if not os.path.exists(PROJECT_MAP_PATH):
        return sources
    
    with open(PROJECT_MAP_PATH, 'r') as f:
        project_map = yaml.safe_load(f)
    
    for node in project_map.get("nodes", []):
        # Only include nodes that have a numeric IID (i.e., they exist on GitLab)
        if isinstance(node.get("id"), int):
            summary = node.get("title", "No title")
            path = os.path.join("gitlab_data", node.get("local_path", ""))
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
    Generates local .md files and updates the project_map.yaml based on the AI plan,
    skipping any issues that already exist.
    """
    console.print("\n[bold green]Plan approved. Generating local files...[/bold green]")
    
    if not os.path.exists(PROJECT_MAP_PATH):
        project_map = {"nodes": [], "links": []}
    else:
        with open(PROJECT_MAP_PATH, 'r') as f:
            project_map = yaml.safe_load(f)

    existing_titles = {node['title'] for node in project_map.get("nodes", [])}
    new_nodes, new_links, skipped_count = [], [], 0

    for issue in plan.get("proposed_issues", []):
        title = issue["title"]
        if title in existing_titles:
            console.print(f"[yellow]Warning: Issue '{title}' already exists. Skipping.[/yellow]")
            skipped_count += 1
            continue

        temp_id = issue["id"]
        frontmatter = {"iid": temp_id, "title": title, "state": "opened", "labels": issue.get("labels", [])}
        markdown_content = f"---\n{yaml.dump(frontmatter, sort_keys=False)}---\n\n{issue.get('description', '')}\n"
        
        # Use the centralized function from gitlab_service
        relative_filepath = gitlab_service.get_issue_filepath(issue.get("title"), issue.get("labels", []))
        if not relative_filepath:
            relative_filepath = os.path.join("_unassigned", f"{_slugify(issue.get('title'))}.md")

        full_filepath = os.path.join(DATA_DIR, relative_filepath)
        os.makedirs(os.path.dirname(full_filepath), exist_ok=True)
        with open(full_filepath, 'w', encoding='utf-8') as f: f.write(markdown_content)
        console.print(f"  - Created file: {full_filepath}")

        new_node = {"id": temp_id, "title": title, "type": "Issue", "state": "opened", "labels": issue.get("labels", []), "local_path": relative_filepath}
        new_nodes.append(new_node)
        
        dependencies = issue.get("dependencies", {})
        # Ensure dependencies is a dict before checking for keys
        if dependencies and "blocks" in dependencies:
            # Handle cases where 'blocks' might be a single item, not a list
            target_ids = dependencies["blocks"]
            if not isinstance(target_ids, list):
                target_ids = [target_ids]
            for target_id in target_ids:
                new_links.append({"source": temp_id, "target": target_id, "type": "blocks"})

        if dependencies and "is_blocked_by" in dependencies:
            # Handle cases where 'is_blocked_by' might be a single item, not a list
            blocker_ids = dependencies["is_blocked_by"]
            if not isinstance(blocker_ids, list):
                blocker_ids = [blocker_ids]
            for blocker_id in blocker_ids:
                new_links.append({"source": blocker_id, "target": temp_id, "type": "blocks"})

    if skipped_count == len(plan.get("proposed_issues", [])):
        console.print("[bold yellow]All proposed issues already exist. No changes made.[/bold yellow]")
        return

    project_map["nodes"].extend(new_nodes)
    if "links" not in project_map: project_map["links"] = []
    project_map["links"].extend(new_links)

    with open(PROJECT_MAP_PATH, 'w') as f: yaml.dump(project_map, f, sort_keys=False)
    console.print(f"[green]✓ Project map updated with {len(new_nodes)} new issues and {len(new_links)} new links.[/green]")

def _upload_to_gitlab(plan: dict, console: Console):
    """Placeholder function for uploading artifacts to GitLab."""
    console.print("\n[bold green]Uploading artifacts to GitLab...[/bold green]")
    # In a real implementation, this would call gitlab_service.upload_artifacts_to_gitlab
    pprint(plan)
    console.print("[yellow]GitLab upload is not yet implemented.[/yellow]")


@app.command("create-feature")
def create_feature(
    feature_description: str = typer.Argument(..., help="A high-level description of the new feature."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run the process without uploading to GitLab."),
    mock_ai: bool = typer.Option(False, "--mock-ai", help="Use a mocked AI response for testing.")
):
    """
    Initiates the AI-assisted workflow to create a new feature.
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
        with open(PROJECT_MAP_PATH, 'w') as f:
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
        console.print(f"[green]✓ AI identified {len(relevant_files)} relevant files.[/green]")
    else:
        console.print("[yellow]Warning: AI could not identify relevant context files.[/yellow]")

    # Step 4: Read relevant content
    context_content = ""
    if relevant_files:
        with console.status("[bold green]Reading content of relevant files...[/bold green]"):
            contents = []
            # Get the project root directory (assuming the script is in a subdirectory like /scripts)
            project_root = os.path.dirname(os.path.abspath(__file__))
            
            for file_path in relevant_files:
                # Construct an absolute path from the project root
                absolute_path = os.path.join(project_root, '..', file_path)
                try:
                    with open(absolute_path, 'r', encoding='utf-8') as f:
                        contents.append(f"---\nFile: {file_path}\nContent: {f.read()}\n---")
                except FileNotFoundError:
                    console.print(f"[yellow]Warning: Could not find file {absolute_path}. Skipping.[/yellow]")
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not read file {absolute_path} due to {e}. Skipping.[/yellow]")
            context_content = "\n".join(contents)
    
    # Step 5: AI Deep Analysis
    with console.status("[bold green]Sending to AI for deep analysis to generate plan...[/bold green]"):
        # Gather existing issues (title and labels) to help AI avoid duplicates and reuse epics
        existing_issues_context = []
        if os.path.exists(PROJECT_MAP_PATH):
            with open(PROJECT_MAP_PATH, 'r') as f:
                project_map = yaml.safe_load(f)
                if project_map and "nodes" in project_map:
                    for node in project_map["nodes"]:
                        existing_issues_context.append({
                            "title": node.get("title"),
                            "labels": node.get("labels", [])
                        })

        plan = ai_service.generate_implementation_plan(
            feature_description, context_content, existing_issues_context, mock_ai
        )

    console.print("\n[bold green]✓ AI generated the following implementation plan:[/bold green]")
    
    if not plan or not plan.get("proposed_issues"):
        console.print("[bold red]Error: The AI did not generate a valid plan.[/bold red]")
        raise typer.Exit(1)
        
    pprint(plan)

    # Step 6: Structured Dialogue (User Confirmation)
    console.print("\n")
    approved = typer.confirm("Do you approve this implementation plan?", abort=True)
    
    if approved:
        # Step 7: Local Generation
        _generate_local_files(plan, console)

        # Step 8: Conditional Upload to GitLab
        if dry_run:
            console.print("\n[bold yellow]--dry-run enabled. Skipping GitLab upload.[/bold yellow]")
        else:
            _upload_to_gitlab(plan, console)
    
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
    with open(PROJECT_MAP_PATH, 'w') as f:
        yaml.dump(map_data, f, sort_keys=False)

    console.print(f"[green]✓ Project map successfully built with {result['issues_found']} issues and saved to {PROJECT_MAP_PATH}.[/green]")

if __name__ == "__main__":
    app()