"""
docgen config -- View and manage configuration.

Subcommands:
  show          Display current settings (secrets redacted)
  set <k> <v>   Update a setting
  reset         Reset to defaults
"""

from pathlib import Path

from cli.core import console
from cli.core.settings import get_settings, save_user_setting, reset_settings

_USER_SETTINGS = Path.home() / ".config" / "docgen" / "settings.toml"


def show_config() -> dict:
    """Display the current configuration, redacting any secrets."""
    settings = get_settings()
    config = settings.as_dict()
    console.print_step("Current configuration:")
    console.console.print_json(data=config)
    return config


def set_config(key: str, value: str) -> None:
    """Set a configuration value."""
    save_user_setting(key, value)
    console.print_success(f"Setting '{key}' updated.")


def reset_config() -> None:
    """Remove user overrides and reset to defaults."""
    if _USER_SETTINGS.exists():
        _USER_SETTINGS.unlink()
    reset_settings()
    console.print_success("Configuration reset to defaults.")
