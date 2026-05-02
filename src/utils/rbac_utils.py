import os
import hashlib
from typing import Dict, Any, List, Optional

def get_local_project_name() -> str:
    """
    Generate a stable project name based on the current working directory.
    """
    cwd = os.path.abspath(os.getcwd())
    return "local_" + hashlib.md5(cwd.encode()).hexdigest()[:12]

def get_project_name(path:str) -> str:
    """
    Generate a stable project name based on the path (git repo or local folder).
    """
    if not path:
        return get_local_project_name()

    project_name = os.path.basename(os.path.normpath(path)).split("/")[-1]
    if project_name.endswith(".git"):
        project_name = project_name[:-4]
        
    if not project_name:
        return get_local_project_name()
        
    return project_name

def build_rbac_filters(
    user_id: Optional[str] = None,
    job_id: Optional[str] = None,
    team_id: Optional[str] = None,
    project_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Builds the Haystack filtration dictionary for Weaviate queries.
    If no explicit IDs are provided, uses the localized fallback project_name.
    """
    conditions = []
    
    if user_id:
        conditions.append({"field": "meta.user_id", "operator": "==", "value": to_uuid(user_id)})
    if team_id:
        conditions.append({"field": "meta.team_id", "operator": "==", "value": to_uuid(team_id)})
    if job_id:
        conditions.append({"field": "meta.job_id", "operator": "==", "value": to_uuid(job_id)})
    if project_name:
        conditions.append({"field": "meta.project_name", "operator": "==", "value": project_name})
        
    # Standalone local execution fallback
    if not conditions:
        local_proj = get_local_project_name()
        conditions.append({"field": "meta.project_name", "operator": "==", "value": local_proj})
        
    if not conditions:
        return None
        
    # Combine conditions
    if len(conditions) == 1:
        return conditions[0]
    return {"operator": "AND", "conditions": conditions}

import uuid

def to_uuid(value: str) -> str:
    """
    Ensure a string is a valid UUID. If not, generate a stable UUID v5 from it.
    This is necessary because Weaviate property 'uuid' types strictly require UUID format.
    """
    if not value:
        return value
    try:
        # Check if already a valid UUID
        uuid.UUID(value)
        return value
    except ValueError:
        # Generate stable UUID from string using a fixed namespace (DNS namespace is a safe default)
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, value))

def apply_rbac_metadata(
    meta: Dict[str, Any],
    user_id: Optional[str] = None,
    job_id: Optional[str] = None,
    team_id: Optional[str] = None,
    project_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Adds RBAC tags to the metadata payload before indexing/saving documents.
    Provides the local fallback 'project_name' if all auth tags are missing, ensuring
    standalone mode stores data accurately.
    """
    # Guarantee we return a new dict or modify in place safely.
    if meta is None:
        meta = {}
        
    auth_tags = [user_id, job_id, team_id, project_name]
    
    if user_id:
        meta["user_id"] = to_uuid(user_id)
    if team_id:
        meta["team_id"] = to_uuid(team_id)
    if job_id:
        meta["job_id"] = to_uuid(job_id)
    if project_name:
        meta["project_name"] = project_name
        
    # Local fallback indexing mode
    if not any(auth_tags):
        meta["project_name"] = get_local_project_name()
        
    return meta
