"""
docgen run -- Execute the documentation pipeline.

Usage:
  docgen run <git-url>
  docgen run <git-url> --background
"""

import multiprocessing
import os
from pathlib import Path
from typing import Any

import yaml

from cli.core import console, secrets
from cli.core.settings import get_settings, settings_to_config_dict

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


def run_pipeline(
    git_url: str,
    api_dir: str | None = None,
) -> dict[str, Any]:
    """
    Run the documentation pipeline on a git repository.

    Loads credentials from keyring, writes a config.yaml compatible with
    the existing pipeline, and executes it.
    """
    # Inject secrets into env
    env_injected = inject_credentials()
    if env_injected:
        console.print_step("Credentials loaded from secure storage.")

    # Write legacy config.yaml so existing pipeline code can consume it
    settings = get_settings()
    config_dict = settings_to_config_dict(settings)

    project_root = Path(__file__).resolve().parent.parent.parent
    config_path = project_root / "config.yaml"

    with open(config_path, "w") as f:
        yaml.dump(config_dict, f, default_flow_style=False)

    console.print_step(f"Generating documentation for: {git_url}")

    PipelineClass = DocumentationPipeline or _get_pipeline_class()
    pipeline = PipelineClass(config_path=str(config_path))
    result = pipeline.run(source_type="git", path=git_url, api_dir=api_dir)

    status = result.get("status", "unknown")
    if status == "completed":
        files = result.get("files", 0)
        endpoints = result.get("endpoints_found", 0)
        console.print_success(
            f"Pipeline completed. {files} files processed, {endpoints} endpoints found."
        )
    else:
        console.print_error(f"Pipeline failed: {result.get('error', 'unknown error')}")

    return result


def run_pipeline_background(git_url: str, api_dir: str | None = None) -> None:
    """Run the pipeline in a background process (cross-platform)."""
    process = multiprocessing.Process(
        target=run_pipeline,
        args=(git_url,),
        kwargs={"api_dir": api_dir},
        daemon=True,
    )
    process.start()
    console.print_step(f"Pipeline started in background (PID: {process.pid}).")
    console.print_step("Output will continue in the background process.")
