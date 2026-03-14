"""
SourceHandler - Haystack component for handling input sources.

Handles git repositories and local folders, collecting file paths for processing.
"""
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

from haystack import component

from src.components.LanguageFinder import LanguageFinder
from src.utils.llm_ignore_parser import get_llm_ignore_filter
from src.utils.logger import DocGenLogger

logger = DocGenLogger()


@component
class SourceHandler:
    """
    Haystack component that handles input sources (git repos or local folders).
    
    Collects all file paths for downstream processing.
    
    Usage:
        handler = SourceHandler()
        result = handler.run(source_type="local", path="/path/to/project")
    """
    
    def __init__(self):
        self.temp_dir: Optional[str] = None
        self.language_finder = LanguageFinder()
    
    @component.output_types(
        files=List[Dict[str, str]],
        working_dir=str,
    )
    def run(self, source_type: str, path: str, credentials: Optional[str] = None, api_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Process input source and collect file paths.
        
        Args:
            source_type: "git" or "local"
            path: Repository URL or local folder path
            credentials: Optional git credentials
            api_dir: Optional path to the api directory (for monorepos)
        Returns:
            Dictionary containing collected files and the working directory.
        """
        working_dir = self._prepare_working_directory(source_type, path, credentials)
        
        self._apply_local_llmignore(working_dir)

        # Analyze api directory, in-case of monorepo

        if(api_dir):
            working_dir= os.path.join(working_dir,api_dir)
        files = self._collect_files(working_dir)

        if not files:
            self.cleanup()
            raise ValueError("Please provide a codebase that creates REST APIs. No valid files found.")
        
        logger.info(f"Collected {len(files)} files from {working_dir}")
        
        return {
            "files": files,
            "working_dir": working_dir,
        }

    def _prepare_working_directory(self, source_type: str, path: str, credentials: Optional[str]) -> str:
        """Routes the input to the appropriate directory preparation method."""
        if source_type == "git":
            return self._clone_repo(path, credentials)
        if source_type == "local":
            return self._copy_local(path)
        
        raise ValueError(f"Invalid source_type: '{source_type}'. Must be 'git' or 'local'")

    def _apply_local_llmignore(self, working_dir: str) -> None:
        """Copies the main project's .llmignore to the working directory if applicable."""
        # Using pathlib to cleanly navigate up 3 directories from the current file
        project_root = Path(__file__).resolve().parents[2]
        local_ignore_path = project_root / ".llmignore"
        target_ignore_path = Path(working_dir) / ".llmignore"

        if local_ignore_path.exists() and Path(working_dir) != local_ignore_path.parent:
            shutil.copy2(local_ignore_path, target_ignore_path)
            logger.info(f"Copied .llmignore from {local_ignore_path} to {working_dir}")
    
    def _clone_repo(self, repo_url: str, credentials: Optional[str] = None) -> str:
        """Clone git repository to temp directory."""
        import git
        
        self.temp_dir = tempfile.mkdtemp(prefix="docgen_")
        final_url = repo_url
        
        if credentials and "@" not in repo_url and "https://" in repo_url:
            final_url = repo_url.replace("https://", f"https://{credentials}@")
        
        try:
            logger.info(f"Cloning {repo_url}...")
            git.Repo.clone_from(final_url, self.temp_dir)
            return self.temp_dir
        except Exception as e:
            self.cleanup()
            raise RuntimeError(f"Failed to clone repository: {e}")
    
    def _copy_local(self, folder_path: str) -> str:
        """Copy local folder to temp directory."""
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Local folder not found: {folder_path}")
        
        self.temp_dir = tempfile.mkdtemp(prefix="docgen_local_")
        
        try:
            shutil.copytree(folder_path, self.temp_dir, dirs_exist_ok=True)
            return self.temp_dir
        except Exception as e:
            self.cleanup()
            raise RuntimeError(f"Failed to copy local folder: {e}")
    
    def _collect_files(self, directory: str) -> List[Dict[str, str]]:
        """
        Collect all file paths from directory, excluding common ignore patterns.
        Detects the programming language for each file.
        """
        file_paths = []
        is_ignored = get_llm_ignore_filter(directory)
        
        for root, dirs, files in os.walk(directory):
            # gitignore_parser needs a trailing slash to correctly match directory rules
            dirs[:] = [d for d in dirs if not is_ignored(os.path.join(root, d) + os.sep)]
            
            for file_name in files:
                full_path = os.path.join(root, file_name)
                
                if is_ignored(full_path):
                    continue

                language = self.language_finder.detect(full_path)
                if language != 'unknown':
                    file_paths.append({
                        'path': full_path,
                        'language': language,
                        'relative_path': os.path.relpath(full_path, directory)
                    })
        
        return file_paths

    def cleanup(self) -> None:
        """Remove temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None