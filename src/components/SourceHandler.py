"""
SourceHandler - Haystack component for handling input sources.

Handles git repositories and local folders, collecting file paths for processing.
"""
import os
import shutil
import tempfile
import logging
from haystack import component
from typing import List, Dict, Any, Optional
from src.components.extractor.framework_detector import FrameworkDetector
from src.components.LanguageFinder import LanguageFinder
logger = logging.getLogger(__name__)

# Directories to exclude from file collection
EXCLUDED_DIRS = {'node_modules', '.git', '__pycache__', '.venv', 'venv', '.idea', '.vscode'}


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
        self.framework_detector = FrameworkDetector()
    
    @component.output_types(
        files=List[Dict[str, str]],
        working_dir=str,
    )
    def run(self, source_type: str, path: str, credentials: Optional[str] = None) -> Dict[str, Any]:
        """
        Process input source and collect file paths.
        
        Args:
            source_type: "git" or "local"
            path: Repository URL or local folder path
            credentials: Optional git credentials
            
        Returns:
            file_paths: List of all file paths
            working_dir: Working directory path
            file_count: Number of files found
        """
        if source_type == "git":
            working_dir = self._clone_repo(path, credentials)
        elif source_type == "local":
            working_dir = self._copy_local(path)
        else:
            raise ValueError(f"Invalid source_type: {source_type}. Must be 'git' or 'local'")
        
        # Collect file paths
        files = self._collect_files(working_dir)

        if not files:
            raise ValueError("Please provide a codebase that creates REST APIs")
        
        logger.info(f"Collected {len(files)} files from {working_dir}")
        
        return {
            "files": files,
            "working_dir": working_dir,
        }
    
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
        Operations on files:
            1- Language Finder - > to find the language of the file.
        
        """
        file_paths = []
        
        for root, dirs, files in os.walk(directory):
            # Remove excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            
            for f in files:
                language = self.language_finder.detect(os.path.join(root, f))
                if language != 'unknown':
                    file_metadata = {}
                    file_metadata['path'] = os.path.join(root, f)
                    file_metadata['language'] = language
                    try:
                        file_metadata['relative_path'] = os.path.relpath(os.path.join(root, f), directory)
                    except ValueError:
                         file_metadata['relative_path'] = f 
                    file_paths.append(file_metadata)
        
        return file_paths
    def cleanup(self):
        """Remove temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
