import typer
import yaml
import os
import glob
import re
import unicodedata
from rich.console import Console
from rich.pretty import pprint

# Use relative imports within the package
from . import gitlab_service
from . import ai_service
from . import config

app = typer.Typer()

# --- Path Definitions are now handled by config.py ---

def _get_context_from_docs() -> list[dict]:
    """Gathers context from all markdown files in the docs directory."""
    # Note: This function assumes a 'docs' folder in the project root.
    # This could also be made configurable in the future.
    docs_dir = os.path.join(config.PROJECT_ROOT, "docs")
    sources = []
    if not os.path.exists(docs_dir):
        return sources
        
    for filepath in glob.glob(f"{docs_dir}/**/*.md", recursive=True):
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
    project_map_path = config.get_project_map_path()
    data_dir = config.get_data_dir()
    sources = []
    if not os.path.exists(project_map_path):
        return sources
    
    with open(project_map_path, 'r') as f:
        project_map = yaml.safe_load(f)
    
    for node in project_map.get("nodes", []):
        if isinstance(node.get("id"), int):
            summary = node.get("title", "No title")
            relative_path = node.get("local_path")
            if relative_path:
                path = os.path.join(data_dir, relative_path)
                sources.append({"path": path, "summary": summary})
        
    return sources

def _slugify(text):
    """Convert text to a URL-friendly slug."""
    text = str(text)
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'--+', '-', text)
    return text.strip('-')

def _generate_local_files(plan: dict, console: Console):
    """
    Generates local .md files and updates project_map.yaml based on the AI plan.
    """
    console.print("\n[bold green]Plan approved. Generating local files...[/bold green]")
    
    project_map_path = config.get_project_map_path()
    data_dir = config.get_data_dir()
    
    if not os.path.exists(project_map_path):
        project_map = {"nodes": [], "links": []}
    else:
        with open(project_map_path, 'r') as f:
            project_map = yaml.safe_load(f)

    existing_titles = {node['title'] for node in project_map.get("nodes", [])}
    new_nodes, new_links, skipped_count = [], [], 0
    
    proposed_issues = plan.get("proposed_issues", [])
    if not proposed_issues:
        console.print("[yellow]Warning: No new issues proposed in the plan.[/yellow]")
        return

    new_epic_map = {}
    epic_type_name = config.settings['labels']['epic_type_name']
    story_type_name = config.settings['labels']['story_type_name']

    for issue in proposed_issues:
        labels = issue.get("labels", [])
        if epic_type_name in labels:
            epic_dir_path_str = gitlab_service.get_issue_filepath(issue.get("title"), labels)
            if epic_dir_path_str:
                temp_epic_label = next((l for l in labels if l.startswith("Epic::")), None)
                if temp_epic_label:
                    new_epic_map[temp_epic_label] = {
                        "path": os.path.dirname(epic_dir_path_str),
                        "id": issue["id"]
                    }

    for issue in proposed_issues:
        title = issue["title"]
        if title in existing_titles:
            console.print(f"[yellow]Warning: Issue '{title}' already exists. Skipping.[/yellow]")
            skipped_count += 1
            continue

        temp_id = issue["id"]
        labels = issue.get("labels", [])
        relative_filepath = None

        if story_type_name in labels:
            temp_epic_label = next((l for l in labels if l.startswith("Epic::")), None)
            if temp_epic_label and temp_epic_label in new_epic_map:
                parent_epic_info = new_epic_map[temp_epic_label]
                parent_epic_path = parent_epic_info["path"]
                parent_epic_id = parent_epic_info["id"]
                story_filename = f"story-{_slugify(title)}.md"
                relative_filepath = os.path.join(parent_epic_path, story_filename)
                new_links.append({"source": parent_epic_id, "target": temp_id, "type": "contains"})

        if not relative_filepath:
            relative_filepath = gitlab_service.get_issue_filepath(title, labels)
        
        if not relative_filepath:
            relative_filepath = os.path.join("_unassigned", f"{_slugify(title)}.md")

        frontmatter = {"iid": temp_id, "title": title, "state": "opened", "labels": labels}
        markdown_content = f"---\n{yaml.dump(frontmatter, sort_keys=False)}---\n\n{issue.get('description', '')}\n"
        full_filepath = os.path.join(data_dir, relative_filepath)
        os.makedirs(os.path.dirname(full_filepath), exist_ok=True)
        with open(full_filepath, 'w', encoding='utf-8') as f: f.write(markdown_content)
        console.print(f"  - Created file: {full_filepath}")

        new_node = {"id": temp_id, "title": title, "type": "Issue", "state": "opened", "labels": labels, "local_path": relative_filepath, "description": issue.get('description', '')}
        new_nodes.append(new_node)
        
        dependencies = issue.get("dependencies", {})
        if "blocks" in dependencies:
            for target_id in dependencies["blocks"]: new_links.append({"source": temp_id, "target": target_id, "type": "blocks"})
        if "is_blocked_by" in dependencies:
            for blocker_id in dependencies["is_blocked_by"]: new_links.append({"source": blocker_id, "target": temp_id, "type": "blocks"})

    if skipped_count == len(proposed_issues):
        console.print("[bold yellow]All proposed issues already exist. No changes made.[/bold yellow]")
        return

    project_map["nodes"].extend(new_nodes)
    if "links" not in project_map: project_map["links"] = []
    project_map["links"].extend(new_links)

    with open(project_map_path, 'w') as f: yaml.dump(project_map, f, sort_keys=False)
    console.print(f"[green]✓ Project map updated with {len(new_nodes)} new issues and {len(new_links)} new links.[/green]")

@app.command("create-feature")
def create_feature(
    feature_description: str = typer.Argument(..., help="A high-level description of the new feature."),
    mock_ai: bool = typer.Option(False, "--mock-ai", help="Use a mocked AI response for testing.")
):
    """
    Initiates the AI-assisted workflow to create a new feature by generating local story map files.
    """
    console = Console()
    project_map_path = config.get_project_map_path()
    
    console.print(f"[bold]Starting AI-assisted creation for feature:[/bold] '{feature_description}'")
    
    with console.status("[bold green]Performing smart sync and rebuilding project map...[/bold green]"):
        gitlab_service.smart_sync()
        build_result = gitlab_service.build_project_map()
        if build_result["status"] == "error":
            console.print(f"[bold red]Error rebuilding project map:[/bold red] {build_result['message']}")
            raise typer.Exit(1)
        with open(project_map_path, 'w') as f:
            yaml.dump(build_result["map_data"], f, sort_keys=False)
    console.print("[green]✓ Project map is up-to-date and local files are consistent.[/green]")

    with console.status("[bold green]Gathering context sources...[/bold green]"):
        all_sources = _get_context_from_docs() + _get_context_from_project_map()
    console.print(f"Found {len(all_sources)} potential context sources.")

    with console.status("[bold green]Sending to AI for pre-filtering analysis...[/bold green]"):
        relevant_files = ai_service.get_relevant_context_files(feature_description, all_sources, mock_ai)
    if relevant_files:
        console.print(f"[green]✓ AI identified {len(relevant_files)} relevant files:[/green]")
        for file_path in relevant_files: console.print(f"  - {file_path}")
    else:
        console.print("[yellow]Warning: AI could not identify relevant context files.[/yellow]")

    context_content = ""
    if relevant_files:
        with console.status("[bold green]Reading content of relevant files...[/bold green]"):
            contents = []
            for file_path in relevant_files:
                absolute_path = file_path
                if not os.path.isabs(absolute_path):
                    absolute_path = os.path.join(config.PROJECT_ROOT, absolute_path)
                
                safe_path = os.path.abspath(absolute_path)
                if not safe_path.startswith(str(config.PROJECT_ROOT)):
                    console.print(f"[yellow]Warning: Skipping file outside project directory: {file_path}[/yellow]")
                    continue
                try:
                    with open(safe_path, 'r', encoding='utf-8') as f:
                        contents.append(f"---\nFile: {file_path}\nContent: {f.read()}\n---")
                except FileNotFoundError:
                    console.print(f"[yellow]Warning: Could not find file {file_path}. Skipping.[/yellow]")
            context_content = "\n".join(contents)
    
    with console.status("[bold green]Sending to AI for deep analysis to generate plan...[/bold green]"):
        existing_issues_context = []
        if os.path.exists(project_map_path):
            with open(project_map_path, 'r') as f:
                project_map = yaml.safe_load(f)
                if project_map and "nodes" in project_map:
                    existing_issues_context = [
                        {"title": n.get("title"), "labels": n.get("labels", []), "state": n.get("state")}
                        for n in project_map["nodes"]
                    ]
        plan = ai_service.generate_implementation_plan(
            feature_description, context_content, existing_issues_context, mock_ai
        )

    console.print("\n[bold green]✓ AI generated the following implementation plan:[/bold green]")
    
    if not plan or not plan.get("proposed_issues"):
        console.print("[green]✓ The AI has determined that this feature is already covered by existing issues. No new plan was generated.[/green]")
        return
        
    pprint(plan)

    console.print("\n")
    approved = typer.confirm("Do you approve this implementation plan?", abort=True)
    
    if approved:
        _generate_local_files(plan, console)
    
    console.print("\n[bold]Workflow finished.[/bold]")

sync_app = typer.Typer()
app.add_typer(sync_app, name="sync", help="Synchronize data from GitLab.")

@sync_app.command("map")
def sync_map():
    """Synchronize GitLab issues and build the project map."""
    console = Console()
    project_map_path = config.get_project_map_path()
    with console.status("[bold green]Synchronizing with GitLab and building project map...[/bold green]"):
        result = gitlab_service.build_project_map()

    if result["status"] == "error":
        console.print(f"[bold red]Error building project map:[/bold red] {result['message']}")
        raise typer.Exit(1)

    with open(project_map_path, 'w') as f:
        yaml.dump(result["map_data"], f, sort_keys=False)

    console.print(f"[green]✓ Project map successfully built with {result['issues_found']} issues and saved to {project_map_path}.[/green]")

upload_app = typer.Typer()
app.add_typer(upload_app, name="upload", help="Upload artifacts to GitLab.")

@upload_app.command("story-map")
def upload_story_map():
    """
    Uploads the locally generated story map (from project_map.yaml) to GitLab.
    """
    console = Console()
    project_map_path = config.get_project_map_path()

    console.print("[bold]Initiating upload of story map to GitLab...[/bold]")

    if not os.path.exists(project_map_path):
        console.print(f"[bold red]Error:[/bold red] {project_map_path} not found. Please generate a story map first.")
        raise typer.Exit(1)

    try:
        with open(project_map_path, 'r') as f:
            project_map = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to read {project_map_path}: {e}")
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