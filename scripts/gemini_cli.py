import typer
import yaml
import gitlab_service # Import the new service module
from gitlab_service import generate_local_artifacts # Import the new function

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

    # --- AI Analysis and Dialogue Steps ---

    # Step 3.1: Ensure local data is fresh for analysis
    typer.echo("\nEnsuring local data is up-to-date for AI analysis...")
    build_result = gitlab_service.build_project_map()
    if build_result["status"] == "error":
        typer.secho(f"Error building local data map: {build_result['message']}", fg=typer.colors.RED)
        raise typer.Exit(1)
    typer.secho(f"Local data is fresh. {build_result['issues_found']} issues loaded.", fg=typer.colors.GREEN)

    # Step 3.2: Two-Phase AI Analysis (Simulated)
    typer.echo("\n--- Starting Two-Phase AI Analysis ---")
    
    # Phase 1 (Pre-filtering): Find all relevant documents for the first-pass LLM.
    # In a real scenario, a smaller LLM would intelligently select a subset of these.
    typer.echo("Phase 1: Identifying all relevant project documents for context...")
    
    # In a real implementation, we would use glob to find these files.
    # For now, we will simulate this by listing the directories.
    relevant_docs_dirs = ["/workspaces/docs", "/workspaces/scripts/gitlab_data"]
    typer.echo(f"Found potential context documents in: {', '.join(relevant_docs_dirs)}")
    typer.secho("Pre-filtering complete. Identified all project documentation and issue data.", fg=typer.colors.GREEN)

    # Phase 2 (Deep Analysis): The primary LLM analyzes the filtered context.
    # We will simulate this by stating our intention.
    typer.echo("\nPhase 2: Performing deep analysis with primary LLM...")
    typer.echo(f"Input to LLM would be:")
    typer.echo(f"  - User Request: '{feature_description}'")
    typer.echo(f"  - Context from files in: {', '.join(relevant_docs_dirs)}")
    
    # Placeholder for the actual analysis and dialogue
    typer.secho("Deep analysis simulation complete.", fg=typer.colors.GREEN)

    # Step 4: Structured Dialogue (User Confirmation) - Simulated
    typer.echo("\n--- Starting Structured Dialogue with User ---")
    typer.echo("AI: Based on the deep analysis of \'feature_description\', I propose the following high-level Epics:")
    typer.echo("  - Epic: User Authentication (Login, Registration, Password Reset)")
    typer.echo("  - Epic: Profile Management (View, Edit Profile, Profile Picture Upload)")
    typer.echo("  - Epic: Content Creation (Post, Edit, Delete Content)")
    
    typer.echo("AI: Do these proposed Epics align with your vision? (Yes/No)")
    # In a real scenario, we would wait for user input here.
    typer.secho("User: Yes (Simulated confirmation)", fg=typer.colors.BLUE)
    typer.secho("Structured dialogue simulation complete. User confirmed high-level Epics.", fg=typer.colors.GREEN)

    # Step 5: Local Generation - Real Implementation
    typer.echo("\n--- Starting Local Generation (Real Implementation) ---")
    
    # Sample proposed issues (this would come from the AI's plan after dialogue)
    sample_proposed_issues = [
        {
            "title": "User Authentication Epic",
            "description": "This epic covers all aspects of user authentication, including registration, login, and password management.",
            "labels": ["Backbone::Core-Functionality", "Epic::User-Authentication", "Type::Epic"],
            "state": "opened"
        },
        {
            "title": "Profile Management Epic",
            "description": "This epic focuses on allowing users to manage their profiles, including editing personal information and uploading profile pictures.",
            "labels": ["Backbone::Core-Functionality", "Epic::Profile-Management", "Type::Epic"],
            "state": "opened"
        },
        {
            "title": "Content Creation Epic",
            "description": "This epic enables users to create, edit, and delete various types of content within the application.",
            "labels": ["Backbone::Core-Functionality", "Epic::Content-Creation", "Type::Epic"],
            "state": "opened"
        }
    ]

    local_gen_result = generate_local_artifacts(sample_proposed_issues, PROJECT_MAP_PATH)

    if local_gen_result["status"] == "error":
        typer.secho(f"Error during local artifact generation: {local_gen_result['message']}", fg=typer.colors.RED)
        raise typer.Exit(1)
    
    typer.secho(f"Local generation complete. Generated {local_gen_result['generated_count']} new artifacts.", fg=typer.colors.GREEN)
    for node in local_gen_result["new_nodes"]:
        typer.echo(f"  - Generated: {node['local_path']} (Temp ID: {node['id']})")

    typer.echo("\nRobust upload to GitLab steps are not yet implemented.")
    typer.echo("Feature creation process is now complete.")

@app.command()
def hello(name: str = "World"):
    """Say hello to NAME."""
    print(f"Hello {name}!")

if __name__ == "__main__":
    app()