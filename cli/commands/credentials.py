"""
docgen credentials -- Manage stored credentials.

Subcommands:
  set <provider>    Re-run credential setup for a provider
  check [provider]  Verify credentials exist
  clear <provider>  Remove stored credentials
"""

from cli.core import console, secrets
from cli.commands.init import REQUIRED_CREDENTIALS, setup_provider_credentials


def check_credentials(provider: str) -> bool:
    """
    Check if all required credentials exist for a provider.
    Returns True if all are present, False otherwise.
    """
    keys = REQUIRED_CREDENTIALS.get(provider, [])
    if not keys:
        console.print_warning(f"No credential requirements defined for '{provider}'.")
        return True

    all_present = True
    for key in keys:
        if secrets.exists(key):
            console.print_step(f"  {key}: stored")
        else:
            console.print_error(f"  {key}: missing")
            all_present = False

    return all_present


def check_all_credentials() -> dict[str, bool]:
    """Check credentials for all known providers."""
    results: dict[str, bool] = {}
    for provider in REQUIRED_CREDENTIALS:
        console.print_step(f"Provider: {provider}")
        results[provider] = check_credentials(provider)
    return results


def clear_credentials(provider: str) -> None:
    """Remove all stored credentials for a provider."""
    keys = REQUIRED_CREDENTIALS.get(provider, [])
    for key in keys:
        secrets.delete(key)
    console.print_success(f"Credentials cleared for '{provider}'.")


def set_credentials(provider: str) -> None:
    """Re-run credential setup for a provider."""
    setup_provider_credentials(provider)
