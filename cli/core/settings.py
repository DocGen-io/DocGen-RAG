"""
Dynaconf-powered settings management.

Reads from (in priority order):
  1. Environment variables with DOCGEN_ prefix
  2. User config:  ~/.config/docgen/settings.toml
  3. Defaults:     cli/default_settings.toml

Exposes a module-level `get_settings()` that returns the Dynaconf object,
and `settings_to_config_dict()` to export back to the legacy config.yaml format.
"""

from pathlib import Path
from typing import Any

from dynaconf import Dynaconf

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_USER_CONFIG_DIR = Path.home() / ".config" / "docgen"
_USER_SETTINGS = _USER_CONFIG_DIR / "settings.toml"
_DEFAULT_SETTINGS = Path(__file__).resolve().parent.parent / "default_settings.toml"

_settings_instance: Dynaconf | None = None


def _build_settings() -> Dynaconf:
    """Construct a new Dynaconf instance."""
    settings_files = [str(_DEFAULT_SETTINGS)]
    if _USER_SETTINGS.exists():
        settings_files.append(str(_USER_SETTINGS))

    return Dynaconf(
        envvar_prefix="DOCGEN",
        settings_files=settings_files,
        environments=False,
        load_dotenv=False,
        merge_enabled=True,
    )


def get_settings() -> Dynaconf:
    """Return the singleton Dynaconf settings object."""
    global _settings_instance
    _settings_instance = _build_settings()
    return _settings_instance


def reset_settings() -> None:
    """Force rebuild of settings on next access."""
    global _settings_instance
    _settings_instance = None


def save_user_setting(key: str, value: Any) -> None:
    """Append/overwrite a key in the user settings file."""
    _USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Read existing content
    lines: list[str] = []
    if _USER_SETTINGS.exists():
        lines = _USER_SETTINGS.read_text().splitlines()

    # Check if key already exists (simple top-level only)
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key} ") or line.strip().startswith(f"{key}="):
            lines[i] = f'{key} = "{value}"' if isinstance(value, str) else f"{key} = {value}"
            found = True
            break

    if not found:
        lines.append(f'{key} = "{value}"' if isinstance(value, str) else f"{key} = {value}")

    _USER_SETTINGS.write_text("\n".join(lines) + "\n")
    reset_settings()


def settings_to_config_dict(settings: Any = None) -> dict:
    """
    Export current settings to a dict matching the legacy config.yaml structure.
    This allows the existing pipeline code to consume CLI-managed settings.
    """
    s = settings or get_settings()
    
    # Start with a base dictionary from the object if possible
    if hasattr(s, "as_dict"):
        config_dict = {k.lower(): v for k, v in s.as_dict().items()}
    else:
        config_dict = {}

    # Ensure 'rag' section exists and is populated (needed by tests and pipeline)
    if "rag" not in config_dict:
        rag_obj = getattr(s, "rag", None)
        if rag_obj:
            config_dict["rag"] = {
                "active_embedder": getattr(rag_obj, "active_embedder", "gemini"),
                "embedding_model": getattr(rag_obj, "embedding_model", "gemini-2.5-flash-lite"),
                "top_k_retriever": getattr(rag_obj, "top_k_retriever", 2),
                "top_k_reranker": getattr(rag_obj, "top_k_reranker", 2),
                "chunk_size": getattr(rag_obj, "chunk_size", 500),
            }
        else:
            config_dict["rag"] = {}

    # Ensure active_provider cascades down to the pipeline components
    # We use getattr and a fallback string to handle mocks and real objects
    raw_active = getattr(s, "active_provider", "gemini")
    active_provider = raw_active if isinstance(raw_active, str) else "gemini"
    
    for section in ["code_analyzer", "doc_creator", "query_generator"]:
        if section not in config_dict:
            config_dict[section] = {}
        # Only override if it's a new or empty section to avoid wiping out defaults
        if not config_dict[section].get("active_generator"):
            config_dict[section]["active_generator"] = active_provider
        
    return config_dict
