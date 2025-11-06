import typer
import yaml
import os
import glob
import gitlab_service
import ai_service

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
    typer.echo(f"Starting AI-assisted creation for feature: '{feature_description}'")
    
    # Step 1: Smart Sync to ensure the project map is up-to-date
    typer.echo("Performing smart sync with GitLab...")
    sync_result = gitlab_service.smart_sync()
    if sync_result["status"] == "error":
        typer.secho(f"Error during sync: {sync_result['message']}", fg=typer.colors.RED)
        raise typer.Exit(1)
    
    if sync_result["updated_count"] > 0:
        typer.echo(f"Sync complete. Found {sync_result['updated_count']} updates. Rebuilding project map...")
        build_result = gitlab_service.build_project_map()
        if build_result["status"] == "error":
            typer.secho(f"Error rebuilding project map: {build_result['message']}", fg=typer.colors.RED)
            raise typer.Exit(1)
        with open(PROJECT_MAP_PATH, 'w') as f:
            yaml.dump(build_result["map_data"], f, sort_keys=False)
        typer.secho("Project map updated.", fg=typer.colors.GREEN)
    else:
        typer.secho("Project map is already up-to-date.", fg=typer.colors.GREEN)

    # Step 2: Gather all potential context sources
    typer.echo("\nGathering all potential context sources...")
    doc_sources = _get_context_from_docs()
    map_sources = _get_context_from_project_map()
    all_sources = doc_sources + map_sources
    typer.echo(f"Found {len(all_sources)} potential context sources.")

    # Step 3: Call AI service for pre-filtering
    typer.echo("Sending context to AI for pre-filtering analysis...")
    relevant_files = ai_service.get_relevant_context_files(feature_description, all_sources)

    if not relevant_files:
        typer.secho("The AI could not identify any relevant context files.", fg=typer.colors.YELLOW)
    else:
        typer.secho("AI analysis complete. The following files were identified as most relevant:", fg=typer.colors.GREEN)
        for file_path in relevant_files:
            typer.echo(f"  - {file_path}")
            
    typer.echo("\nPre-filtering phase complete. Next step would be deep analysis with this context.")

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