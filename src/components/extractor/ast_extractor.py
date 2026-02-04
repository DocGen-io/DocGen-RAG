"""
ASTExtractor - Haystack component for extracting AST from source files.

Routes to the appropriate language-specific extractor based on file extension.
Supports Java, TypeScript, Python, and C#.
"""
import os
import json
from haystack import component
from typing import List, Dict, Any, Optional
import logging

from src.components.LanguageFinder import LanguageFinder
from src.utils.config_loader import load_config

from .general_extractor import GeneralExtractor

logger = logging.getLogger(__name__)


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
        self._language_finder = LanguageFinder()
      
    
    def _extract_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract AST from a single file."""
        language = self._language_finder.detect(file_path)
        if language == 'unknown':
            logger.warning(f"Unknown language for file: {file_path}")
            return []
        
        return GeneralExtractor(language).extract(file_path)
    
    @component.output_types(
        ast_data=List[Dict[str, Any]],
        files_processed=int,
        files_failed=int
    )
    def run(self, file_paths: List[str]) -> Dict[str, Any]:
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
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                files_failed += 1
                continue
            
            try:
                ast_data = self._extract_file(file_path)
                if ast_data:
                    all_ast_data.extend(ast_data)
                    files_processed += 1
                else:
                    files_failed += 1
            except Exception as e:
                logger.error(f"Error extracting {file_path}: {e}")
                files_failed += 1
        
        logger.info(f"Extracted AST from {files_processed} files, {files_failed} failed")
        
        return {
            "ast_data": all_ast_data,
            "files_processed": files_processed,
            "files_failed": files_failed
        }
