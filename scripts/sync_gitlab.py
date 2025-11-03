#!/usr/bin/env python

"""Main script to synchronize GitLab data."""

import gitlab
import config
import os
import re
import yaml
import shutil

AGILE_HIERARCHY_MAP = {
    "Backbone": "backbones",
    "Epic": "epics",
    "Story": "stories",
    "Task": "tasks",
}

def _slugify(text):
    """Converts text to a URL-friendly slug."""
    text = re.sub(r'\s+', '-', text).lower()  # Replace spaces with hyphens and convert to lowercase
    text = re.sub(r'[^a-z0-9-]', '', text)  # Remove non-alphanumeric characters except hyphens
    return text

def _get_issue_filepath(issue, base_output_dir):
    """Determines the file path for an issue based on its labels and hierarchy."""
    path_parts = [base_output_dir]
    issue_labels = set(issue.labels)

    # Determine hierarchy based on labels
    hierarchy_levels = []
    for level_name, dir_name in AGILE_HIERARCHY_MAP.items():
        for label in issue_labels:
            if label.startswith(f"{level_name}:"):
                hierarchy_levels.append((level_name, dir_name, label.split(':', 1)[1].strip()))
                break
    
    # If no hierarchy labels are found, place in _unassigned directory
    if not hierarchy_levels:
        path_parts.append("_unassigned")
    else:
        # Sort hierarchy levels to ensure consistent path order (e.g., Backbone before Epic)
        # This assumes AGILE_HIERARCHY_MAP keys are ordered correctly or we define an explicit order
        defined_order = list(AGILE_HIERARCHY_MAP.keys())
        hierarchy_levels.sort(key=lambda x: defined_order.index(x[0]) if x[0] in defined_order else len(defined_order))

        for _, dir_name, label_value in hierarchy_levels:
            path_parts.append(dir_name)
            path_parts.append(_slugify(label_value))

    # Add issue title as filename
    filename = f"{_slugify(issue.title)}.md"
    return os.path.join(*path_parts, filename)

def _generate_markdown_content(issue):
    """Generates markdown content for a given GitLab issue."""
    frontmatter = {
        "id": issue.iid,
        "title": issue.title,
        "type": issue.issue_type, # Added issue type
        "state": issue.state,
        "labels": issue.labels,
        "milestone": issue.milestone['title'] if issue.milestone else None,
        "assignee": issue.assignee['username'] if issue.assignee else None,
        "due_date": issue.due_date,
        "created_at": issue.created_at,
        "updated_at": issue.updated_at,
        "web_url": issue.web_url,
    }

    # Remove None values from frontmatter
    frontmatter = {k: v for k, v in frontmatter.items() if v is not None}

    markdown_content = "---\n"  # Start YAML frontmatter
    markdown_content += yaml.dump(frontmatter, sort_keys=False, allow_unicode=True)
    markdown_content += "---\n\n"  # End YAML frontmatter
    markdown_content += issue.description if issue.description else "No description provided."

    return markdown_content


def main():
    """Main function to run the sync process."""
    print("Sync script starting...")

    base_output_dir = "gitlab_data"
    if os.path.exists(base_output_dir):
        shutil.rmtree(base_output_dir)
        print(f"Cleaned up existing {base_output_dir} directory.")
    os.makedirs(base_output_dir, exist_ok=True)

    # Initialize GitLab connection
    try:
        gl = gitlab.Gitlab(config.GITLAB_URL, private_token=config.PRIVATE_TOKEN)
        gl.auth()  # Authenticate to verify the token and URL
        print("Successfully authenticated to GitLab.")
    except Exception as e:
        print(f"Failed to authenticate to GitLab: {e}")
        return

    # Get the project
    try:
        project = gl.projects.get(config.PROJECT_PATH)
        print(f"Successfully found project: {project.name_with_namespace}")
    except Exception as e:
        print(f"Failed to get project '{config.PROJECT_PATH}': {e}")
        return

    # Fetch issues
    issues = project.issues.list(all=True)
    print(f"Found {len(issues)} issues.")

    for issue in issues:
        filepath = _get_issue_filepath(issue, base_output_dir)
        markdown_content = _generate_markdown_content(issue)

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"Wrote issue {issue.iid} to {filepath}")

    print("Sync script finished.")

if __name__ == "__main__":
    main()
