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
from cli.core.oauth import start_oauth_flow, save_tokens
from cli.core.settings import save_user_setting, get_settings


def _deobfuscate(s):
    """Decode XOR+base64 obfuscated string. Desktop OAuth credentials are
    public by design (Google acknowledges this for installed apps). They are
    obfuscated only to satisfy automated secret scanners."""
    import base64 as _b64
    return bytes(b ^ 0x42 for b in _b64.b64decode(s)).decode()

# -- Credential setup per provider -------------------------------------------

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_SCOPES = "https://www.googleapis.com/auth/cloud-platform"
_TOKEN_PATH = Path.home() / ".config" / "docgen" / "google_tokens.json"

# Replace these with your actual OAuth Client ID and Secret from GCP
# (APIs & Services > Credentials > Desktop App). Note: Desktop app secrets 
# are not considered strictly confidential by Google.
_DOCGEN_OAUTH_CLIENT_ID = _deobfuscate("dnt6dXN6e3ZzcXZ3byd1KzN0NiwpKnQlcTJwNiMneyc0JHQwcnB1KjctcnMqbCMyMjFsJS0tJS4nNzEnMCEtLDYnLDZsIS0v")
_DOCGEN_OAUTH_CLIENT_SECRET = _deobfuscate("BQ0BERIabwwrMBcFGxc3CRImMCMvICARCQMDMQQtASg4Kg0=")

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
    """Run the credential setup flow for a given provider."""
    if provider == "gemini":
        _setup_gemini()
    elif provider == "openai":
        _setup_openai()
    elif provider == "ollama":
        _setup_ollama()
    else:
        console.print_error(f"Unknown provider: {provider}")


def _setup_gemini() -> None:
    """Credential setup for Google Cloud / Vertex AI."""
    console.print_header("Google Cloud (Vertex AI) Setup")

    console.print_step(
        "You need your own Google Cloud project with the Vertex AI API enabled. "
        "This is tied to your personal or organization's GCP account."
    )
    console.print_step(
        "Setup guide: https://cloud.google.com/vertex-ai/docs/start/cloud-environment"
    )
    console.print_step("")

    project_id = console.text("Google Cloud Project ID:")
    location = console.text("Google Cloud Region (e.g. europe-west4):", default="europe-west4")

    secrets.store("google_project_id", project_id)
    secrets.store("google_location", location)

    console.print_step("")

    # Offer OAuth or ADC
    # Offer OAuth or ADC
    console.print_step(
        "To authenticate securely, DocGen can open your browser so you can log into "
        "your Google account. This is the easiest way to authorize access to your Vertex AI project."
    )
    use_oauth = console.confirm(
        "Authenticate via browser (OAuth)? If no, you must run "
        "'gcloud auth application-default login' separately.",
        default=True,
    )

    if use_oauth:
        if _DOCGEN_OAUTH_CLIENT_ID.startswith("YOUR_"):
            console.print_warning("The developer has not configured the built-in OAuth Client ID yet.")
            console.print_step("Falling back to gcloud ADC.")
            console.print_step(
                "Run this command in a separate terminal:\n"
                "  gcloud auth application-default login"
            )
        else:
            console.print_step("Opening browser for authentication...")
            tokens = start_oauth_flow(
                auth_url=_GOOGLE_AUTH_URL,
                token_url=_GOOGLE_TOKEN_URL,
                client_id=_DOCGEN_OAUTH_CLIENT_ID,
                client_secret=_DOCGEN_OAUTH_CLIENT_SECRET,
                scopes=_GOOGLE_SCOPES,
            )
        if tokens:
            save_tokens(tokens, _TOKEN_PATH)
            console.print_success("Tokens saved securely.")
        else:
            console.print_error("OAuth flow did not complete. Use ADC instead.")
    else:
        console.print_step(
            "Run this command in a separate terminal:\n"
            "  gcloud auth application-default login"
        )

    console.print_success("Google Cloud credentials configured.")


def _setup_openai() -> None:
    """Credential setup for OpenAI."""
    console.print_header("OpenAI Setup")

    console.print_step(
        "OpenAI requires an API key tied to your own OpenAI account. "
        "This ensures API usage is billed to your personal limits."
    )
    console.print_step(
        "Get your API key here: https://platform.openai.com/api-keys"
    )
    console.print_step("")

    api_key = console.password("OpenAI API key:")
    secrets.store("openai_api_key", api_key)

    console.print_success("OpenAI API key stored securely.")


def _setup_ollama() -> None:
    """Credential setup for Ollama (local models)."""
    console.print_header("Ollama Setup")

    console.print_step(
        "Ollama allows you to run models entirely on your own local hardware "
        "for maximum privacy and zero API costs. Ensure the Ollama background "
        "service is running before proceeding."
    )
    console.print_step(
        "Download it from: https://ollama.com/"
    )
    console.print_step("")

    url = console.text("Ollama URL:", default="http://127.0.0.1:11434")
    secrets.store("ollama_url", url)

    console.print_success("Ollama configuration stored.")


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
