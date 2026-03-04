import os
import sqlite3
import subprocess
from typing import Dict, List, Any
from haystack import component
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)

@component
class FileHasher:
    """
    Haystack component that caches files using git hash-object.
    It takes input from SourceHandler and only passes along files
    that have changed since the last run.
    """
    
    def __init__(self, default_db_name: str = "dependencies.db"):
        self.default_db_name = default_db_name
        self.db_path = None
        
    def _init_db(self):
        """Initialize SQLite table for file hashes."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS file_hashes (
                        file_path TEXT UNIQUE,
                        git_hash TEXT
                    )
                ''')
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database for file_hashes: {e}")
            
    def _get_git_hash(self, file_path: str) -> str:
        """Computes the git hash-object for a given file."""

        try:
            result = subprocess.run(
                ["git", "hash-object", str(file_path)],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to compute git hash for {file_path}: {e.stderr}")
            return ""
        except Exception as e:
            logger.error(f"Failed to hash {file_path} due to unexpected error: {e}")
            return ""
            
    @component.output_types(
        files=List[Dict[str, str]],
        working_dir=str,
        pending_hashes=Dict[str, str]
    )
    def run(self, files: List[Dict[str, str]], working_dir: str, project_name: str) -> Dict[str, Any]:
        """
        Process the incoming list of files, hash them using Git, and return only the ones
        that have changed (or are new) since the last execution.
        """
        # Set up project-specific DB path
        output_dir = os.path.join("output", project_name)
        os.makedirs(output_dir, exist_ok=True)
        self.db_path = os.path.join(output_dir, self.default_db_name)
        self._init_db()
        
        changed_files = []
        pending_hashes = {}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for file_entry in files:
                    file_path = file_entry.get("path")
                    if not file_path or not os.path.exists(file_path):
                        continue
                        
                    current_hash = self._get_git_hash(file_path)
                    if not current_hash:
                        # Fallback: if hashing fails, process the file just in case
                        changed_files.append(file_entry)
                        continue
                        
                    # Check existing hash in DB
                    db_key = file_entry.get("relative_path")
                    if not db_key:
                        db_key = os.path.basename(file_path)
                        logger.warning(f"FileHasher missing relative_path for {file_path}, file_entry keys: {list(file_entry.keys())}, using fallback key: {db_key}")
                    else:
                        logger.info(f"FileHasher using relative_path: {db_key}")
                        
                    cursor.execute("SELECT git_hash FROM file_hashes WHERE file_path = ?", (db_key,))
                    row = cursor.fetchone()
                    
                    if row is None or row[0] != current_hash:
                        # It's new or modified
                        changed_files.append(file_entry)
                        pending_hashes[db_key] = current_hash
                        
                # No longer committing hashes here.
                
        except Exception as e:
            logger.error(f"Database error during file hashing: {e}")
            # Failsafe: return all files if DB is down
            return {"files": files, "working_dir": working_dir, "pending_hashes": {}}
            
        logger.info(f"FileHasher filtered {len(files)} files down to {len(changed_files)} changed files.")
        
        return {
            "files": changed_files,
            "working_dir": working_dir,
            "pending_hashes": pending_hashes
        }
