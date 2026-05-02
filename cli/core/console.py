"""
Console output and interactive prompts.

Single Rich Console instance + thin wrappers around questionary prompts.
No emoji, no icons, no cliche words -- just clean professional output.
"""

import sys
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def _check_abort(result):
    """Exit cleanly if the user aborts a prompt (Ctrl+C)."""
    if result is None:
        print_warning("Operation cancelled by user.")
        sys.exit(1)
    return result


def print_header(text: str) -> None:
    """Print a styled section header."""
    console.print(Panel(text, style="bold cyan", expand=False))


def print_step(text: str) -> None:
    """Print a step/progress message."""
    console.print(f"  {text}", style="dim")


def print_success(text: str) -> None:
    """Print a success message."""
    console.print(f"  {text}", style="bold green")


def print_error(text: str) -> None:
    """Print an error message."""
    console.print(f"  Error: {text}", style="bold red")


def print_warning(text: str) -> None:
    """Print a warning message."""
    console.print(f"  Warning: {text}", style="yellow")


def confirm(message: str, default: bool = True) -> bool:
    """Ask for yes/no confirmation."""
    return _check_abort(questionary.confirm(message, default=default).ask())


def select(message: str, choices: list[str]) -> str:
    """Ask user to select from a list."""
    return _check_abort(questionary.select(message, choices=choices).ask())


def text(message: str, default: str = "") -> str:
    """Ask for free-form text input."""
    return _check_abort(questionary.text(message, default=default).ask())


def password(message: str) -> str:
    """Ask for sensitive input (masked)."""
    return _check_abort(questionary.password(message).ask())


def make_table(title: str, columns: list[str]) -> Table:
    """Create a Rich table with the given columns."""
    table = Table(title=title, show_lines=True)
    for col in columns:
        table.add_column(col, style="cyan")
    return table
