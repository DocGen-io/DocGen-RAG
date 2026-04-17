"""
PipelineContext — Single source of truth for pipeline-wide runtime context.

Replaces the raw `api_details: Dict[str, Any]` that was threaded through every
component constructor and run() call. Components that need RBAC tagging or
Weaviate filtering read from this typed object instead of unpacking an
untyped dictionary.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PipelineContext:
    """Immutable runtime context passed through the pipeline."""

    project_name: str = ""

    # RBAC / multi-tenancy fields
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    job_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to a plain dict (for JSON logging, Haystack params, etc.)."""
        return {
            "project_name": self.project_name,
            "user_id": self.user_id,
            "team_id": self.team_id,
            "job_id": self.job_id,
        }
