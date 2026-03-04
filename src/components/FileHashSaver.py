import os
import sqlite3
from typing import Dict, Any
from haystack import component
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)

@component
class FileHashSaver:
    """
    Haystack component that saves the files hashes to the database ONLY 
    after the rest of the pipeline successfully completes.
    """
    def __init__(self, default_db_name: str = "dependencies.db"):
        self.default_db_name = default_db_name
        self.db_path = None
        
    @component.output_types(
        hashes_saved=int
    )
    def run(self, pending_hashes: Dict[str, str], project_name: str, merge_status: Any) -> Dict[str, Any]:
        """
        Saves the hashes into SQLite upon pipeline success.
        `merge_status` is an arbitrary signal variable to force this component 
        to execute at the end of the DAG.
        """
        if not pending_hashes:
            return {"hashes_saved": 0}
            
        output_dir = os.path.join("output", project_name)
        os.makedirs(output_dir, exist_ok=True)
        self.db_path = os.path.join(output_dir, self.default_db_name)
        
        saved_count = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS file_hashes (
                        file_path TEXT UNIQUE,
                        git_hash TEXT
                    )
                ''')
                
                for db_key, current_hash in pending_hashes.items():
                    cursor.execute('''
                        INSERT OR REPLACE INTO file_hashes (file_path, git_hash)
                        VALUES (?, ?)
                    ''', (db_key, current_hash))
                    saved_count += 1
                    
                conn.commit()
                logger.info(f"FileHashSaver successfully saved {saved_count} file hashes to {self.default_db_name}.")
        except Exception as e:
            logger.error(f"Failed to save document hashes to SQLite at pipeline completion: {e}")
            
        return {"hashes_saved": saved_count}
