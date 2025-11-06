import typer
import gitlab_service
from typing_extensions import Annotated
from rich.console import Console
from rich.table import Table

# Initialize rich console for better output
console = Console()
app = typer.Typer()

@app.command()
def main(
    iids: Annotated[str, typer.Argument(help="A comma-separated string of issue IIDs to delete.")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip the confirmation prompt. DANGEROUS!")] = False
):
    """
    Connects to GitLab and deletes a list of issues in bulk.
    
    This is a DESTRUCTIVE operation. Please use with caution.
    """
    console.print("[bold yellow]Starting bulk delete process...[/bold yellow]")

    # 1. Parse and validate the input IIDs
    try:
        iid_list = [int(iid.strip()) for iid in iids.split(',') if iid.strip()]
        if not iid_list:
            raise ValueError("IID list is empty.")
    except ValueError:
        console.print("[bold red]Error:[/bold red] Please provide a valid, non-empty, comma-separated list of issue IDs (e.g., '25,26,27').")
        raise typer.Exit(code=1)

    # 2. Connect to GitLab
    try:
        gl = gitlab_service.get_gitlab_client()
        project_id = gitlab_service.os.getenv("GITLAB_PROJECT_ID")
        project = gl.projects.get(project_id)
        console.print(f"Successfully connected to project: [bold cyan]{project.name_with_namespace}[/bold cyan]")
    except Exception as e:
        console.print(f"[bold red]Error connecting to GitLab:[/bold red] {e}")
        raise typer.Exit(code=1)

    # 3. Fetch issues for confirmation
    issues_to_delete = []
    console.print("\nFetching details for issues to be deleted...")
    with console.status("[bold green]Fetching issues...[/bold green]"):
        for iid in iid_list:
            try:
                issue = project.issues.get(iid)
                issues_to_delete.append(issue)
            except Exception:
                console.print(f"[yellow]Warning: Could not find issue with IID #{iid}. Skipping.[/yellow]")

    if not issues_to_delete:
        console.print("[bold red]No valid, existing issues found to delete. Aborting.[/bold red]")
        raise typer.Exit()

    # 4. Display confirmation table
    table = Table(title="[bold red blink]ISSUES SCHEDULED FOR PERMANENT DELETION[/bold red blink]")
    table.add_column("IID", style="magenta", justify="right")
    table.add_column("Title", style="cyan")
    table.add_column("State", style="green")
    for issue in issues_to_delete:
        table.add_row(str(issue.iid), issue.title, issue.state)
    
    console.print(table)

    # 5. Ask for final confirmation
    if not force:
        if not typer.confirm(f"\nAre you absolutely sure you want to permanently delete these {len(issues_to_delete)} issues?"):
            console.print("[yellow]Operation cancelled by user.[/yellow]")
            raise typer.Exit()
    else:
        console.print("[bold yellow]--force flag detected. Skipping confirmation.[/bold yellow]")

    # 6. Perform deletion
    deleted_count = 0
    console.print("\n[bold red]Proceeding with deletion...[/bold red]")
    with console.status("[bold red]Deleting issues...[/bold red]") as status:
        for issue in issues_to_delete:
            try:
                status.update(f"Deleting issue #{issue.iid}: '{issue.title}'")
                issue.delete()
                console.print(f"  [green]✓[/green] Successfully deleted issue #{issue.iid}: '{issue.title}'")
                deleted_count += 1
            except Exception as e:
                console.print(f"  [red]✗[/red] Failed to delete issue #{issue.iid}. Reason: {e}")

    console.print(f"\n[bold green]Bulk delete operation complete.[/bold green]")
    console.print(f"Successfully deleted {deleted_count} of {len(issues_to_delete)} targeted issue(s).")


if __name__ == "__main__":
    app()
