#!/usr/bin/env python3
import os
import sys

# Resolve project root and virtual environment Python interpreter
script_path = os.path.realpath(__file__)
repo_dir = os.path.dirname(os.path.dirname(script_path))
venv_python = os.path.join(repo_dir, ".venv", "bin", "python")

# If we are not currently running under the virtual environment's Python interpreter,
# and the virtual environment's python exists, re-execute using it!
if sys.executable != venv_python and os.path.exists(venv_python):
    os.execv(venv_python, [venv_python, script_path] + sys.argv[1:])

# Now we are guaranteed to run under the venv's Python, or we fallback gracefully.
if repo_dir not in sys.path:
    sys.path.insert(0, repo_dir)

from cli.app import app

if __name__ == "__main__":
    app()
