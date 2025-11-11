import os
from . import gitlab_client, file_system_repo, project_mapper, gitlab_uploader

def smart_sync() -> dict:
    """
    Performs a smart sync by checking for updated issues in GitLab
    based on a local timestamp cache.
    """
    project_id = os.getenv("GGW_GITLAB_PROJECT_ID")
    if not project_id:
        raise ValueError("Error: GGW_GITLAB_PROJECT_ID must be set.")

    last_timestamps = file_system_repo.read_timestamps_cache()
    
    # This is inefficient as it fetches all issues just for timestamps.
    # A more advanced implementation would use the GitLab API's `updated_after` filter.
    # For now, we replicate the original logic's inefficiency.
    all_issues = gitlab_client.get_project_issues(project_id, all=True, as_list=False)
    
    current_timestamps = {str(issue.iid): issue.updated_at for issue in all_issues}
    
    updated_issue_iids = [
        int(iid) for iid, updated_at in current_timestamps.items()
        if iid not in last_timestamps or last_timestamps[iid] < updated_at
    ]
    
    updated_issues = [gitlab_client.get_project_issue(project_id, iid) for iid in updated_issue_iids]
    
    file_system_repo.write_timestamps_cache(current_timestamps)
    
    return {
        "status": "success",
        "updated_count": len(updated_issues),
        "updated_issues": [{"iid": i.iid, "title": i.title} for i in updated_issues],
        "total_issues": len(current_timestamps)
    }

def build_project_map_and_sync_files() -> dict:
    """
    Orchestrates building the project map and syncing files from GitLab.
    """
    project_id = os.getenv("GGW_GITLAB_PROJECT_ID")
    if not project_id:
        return {"status": "error", "message": "GGW_GITLAB_PROJECT_ID must be set."}
    
    return project_mapper.build_project_map(project_id)

def upload_new_artifacts(project_map: dict) -> dict:
    """
    Orchestrates uploading new artifacts from the project map to GitLab.
    """
    project_id = os.getenv("GGW_GITLAB_PROJECT_ID")
    if not project_id:
        return {"status": "error", "message": "GGW_GITLAB_PROJECT_ID must be set."}

    return gitlab_uploader.upload_artifacts_to_gitlab(project_id, project_map)
