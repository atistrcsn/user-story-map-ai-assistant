import json
import re
import yaml
from pathlib import Path
from gemini_gitlab_workflow import config

def _slugify(text: str) -> str:
    """Converts text to a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'--+', '-', text)
    return text.strip('-')

def get_issue_filepath(title: str, labels: list[str]) -> Path | None:
    """
    Determines the canonical file path for an issue based on its title and labels.
    """
    is_epic = "Type::Epic" in labels
    is_story = "Type::Story" in labels
    is_task = "Type::Task" in labels

    if is_task:
        return None  # Tasks are not standalone files

    filename = f"{_slugify(title)}.md"
    if is_epic:
        filename = "epic.md"
    elif is_story:
        filename = f"story-{_slugify(title)}.md"

    backbone_label = next((label for label in labels if label.startswith("Backbone::")), None)
    
    if not backbone_label:
        return Path("_unassigned") / filename

    backbone_name = _slugify(backbone_label.split("::", 1)[1])

    if is_epic:
        epic_name = _slugify(title)
        return Path("backbones") / backbone_name / epic_name / filename

    return Path("backbones") / backbone_name / filename

def _generate_markdown_content(issue) -> str:
    """Generates the full Markdown content for an issue."""
    frontmatter = {
        "iid": issue.iid,
        "title": str(issue.title),
        "state": str(issue.state),
        "labels": list(issue.labels),
        "web_url": str(issue.web_url),
        "created_at": str(issue.created_at),
        "updated_at": str(issue.updated_at),
        "task_completion_status": issue.task_completion_status
    }
    content = f"---\n{yaml.dump(frontmatter, sort_keys=False)}---\n\n{issue.description or ''}\n"
    return content

def write_issue_file(relative_filepath: Path, issue_data) -> Path:
    """
    Writes the content of a GitLab issue to a local Markdown file.
    `issue_data` is expected to be a GitLab issue object.
    """
    content = _generate_markdown_content(issue_data)
    full_filepath = config.DATA_DIR / relative_filepath
    full_filepath.parent.mkdir(parents=True, exist_ok=True)
    full_filepath.write_text(content, encoding='utf-8')
    return full_filepath

def write_project_map(project_map_data: dict):
    """Writes the project map data to the YAML file."""
    with open(config.PROJECT_MAP_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(project_map_data, f, sort_keys=False)

def read_timestamps_cache() -> dict:
    """Reads the timestamps cache file."""
    config.CACHE_DIR.mkdir(exist_ok=True)
    if not config.TIMESTAMPS_CACHE_PATH.exists():
        return {}
    try:
        with open(config.TIMESTAMPS_CACHE_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def write_timestamps_cache(timestamps: dict):
    """Writes data to the timestamps cache file."""
    config.CACHE_DIR.mkdir(exist_ok=True)
    with open(config.TIMESTAMPS_CACHE_PATH, 'w') as f:
        json.dump(timestamps, f, indent=2)
