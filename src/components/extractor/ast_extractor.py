"""
ASTExtractor - Haystack component for extracting AST from source files.

Routes to the appropriate language-specific extractor based on file extension.
Supports Java, TypeScript, Python, and C#.
"""
import os
import json
from haystack import component
from typing import List, Dict, Any, Optional

from src.components.LanguageFinder import LanguageFinder
from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger

from .general_extractor import GeneralExtractor

@component
class ASTExtractor:
    """
    Haystack component that extracts AST from source files.
    
    Routes to the appropriate language-specific extractor based on file type.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the ASTExtractor component.
        """
        self.config = load_config(config_path)
        self.logger = DocGenLogger(self.__class__.__name__)
      
    
    def _extract_file(self, file_metadata: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract AST from a single file."""
        language = file_metadata['language']
        file_path = file_metadata['path']
        if language == 'unknown':
            self.logger.warning(f"Unknown language for file: {file_path}", location="_extract_file")
            return []
        
        return GeneralExtractor(language).extract(file_path, file_metadata)
    
    @component.output_types(
        ast_data=List[Dict[str, Any]],
        files_processed=int,
        files_failed=int
    )
    def run(self, files: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Extract AST from multiple source files.
        
        Args:
            file_paths: List of paths to source files
            
        Returns:
            Dictionary with:
                - ast_data: List of extracted AST class/method data
                - files_processed: Number of files successfully processed
                - files_failed: Number of files that failed
        """
        all_ast_data = []
        files_processed = 0
        files_failed = 0
        
        for file_metadata in files:
            file_path = file_metadata['path']
            if not os.path.exists(file_path):
                self.logger.warning(f"File not found: {file_path}", location="ast_extractor.run")
                files_failed += 1
                continue
            
            try:
                ast_data = self._extract_file(file_metadata)
                if ast_data:
                    all_ast_data.extend(ast_data)
                    files_processed += 1
                else:
                    files_failed += 1
            except Exception as e:
                self.logger.error(f"Error extracting {file_path}: {e}", location="ast_extractor.run")
                files_failed += 1
        
        self.logger.info(f"Extracted AST from {files_processed} files, {files_failed} failed", location="ast_extractor.run")
        
        return {
            "ast_data": all_ast_data,
            "files_processed": files_processed,
            "files_failed": files_failed
        }
