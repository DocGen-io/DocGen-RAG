import os
import shutil
import tempfile
import git
from pathlib import Path
from typing import Optional

class InputHandler:
    """
    Handles input sources for the documentation generation (Git Repos or Local Folders).
    """

    def __init__(self):
        self.temp_dir: Optional[str] = None

    def process_git_repo(self, repo_url: str, credentials: Optional[str] = None) -> str:
        """
        Clones a git repo to a temporary directory.
        Credentials handling is simplified for this demo (assumes https with auth token in URL if needed, 
        or SSH key configured in environment).
        """
        self.temp_dir = tempfile.mkdtemp(prefix="docgen_rag_")
        
        # Insert credentials into URL if provided and not already present
        final_url = repo_url
        if credentials and "@" not in repo_url and "https://" in repo_url:
            final_url = repo_url.replace("https://", f"https://{credentials}@")

        try:
            print(f"Cloning {repo_url} into {self.temp_dir}...")
            git.Repo.clone_from(final_url, self.temp_dir)
            return self.temp_dir
        except Exception as e:
            self.cleanup()
            raise RuntimeError(f"Failed to clone repository: {e}")

    def process_local_folder(self, folder_path: str) -> str:
        """
        Copies a local folder to a temporary directory to avoid modifying the source.
        """
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Local folder not found: {folder_path}")

        self.temp_dir = tempfile.mkdtemp(prefix="docgen_rag_local_")
        
        # We copy individual items to avoid copying the root folder *into* the temp dir, 
        # we want the contents *of* the folder in the temp dir.
        try:
             shutil.copytree(folder_path, self.temp_dir, dirs_exist_ok=True)
             return self.temp_dir
        except Exception as e:
            self.cleanup()
            raise RuntimeError(f"Failed to copy local folder: {e}")

    def cleanup(self):
        """
        Removes the temporary directory.
        """
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
