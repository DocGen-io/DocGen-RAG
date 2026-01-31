"""Endpoint folder scanner - scans endpoint subdirectories with swagger/postman files."""
from typing import Dict, Any
import os
import logging
from src.utils.folder_scanners.base import FolderScanner
from src.utils.json_loader import load_json_file

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
        """Load swagger and postman data from endpoint folder."""
        swagger_path = os.path.join(path, "swagger.json")
        postman_path = os.path.join(path, "postman.json")
        
        swagger_data = load_json_file(swagger_path)
        if swagger_data is None:
            logger.warning(f"Failed to load swagger.json from {name}")
            return None
        
        postman_data = load_json_file(postman_path) if os.path.exists(postman_path) else {}
        http_method = self._extract_http_method(swagger_data, postman_data)
        
        # Skip endpoints without HTTP method
        if http_method is None:
            logger.error(f"Skipping endpoint '{name}': no HTTP method found in swagger or postman data")
            return None
        
        return {
            "method_name": name,
            "http_method": http_method,
            "swagger_data": swagger_data,
            "postman_data": postman_data or {}
        }
    
    def _extract_http_method(self, swagger_data: Dict, postman_data: Dict) -> str:
        """Extract HTTP method from endpoint data. Returns None if not found."""
        # Try postman first
        if postman_data.get("method"):
            return postman_data["method"]
        if postman_data.get("request", {}).get("method"):
            return postman_data["request"]["method"]
        # Try swagger
        for field in ["method", "httpMethod", "http_method"]:
            if swagger_data.get(field):
                return swagger_data[field]
        return None

