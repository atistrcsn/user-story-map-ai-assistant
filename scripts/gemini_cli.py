import typer
import yaml
import gitlab_service # Import the new service module

app = typer.Typer()

PROJECT_MAP_PATH = "project_map.yaml"

# The CLI is now much thinner. It's responsible for user interaction and calling the service.

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

@app.command("create")
def create_feature(
    feature_description: str = typer.Argument(..., help="A high-level description of the new feature.")
):
    """
    Initiates the AI-assisted workflow to create a new feature story map.
    """
    typer.echo(f"Starting AI-assisted creation for feature: '{feature_description}'")
    
    # Step 1: Smart Sync, handled by the service layer
    typer.echo("Performing smart sync with GitLab...")
    sync_result = gitlab_service.smart_sync()

    if sync_result["status"] == "error":
        typer.secho(f"Error during sync: {sync_result['message']}", fg=typer.colors.RED)
        raise typer.Exit(1)

    if sync_result["updated_count"] == 0:
        typer.secho(f"Project is up-to-date. Total issues: {sync_result['total_issues']}.", fg=typer.colors.GREEN)
    else:
        typer.echo(f"Sync complete. Found {sync_result['updated_count']} new or updated issues:")
        for issue in sync_result["updated_issues"]:
            typer.echo(f"  - Fetched updated issue #{issue['iid']}: {issue['title']}")

    typer.echo("\nAI analysis and dialogue steps are not yet implemented.")
    typer.echo("Feature creation process placeholder complete.")

@app.command()
def hello(name: str = "World"):
    """Say hello to NAME."""
    print(f"Hello {name}!")

if __name__ == "__main__":
    app()