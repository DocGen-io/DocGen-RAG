"""
Commit-hash-pinned provider fetching from GitHub.

The provider_manifest.json is the single source of truth for:
  - Which commit hash to fetch from
  - Which files constitute each provider (embedder + generator)
  - Which pip packages each provider requires

Adding a new provider = adding one JSON entry. No code changes.
"""

import json
import subprocess
import urllib.request
from pathlib import Path
from typing import Any


def load_manifest(manifest_path: str) -> dict[str, Any]:
    """Load and parse the provider manifest JSON."""
    with open(manifest_path) as f:
        return json.load(f)


def build_raw_url(repo: str, commit: str, filepath: str) -> str:
    """Construct a raw GitHub URL for a file at a specific commit."""
    return f"https://raw.githubusercontent.com/{repo}/{commit}/{filepath}"


def list_providers(manifest_path: str) -> list[str]:
    """Return the names of all providers defined in the manifest."""
    manifest = load_manifest(manifest_path)
    return list(manifest["providers"].keys())


def fetch_provider_file(repo: str, commit: str, filepath: str) -> str:
    """Download a single file from GitHub at the pinned commit hash."""
    url = build_raw_url(repo, commit, filepath)
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")


def fetch_and_save_provider(
    manifest: dict[str, Any],
    provider_name: str,
    target_dir: Path,
) -> list[str]:
    """
    Fetch all files for a provider and save them locally.

    Returns the list of saved file paths.
    """
    repo = manifest["repo"]
    commit = manifest["commit"]
    provider = manifest["providers"][provider_name]
    saved: list[str] = []

    for file_type in ("embedder", "generator"):
        filepath = provider[file_type]
        content = fetch_provider_file(repo, commit, filepath)

        # Save under target_dir/provider_name/filename
        dest = target_dir / provider_name / Path(filepath).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        saved.append(str(dest))

    return saved


def install_packages(packages: list[str]) -> None:
    """Install Python packages using uv."""
    if not packages:
        return
    subprocess.run(
        ["uv", "pip", "install", *packages],
        check=True,
        capture_output=True,
        text=True,
    )


def get_manifest_path() -> str:
    """Return the absolute path to the bundled provider_manifest.json."""
    return str(Path(__file__).resolve().parent.parent / "provider_manifest.json")
