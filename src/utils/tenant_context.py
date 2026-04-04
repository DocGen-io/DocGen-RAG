import contextvars
from typing import Optional

# Context variable for holding the active team ID during isolated component execution
current_tenant_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("tenant_id", default=None)

def set_tenant(team_id: str):
    """Set the Weaviate tenant context for the current executing pipeline."""
    return current_tenant_id.set(team_id)

def get_tenant() -> str | None:
    """Get the active Weaviate tenant from context."""
    return current_tenant_id.get()
