"""
JSON file utilities for loading AST and code mapper data.

This module provides a unified function for loading JSON files
that can be used by both the AST extractor and WeaviateCodeWriter.
"""

import json
import os
import logging
from typing import List, Dict, Any, Union, Optional

logger = logging.getLogger(__name__)


def load_json_file(file_path: str) -> Optional[Union[List, Dict]]:
    """
    Load a single JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Parsed JSON data (list or dict) or None if error
    """
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON in {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return None


def load_json_folder(folder_path: str) -> List[Dict[str, Any]]:
    """
    Load all JSON files from a folder.
    
    Returns a list of dicts, each containing:
    - file_name: The filename of the JSON file
    - data: The parsed JSON content
    
    Args:
        folder_path: Path to folder containing JSON files
        
    Returns:
        List of dictionaries with file_name and data
    """
    json_files = []
    
    if not os.path.exists(folder_path):
        logger.warning(f"Folder does not exist: {folder_path}")
        return json_files
    
    if not os.path.isdir(folder_path):
        logger.warning(f"Path is not a directory: {folder_path}")
        return json_files
    
    for filename in sorted(os.listdir(folder_path)):
        if filename.endswith('.json'):
            filepath = os.path.join(folder_path, filename)
            data = load_json_file(filepath)
            if data is not None:
                json_files.append({
                    'file_name': filename,
                    'data': data
                })
    
    logger.info(f"Loaded {len(json_files)} JSON files from {folder_path}")
    return json_files


def flatten_ast_methods(ast_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Flatten AST data to a list of method dictionaries.
    Each method will already have class_name and file_name from the base_extractor.
    
    Args:
        ast_data: List of class definitions from AST JSON files
        
    Returns:
        List of method dictionaries with all metadata
    """
    methods = []
    
    for file_info in ast_data:
        file_name = file_info.get('file_name', 'unknown')
        data = file_info.get('data', [])
        
        # Handle both array and single object formats
        classes = data if isinstance(data, list) else [data]
        
        for class_info in classes:
            class_methods = class_info.get('methods', [])
            for method in class_methods:
                # Method already has class_name and file_name from base_extractor
                # Just ensure it has all the class-level metadata too
                method_with_context = {
                    **method,
                    'class_type': class_info.get('class_type', ''),
                    'base_path': class_info.get('base_path', '/')
                }
                methods.append(method_with_context)
    
    return methods
