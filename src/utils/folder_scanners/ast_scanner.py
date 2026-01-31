"""AST folder scanner - scans folders containing JSON AST files."""
from typing import Dict, Any
import os
from src.utils.folder_scanners.base import FolderScanner
from src.utils.json_loader import load_json_file


class ASTFolderScanner(FolderScanner):
    """Scanner for AST JSON file folders."""
    
    def _is_valid_item(self, path: str, name: str) -> bool:
        """Only process .json files."""
        return os.path.isfile(path) and name.endswith('.json')
    
    def _process_item(self, path: str, name: str) -> Dict[str, Any]:
        """Load JSON file and return with filename."""
        data = load_json_file(path)
        if data is not None:
            return {'file_name': name, 'data': data}
        return None
