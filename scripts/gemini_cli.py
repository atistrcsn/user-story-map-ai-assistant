import os
import re
import typer
import gitlab
import networkx as nx
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = typer.Typer()

PROJECT_MAP_PATH = "project_map.yaml"

# GitLab client initialization (placeholder)
def get_gitlab_client():
    gitlab_url = os.getenv("GITLAB_URL")
    gitlab_private_token = os.getenv("GITLAB_PRIVATE_TOKEN")

    if not gitlab_url or not gitlab_private_token:
        typer.echo("Error: GITLAB_URL and GITLAB_PRIVATE_TOKEN must be set in .env or environment variables.", err=True)
        raise typer.Exit(code=1)

    try:
        gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_private_token)
        gl.auth()
        return gl
    except gitlab.exceptions.GitlabError as e:
        typer.echo(f"Error connecting to GitLab: {e}", err=True)
        raise typer.Exit(code=1)

def parse_relationships(current_issue_iid: int, text: str) -> list[dict]:
    """Parses text to find GitLab issue relationships (e.g., '/blocked by #<IID>', '/blocking #<IID>')."""
    relationships = []

    # Pattern for /blocking #<IID>
    # The issue containing this text is blocking the target issue.
    # Source: current_issue_iid, Target: captured_iid, Type: blocks
    blocking_pattern = re.compile(r"/blocking\s+#(\d+)", re.IGNORECASE)
    for match in blocking_pattern.finditer(text):
        target_iid = int(match.group(1))
        relationships.append({"source": current_issue_iid, "target": target_iid, "type": "blocks"})

    # Pattern for /blocked by #<IID>
    # The issue containing this text is blocked by the target issue.
    # Source: captured_iid, Target: current_issue_iid, Type: blocks
    blocked_by_pattern = re.compile(r"/blocked by\s+#(\d+)", re.IGNORECASE)
    for match in blocked_by_pattern.finditer(text):
        source_iid = int(match.group(1))
        relationships.append({"source": source_iid, "target": current_issue_iid, "type": "blocks"})

    return relationships

sync_app = typer.Typer()
app.add_typer(sync_app, name="sync", help="Synchronize data from GitLab.")

@sync_app.command("map")
def sync_map():
    """Synchronize GitLab issues and build the project map."""
    typer.echo("Starting GitLab synchronization to build project map...")
    gl = get_gitlab_client()

    project_id = os.getenv("GITLAB_PROJECT_ID")
    if not project_id:
        typer.echo("Error: GITLAB_PROJECT_ID must be set in .env or environment variables.", err=True)
        raise typer.Exit(code=1)

    try:
        project = gl.projects.get(project_id)
    except gitlab.exceptions.GitlabError as e:
        typer.echo(f"Error fetching project {project_id}: {e}", err=True)
        raise typer.Exit(code=1)

    issues = project.issues.list(all=True)
    typer.echo(f"Found {len(issues)} issues in project {project.name} (ID: {project_id}).")

    G = nx.DiGraph()
    nodes_data = []
    unique_links_set = set() # To store unique (source, target, type) tuples
    links_data = []

    for issue in issues:
        # Add issue as a node
        node = {
            "id": issue.iid,
            "title": issue.title,
            "type": "Issue", # Default type, can be refined later based on labels
            "state": issue.state,
            "web_url": issue.web_url,
            "labels": issue.labels,
            "created_at": issue.created_at,
            "updated_at": issue.updated_at,
            # Add more metadata as needed
        }
        nodes_data.append(node)
        G.add_node(issue.iid, **node)

        # Parse relationships from description
        found_relationships = parse_relationships(issue.iid, issue.description or "")
        for rel in found_relationships:
            link_tuple = (rel["source"], rel["target"], rel["type"])
            if link_tuple not in unique_links_set:
                unique_links_set.add(link_tuple)
                links_data.append(rel)
                G.add_edge(rel["source"], rel["target"], type=rel["type"])

        # Parse relationships from comments
        typer.echo(f"  -> Fetching comments for issue #{issue.iid}...")
        for comment in issue.notes.list(all=True):
            found_relationships = parse_relationships(issue.iid, comment.body)
            for rel in found_relationships:
                link_tuple = (rel["source"], rel["target"], rel["type"])
                if link_tuple not in unique_links_set:
                    unique_links_set.add(link_tuple)
                    links_data.append(rel)
                    G.add_edge(rel["source"], rel["target"], type=rel["type"])

    # Convert networkx graph to node-link format for YAML
    project_map_data = {
        "doctrine": {
            "gemini_md_path": "/docs/spec/GEMINI.md",
            "gemini_md_commit_hash": "TODO: git rev-parse HEAD:path/to/GEMINI.md"
        },
        "nodes": nodes_data,
        "links": links_data
    }

    with open(PROJECT_MAP_PATH, 'w') as f:
        yaml.dump(project_map_data, f, sort_keys=False)

    typer.echo(f"Project map successfully built and saved to {PROJECT_MAP_PATH}.")
    typer.echo("GitLab synchronization complete. Project map built.")

@app.command()
def hello(name: str = "World"):
    """Say hello to NAME."""
    print(f"Hello {name}!")

if __name__ == "__main__":
    app()