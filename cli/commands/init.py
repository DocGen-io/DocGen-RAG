"""
docgen init -- First-time setup wizard.

Walks the user through:
  1. Docker availability check
  2. Provider selection
  3. Provider-specific credential setup (OAuth for Google, API key for OpenAI)
  4. Provider file fetching from GitHub (pinned commit)
  5. Package installation
  6. Docker volume creation and service startup
"""

import subprocess
from pathlib import Path

from cli.core import console, secrets
from cli.core import provider_registry as registry
from cli.core.docker import compose_up, ensure_volume
from cli.core.settings import save_user_setting, get_settings
from cli.commands.provider_strategies import STRATEGIES


# Maps provider -> list of required credential keys
REQUIRED_CREDENTIALS: dict[str, list[str]] = {
    "gemini": ["google_project_id", "google_location"],
    "openai": ["openai_api_key"],
    "ollama": ["ollama_url"],
}


def check_docker() -> bool:
    """Verify Docker is installed and available."""
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def setup_provider_credentials(provider: str) -> None:
    """Run the credential setup flow for a given provider using the Strategy Pattern."""
    strategy_cls = STRATEGIES.get(provider)
    if strategy_cls:
        strategy = strategy_cls()
        strategy.setup()
    else:
        console.print_error(f"Unknown provider: {provider}")


# -- Main init flow -----------------------------------------------------------

def run_init() -> None:
    """Execute the full first-time setup wizard."""
    console.print_header("DocGen Setup")

    # 1. Check Docker
    console.print_step("Checking Docker availability...")
    if not check_docker():
        console.print_error(
            "Docker is not installed or not running. "
            "Install it from https://docs.docker.com/get-docker/"
        )
        return
    console.print_success("Docker is available.")

    # 2. Select provider
    provider = console.select(
        "Select your AI provider:",
        choices=["gemini", "openai", "ollama"],
    )
    if not provider:
        return

    save_user_setting("active_provider", provider)
    save_user_setting("rag.active_embedder", provider)

    # 3. Provider credentials
    setup_provider_credentials(provider)

    # 4. Fetch provider files
    console.print_step(f"Fetching {provider} provider files from repository...")
    manifest_path = registry.get_manifest_path()
    manifest = registry.load_manifest(manifest_path)

    if provider in manifest["providers"]:
        target_dir = Path.home() / ".config" / "docgen" / "providers"
        try:
            saved = registry.fetch_and_save_provider(manifest, provider, target_dir)
            console.print_success(f"Provider files saved: {len(saved)} files.")
        except Exception as e:
            console.print_warning(f"Could not fetch provider files: {e}")
            console.print_step("Using local provider files instead.")

    # 5. Install packages
    packages = manifest["providers"].get(provider, {}).get("pip_packages", [])
    if packages:
        console.print_step(f"Installing packages: {', '.join(packages)}")
        try:
            registry.install_packages(packages)
            console.print_success("Packages installed.")
        except Exception as e:
            console.print_warning(f"Package installation issue: {e}")

    # 6. Docker volume
    console.print_step("Creating Docker volume for persistent data...")
    try:
        ensure_volume("docgen-data")
        console.print_success("Volume ready.")
    except Exception as e:
        console.print_warning(f"Volume creation issue: {e}")

    # 7. Start services
    settings = get_settings()
    compose_file = getattr(settings, "docker", {})
    compose_path = getattr(compose_file, "compose_file", "docker-compose.yaml")

    start_services = console.confirm("Start background services (Weaviate)?")
    if start_services:
        try:
            # Resolve compose file relative to project root
            project_root = Path(__file__).resolve().parent.parent.parent
            full_compose_path = project_root / compose_path
            compose_up(str(full_compose_path))
            console.print_success("Services started.")
        except Exception as e:
            console.print_warning(f"Could not start services: {e}")

    console.print_header("Setup Complete")
    console.print_step("Run 'docgen run <git-url>' to generate documentation.")
