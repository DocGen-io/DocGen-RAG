"""
Docker and volume management utilities.

Provides thin wrappers around Docker CLI commands for:
  - Named volume creation
  - Compose lifecycle (up/down)
  - Container status checks
"""

import subprocess


def ensure_volume(name: str) -> None:
    """Create a Docker named volume if it does not already exist."""
    result = subprocess.run(
        ["docker", "volume", "inspect", name],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        subprocess.run(
            ["docker", "volume", "create", name],
            check=True,
            capture_output=True,
            text=True,
        )


def compose_up(compose_path: str) -> None:
    """Start services defined in a docker-compose file."""
    subprocess.run(
        ["docker", "compose", "-f", compose_path, "up", "-d"],
        check=True,
        capture_output=True,
        text=True,
    )


def compose_down(compose_path: str) -> None:
    """Stop services defined in a docker-compose file."""
    subprocess.run(
        ["docker", "compose", "-f", compose_path, "down"],
        check=False,
        capture_output=True,
        text=True,
    )


def is_running(container_name: str) -> bool:
    """Check if a Docker container is currently running."""
    result = subprocess.run(
        [
            "docker", "inspect", "-f",
            "{{.State.Running}}", container_name,
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"
