"""
DocGen CLI -- Professional command-line interface for DocGen-RAG.

Usage:
  docgen init                        First-time setup
  docgen run <git-url>               Generate documentation
  docgen config show|set|reset       Manage configuration
  docgen provider list|add|remove    Manage AI providers
  docgen credentials set|check|clear Manage stored credentials
"""

from typing import Optional

import typer

from cli.core.console import print_header

app = typer.Typer(
    name="docgen",
    help="DocGen -- AI-powered API documentation generator.",
    add_completion=False,
    no_args_is_help=True,
)


# -- Top-level commands -------------------------------------------------------

@app.command()
def init() -> None:
    """Run the first-time setup wizard."""
    from cli.commands.init import run_init
    run_init()


@app.command()
def run(
    git_url: str = typer.Argument(..., help="Git repository URL to document."),
    api_dir: Optional[str] = typer.Option(None, "--api-dir", help="Subdirectory containing the API."),
    background: bool = typer.Option(False, "--background", help="Run in a background process."),
) -> None:
    """Generate documentation for a Git repository."""
    from cli.commands.run import run_pipeline, run_pipeline_background
    from cli.core.console import confirm as cli_confirm, text as cli_text

    # If --api-dir wasn't provided via CLI flag, offer interactive prompt
    if api_dir is None:
        if cli_confirm("Would you like to specify the API subdirectory path?", default=False):
            api_dir = cli_text("Enter the API subdirectory path (relative to repo root):")
            if not api_dir.strip():
                api_dir = None

    if background:
        run_pipeline_background(git_url, api_dir=api_dir)
    else:
        run_pipeline(git_url, api_dir=api_dir)


@app.command()
def outputs() -> None:
    """List generated Swagger specifications and view/open them."""
    from cli.commands.outputs import list_outputs
    list_outputs()


@app.command()
def reboard() -> None:
    """Reset configuration and run the first-time setup wizard again."""
    from cli.commands.config import reset_config
    from cli.commands.init import run_init
    from cli.core.console import print_step, print_header

    print_header("DocGen Reboarding")
    print_step("Resetting current configuration...")
    reset_config()
    print_step("Starting fresh setup...")
    run_init()


# -- Config subcommands -------------------------------------------------------

config_app = typer.Typer(
    name="config",
    help="View and manage configuration.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show() -> None:
    """Display current configuration."""
    from cli.commands.config import show_config
    show_config()


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Setting key (e.g. 'active_provider')."),
    value: str = typer.Argument(..., help="New value."),
) -> None:
    """Update a configuration value."""
    from cli.commands.config import set_config
    set_config(key, value)


@config_app.command("reset")
def config_reset() -> None:
    """Reset configuration to defaults."""
    from cli.commands.config import reset_config
    reset_config()


# -- Provider subcommands -----------------------------------------------------

provider_app = typer.Typer(
    name="provider",
    help="Manage AI provider strategies.",
    no_args_is_help=True,
)
app.add_typer(provider_app, name="provider")


@provider_app.command("list")
def provider_list() -> None:
    """List available providers."""
    from cli.commands.provider import list_available
    list_available()


@provider_app.command("add")
def provider_add(
    name: str = typer.Argument(..., help="Provider name (gemini, openai, ollama)."),
) -> None:
    """Fetch and install a provider."""
    from cli.commands.provider import add_provider
    add_provider(name)


@provider_app.command("remove")
def provider_remove(
    name: str = typer.Argument(..., help="Provider name to remove."),
) -> None:
    """Remove cached provider files."""
    from cli.commands.provider import remove_provider
    remove_provider(name)


# -- Credentials subcommands --------------------------------------------------

cred_app = typer.Typer(
    name="credentials",
    help="Manage stored credentials.",
    no_args_is_help=True,
)
app.add_typer(cred_app, name="credentials")


@cred_app.command("set")
def cred_set(
    provider: str = typer.Argument(..., help="Provider to configure (gemini, openai, ollama)."),
) -> None:
    """Set up credentials for a provider."""
    from cli.commands.credentials import set_credentials
    set_credentials(provider)


@cred_app.command("check")
def cred_check(
    provider: Optional[str] = typer.Argument(None, help="Specific provider to check (or all)."),
) -> None:
    """Check if required credentials are stored."""
    from cli.commands.credentials import check_credentials, check_all_credentials
    if provider:
        check_credentials(provider)
    else:
        check_all_credentials()


@cred_app.command("clear")
def cred_clear(
    provider: str = typer.Argument(..., help="Provider whose credentials to remove."),
) -> None:
    """Remove stored credentials for a provider."""
    from cli.commands.credentials import clear_credentials
    clear_credentials(provider)


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        from cli.core.console import print_warning
        import sys
        print_warning("Operation cancelled by user.")
        sys.exit(1)
