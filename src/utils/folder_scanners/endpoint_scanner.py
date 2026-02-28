"""Endpoint folder scanner - scans endpoint subdirectories with swagger files."""
from typing import Dict, Any
import os
import logging
from src.utils.folder_scanners.base import FolderScanner
from src.utils.json_loader import load_json_file
from src.utils.definitions import API_METHODS

logger = logging.getLogger(__name__)


class EndpointFolderScanner(FolderScanner):
    """Scanner for endpoint documentation folders."""
    
    def _is_valid_item(self, path: str, name: str) -> bool:
        """Only process directories containing swagger.json."""
        if not os.path.isdir(path):
            return False
        swagger_path = os.path.join(path, "swagger.json")
        return os.path.exists(swagger_path)
    
    def _process_item(self, path: str, name: str) -> Dict[str, Any]:
        """Load swagger data from endpoint folder."""
        swagger_path = os.path.join(path, "swagger.json")
        
        swagger_data = load_json_file(swagger_path)
        if swagger_data is None:
            logger.warning(f"Failed to load swagger.json from {name}")
            return None
        
        http_method = self._extract_http_method(swagger_data)
        
        # Skip endpoints without HTTP method
        if http_method is None:
            logger.error(f"Skipping endpoint '{name}': no HTTP method found in swagger data")
            return None
        
        return {
            "method_name": name,
            "http_method": http_method,
            "swagger_data": swagger_data,
        }
    
    def _extract_http_method(self, swagger_data: Dict) -> str:
        """Extract HTTP method from endpoint data. Returns None if not found."""
        # 1. Check top-level keys first (injected by DocCreator)
        for field in ["method", "httpMethod", "http_method"]:
            if swagger_data.get(field):
                return swagger_data[field]
                
        # 2. Check within 'paths' if the LLM outputted a full paths object
        if "paths" in swagger_data:
            for path, path_obj in swagger_data["paths"].items():
                if isinstance(path_obj, dict):
                    for method in API_METHODS:
                        if method in path_obj:
                            return method
                            
        # 3. Check if the root level IS the path object itself
        for method in API_METHODS:
            if method in swagger_data:
                return method
                
        return None

