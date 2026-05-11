"""
docgen run -- Execute the documentation pipeline.

Usage:
  docgen run                  Interactive mode (choose local or git)
  docgen run <git-url>        Git mode (direct)
  docgen run --background     Run in a background process
"""

from dynaconf.base import Settings
import multiprocessing
import os
from pathlib import Path
from typing import Any

import yaml

from cli.core import console, secrets
from cli.core.settings import (
    get_settings,
    settings_to_config_dict,
    MissingSettingError,
    save_user_setting,
    reset_settings,
)
from cli.core.config_schemas import REQUIRED_SETTINGS_CONFIG

# Module-level reference that tests can patch via `cli.commands.run.DocumentationPipeline`.
# Actual class is resolved at call time to avoid heavy imports on module load.
DocumentationPipeline = None


def _get_pipeline_class():
    """Lazy-load DocumentationPipeline to avoid heavy imports at module level."""
    global DocumentationPipeline
    if DocumentationPipeline is None:
        from src.pipelines.documentation_pipeline import DocumentationPipeline as _cls
        DocumentationPipeline = _cls
    return DocumentationPipeline


def inject_credentials() -> dict[str, str]:
    """
    Load credentials from the keyring and prepare environment variables
    for the pipeline to consume.

    Returns a dict of env vars that were injected.
    """
    env_vars: dict[str, str] = {}
    settings = get_settings()
    provider = getattr(settings, "active_provider", "gemini")

    if provider == "gemini":
        project = secrets.retrieve("google_project_id")
        location = secrets.retrieve("google_location")
        if project:
            os.environ["GOOGLE_CLOUD_PROJECT"] = project
            env_vars["GOOGLE_CLOUD_PROJECT"] = project
        if location:
            os.environ["GOOGLE_CLOUD_LOCATION"] = location
            env_vars["GOOGLE_CLOUD_LOCATION"] = location

    elif provider == "openai":
        api_key = secrets.retrieve("openai_api_key")
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            env_vars["OPENAI_API_KEY"] = "***"

    elif provider == "ollama":
        url = secrets.retrieve("ollama_url")
        if url:
            os.environ["OLLAMA_URL"] = url
            env_vars["OLLAMA_URL"] = url

    return env_vars


# Helper to loop and prompt user for missing settings


def loop_missing_settings(e: MissingSettingError, settings: Settings) -> None:
    """Prompt the user dynamically for a missing setting using REQUIRED_SETTINGS_CONFIG."""
    config = REQUIRED_SETTINGS_CONFIG.get(e.key)
    
    if config:
        prompt_type = config.get("type", "text")
        
        # Resolve dynamic message
        msg_val = config.get("message")
        message = msg_val(settings) if callable(msg_val) else msg_val
        
        # Prompt based on type
        if prompt_type == "select":
            choices_val = config.get("choices", [])
            choices = choices_val(settings) if callable(choices_val) else choices_val
            val = console.select(message, choices=choices)
        else:
            default_val = config.get("default")
            default = default_val(settings) if callable(default_val) else default_val
            val = console.text(message, default=default)
            
        error_message = config.get("error_message", f"Value for '{e.key}' is required to continue.")
    else:
        # Fallback for unregistered settings
        message = f"Enter value for '{e.key}':"
        val = console.text(message)
        error_message = f"Value for '{e.key}' is required to continue."

    if not val:
        console.print_error(error_message)
        raise SystemExit(1)
        
    save_user_setting(e.key, val)
    # Reset settings so they are re-evaluated in the next loop iteration
    reset_settings()


def run_pipeline(
    path: str,
    source_type: str = "git",
    api_dir: str | None = None,
) -> dict[str, Any]:
    """
    Run the documentation pipeline on a local project or git repository.

    Loads credentials from keyring, writes a config.yaml compatible with
    the existing pipeline, and executes it.
    """
    # Inject secrets into env
    env_injected = inject_credentials()
    if env_injected:
        console.print_step("Credentials loaded from secure storage.")

    # Write legacy config.yaml so existing pipeline code can consume it
    while True:
        settings = get_settings()
        try:
            config_dict = settings_to_config_dict(settings)
            break
        except MissingSettingError as e:
            console.print_warning(f"Missing required configuration: {e}")
            loop_missing_settings(e, settings)

    project_root = Path(__file__).resolve().parent.parent.parent
    config_path = project_root / "config.yaml"

    with open(config_path, "w") as f:
        yaml.dump(config_dict, f, default_flow_style=False)

    console.print_step(f"Generating documentation for: {path}")

    PipelineClass = DocumentationPipeline or _get_pipeline_class()
    pipeline = PipelineClass(config_path=str(config_path))
    result = pipeline.run(source_type=source_type, path=path, api_dir=api_dir)

    status = result.get("status", "unknown")
    if status == "completed":
        files = result.get("files", 0)
        endpoints = result.get("endpoints_found", 0)
        console.print_success(
            f"Pipeline completed. {files} files processed, {endpoints} endpoints found."
        )
        swagger_path = result.get("swagger_path")
        if swagger_path:
            abs_path = os.path.abspath(swagger_path)
            console.console.print(
                f"\n  [bold green]Swagger API Specification generated successfully![/bold green]"
            )
            console.console.print(
                f"  Click to access: [link=file://{abs_path}]file://{abs_path}[/link]\n",
                style="bold cyan"
            )
            try:
                if console.confirm("Would you like to open the generated Swagger JSON file in your default browser?", default=False):
                    import webbrowser
                    webbrowser.open(f"file://{abs_path}")
            except Exception:
                # Fallback gracefully if running in a non-interactive/headless shell
                pass
    else:
        console.print_error(f"Pipeline failed: {result.get('error', 'unknown error')}")

    return result


def run_pipeline_background(path: str, source_type: str = "git", api_dir: str | None = None) -> None:
    """Run the pipeline in a background process (cross-platform)."""
    process = multiprocessing.Process(
        target=run_pipeline,
        args=(path,),
        kwargs={"source_type": source_type, "api_dir": api_dir},
        daemon=True,
    )
    process.start()
    console.print_step(f"Pipeline started in background (PID: {process.pid}).")
    console.print_step("Output will continue in the background process.")
