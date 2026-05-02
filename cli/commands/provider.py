"""
docgen provider -- Manage AI provider strategies.

Subcommands:
  list            Show available providers and active selection
  add <name>      Fetch and install a provider from the manifest
  remove <name>   Remove a provider's cached files
"""

from pathlib import Path

from cli.core import console
from cli.core import provider_registry as registry


def list_available() -> list[str]:
    """List all providers defined in the manifest."""
    manifest_path = registry.get_manifest_path()
    providers = registry.list_providers(manifest_path)

    table = console.make_table("Available Providers", ["Name", "Packages"])
    manifest = registry.load_manifest(manifest_path)

    for name in providers:
        info = manifest["providers"][name]
        packages = ", ".join(info["pip_packages"])
        table.add_row(name, packages)

    console.console.print(table)
    return providers


def add_provider(name: str) -> None:
    """Fetch provider files from GitHub and install required packages."""
    manifest_path = registry.get_manifest_path()
    manifest = registry.load_manifest(manifest_path)

    if name not in manifest["providers"]:
        console.print_error(
            f"Provider '{name}' not found in manifest. "
            f"Available: {', '.join(manifest['providers'].keys())}"
        )
        return

    console.print_step(f"Fetching '{name}' provider files (commit: {manifest['commit'][:12]})...")

    target_dir = Path.home() / ".config" / "docgen" / "providers"
    saved = registry.fetch_and_save_provider(manifest, name, target_dir)
    console.print_success(f"Saved {len(saved)} files.")

    packages = manifest["providers"][name]["pip_packages"]
    if packages:
        console.print_step(f"Installing: {', '.join(packages)}")
        registry.install_packages(packages)
        console.print_success("Packages installed.")


def remove_provider(name: str) -> None:
    """Remove cached provider files."""
    target_dir = Path.home() / ".config" / "docgen" / "providers" / name
    if target_dir.exists():
        import shutil
        shutil.rmtree(target_dir)
        console.print_success(f"Provider '{name}' files removed.")
    else:
        console.print_warning(f"No cached files found for '{name}'.")
