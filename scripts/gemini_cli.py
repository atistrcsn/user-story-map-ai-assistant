import typer
import yaml
import os
import glob
import gitlab_service
import ai_service
from rich.console import Console

app = typer.Typer()

PROJECT_MAP_PATH = "project_map.yaml"
DOCS_DIR = "docs"

def _get_context_from_docs() -> list[dict]:
    """Gathers context from all markdown files in the docs directory."""
    sources = []
    for filepath in glob.glob(f"{DOCS_DIR}/**/*.md", recursive=True):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                # Use the first line as a summary/title
                summary = f.readline().strip().replace('#', '').strip()
            sources.append({"path": filepath, "summary": summary})
        except Exception:
            # Ignore files that can't be read
            continue
    return sources

def _get_context_from_project_map() -> list[dict]:
    """Gathers context from the project_map.yaml file."""
    sources = []
    if not os.path.exists(PROJECT_MAP_PATH):
        return sources
    
    with open(PROJECT_MAP_PATH, 'r') as f:
        project_map = yaml.safe_load(f)
    
    for node in project_map.get("nodes", []):
        summary = node.get("title", "No title")
        path = os.path.join("gitlab_data", node.get("local_path", ""))
        sources.append({"path": path, "summary": summary})
        
    return sources

@app.command("create-feature")
def create_feature(
    feature_description: str = typer.Argument(..., help="A high-level description of the new feature.")
):
    """
    Initiates the AI-assisted workflow to create a new feature, starting with context pre-filtering.
    """
    console = Console()
    
    console.print(f"[bold]Starting AI-assisted creation for feature:[/bold] '{feature_description}'")
    
    # Step 1: Smart Sync to ensure the project map is up-to-date
    with console.status("[bold green]Performing smart sync with GitLab...[/bold green]"):
        sync_result = gitlab_service.smart_sync()
        if sync_result["status"] == "error":
            console.print(f"[bold red]Error during sync:[/bold red] {sync_result['message']}")
            raise typer.Exit(1)
    
    if sync_result["updated_count"] > 0:
        with console.status("[bold green]Sync complete. Rebuilding project map...[/bold green]"):
            build_result = gitlab_service.build_project_map()
            if build_result["status"] == "error":
                console.print(f"[bold red]Error rebuilding project map:[/bold red] {build_result['message']}")
                raise typer.Exit(1)
            with open(PROJECT_MAP_PATH, 'w') as f:
                yaml.dump(build_result["map_data"], f, sort_keys=False)
        console.print("[green]✓ Project map updated.[/green]")
    else:
        console.print("[green]✓ Project map is already up-to-date.[/green]")

    # Step 2: Gather all potential context sources
    with console.status("[bold green]Gathering all potential context sources...[/bold green]"):
        doc_sources = _get_context_from_docs()
        map_sources = _get_context_from_project_map()
        all_sources = doc_sources + map_sources
    console.print(f"Found {len(all_sources)} potential context sources.")

    # Step 3: Call AI service for pre-filtering
    with console.status("[bold green]Sending context to AI for pre-filtering analysis...[/bold green]"):
        relevant_files = ai_service.get_relevant_context_files(feature_description, all_sources)

    if not relevant_files:
        console.print("[yellow]Warning: The AI could not identify any relevant context files. Deep analysis will proceed without file context.[/yellow]")
    else:
        console.print("[bold green]✓ AI pre-filtering complete. Most relevant files:[/bold green]")
        for file_path in relevant_files:
            console.print(f"  - {file_path}")
            
    # Step 4: Read content of relevant files for deep analysis
    context_content = ""
    if relevant_files:
        with console.status("[bold green]Reading content of relevant files...[/bold green]"):
            contents = []
            for file_path in relevant_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        contents.append(f"---\nFile: {file_path}\nContent: {f.read()}\n---")
                except Exception:
                    console.print(f"[yellow]Warning: Could not read file {file_path}. Skipping.[/yellow]")
            context_content = "\n".join(contents)
    
    # Step 5: Call AI service for deep analysis
    with console.status("[bold green]Sending context to AI for deep analysis to generate plan...[/bold green]"):
        plan = ai_service.generate_implementation_plan(feature_description, context_content)

    console.print("\n[bold green]✓ AI deep analysis complete. Generated Implementation Plan:[/bold green]")
    
    if not plan or not plan.get("proposed_issues"):
        console.print("[yellow]The AI did not propose any issues for the implementation plan.[/yellow]")
    else:
        # Pretty print the plan
        from rich.pretty import pprint
        pprint(plan)

    console.print("\n[bold]Workflow complete.[/bold] Next steps would be structured dialogue and local generation.")

sync_app = typer.Typer()
app.add_typer(sync_app, name="sync", help="Synchronize data from GitLab.")

@sync_app.command("map")
def sync_map():
    """Synchronize GitLab issues and build the project map."""
    typer.echo("Starting GitLab synchronization to build project map...")
    
    result = gitlab_service.build_project_map()

    if result["status"] == "error":
        typer.secho(f"Error building project map: {result['message']}", fg=typer.colors.RED)
        raise typer.Exit(1)

    map_data = result["map_data"]
    with open(PROJECT_MAP_PATH, 'w') as f:
        yaml.dump(map_data, f, sort_keys=False)

    typer.secho(f"Project map successfully built with {result['issues_found']} issues and saved to {PROJECT_MAP_PATH}.", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app()