import os
import sys
import webbrowser
from pathlib import Path
from cli.core import console


def list_outputs() -> None:
    """Find and display all generated swagger.json specifications, allowing the user to select and view one."""
    console.print_header("Generated Swagger Specifications")

    output_dir = Path("output")
    if not output_dir.exists() or not output_dir.is_dir():
        console.print_warning(
            "No output directory found. Generate some specifications first with 'docgen run <git-url>'."
        )
        return

    # Scan for master swagger.json files only (depth 2: output/<project_name>/swagger.json)
    swagger_files = sorted(list(output_dir.glob("*/swagger.json")))
    if not swagger_files:
        console.print_warning(
            "No final swagger.json files found. Generate some specifications first with 'docgen run <git-url>'."
        )
        return

    # Prepare display choices
    choices = []
    file_map = {}
    for path in swagger_files:
        project_name = path.parent.name
        display_name = f"{project_name} (final swagger)"
        choices.append(display_name)
        file_map[display_name] = path

    choices.append("[Cancel]")

    # Select which specification to view
    selected = console.select("Select a Swagger specification to access:", choices=choices)
    if selected == "[Cancel]":
        console.print_step("Operation cancelled.")
        return

    selected_file = file_map.get(selected)
    if not selected_file:
        return

    abs_path = selected_file.resolve()
    console.console.print(
        f"\n  [bold green]Selected: {selected_file.parent.name}[/bold green]"
    )
    console.console.print(
        f"  Clickable terminal link: [link=file://{abs_path}]file://{abs_path}[/link]\n",
        style="bold cyan"
    )

    # Prompt action on selection
    action_choices = [
        "Open in default web browser",
        "Print absolute file path",
        "Cancel",
    ]
    action = console.select("What would you like to do with this specification?", choices=action_choices)

    if action == "Open in default web browser":
        console.print_step(f"Opening browser to file://{abs_path}")
        webbrowser.open(f"file://{abs_path}")
    elif action == "Print absolute file path":
        console.console.print(f"  {abs_path}\n", style="bold")
    else:
        console.print_step("Operation cancelled.")
