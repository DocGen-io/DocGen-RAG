"""
DocumentationMerger - Haystack component for merging endpoint documentation files.

This component scans the output directory for individual endpoint folders,
reads their swagger.json and postman.json files, and merges them into
complete Swagger/OpenAPI 3.0 and Postman Collection v2.1 output files.
"""

from haystack import component
from typing import Dict, Any, List, Optional
import os
import json
import logging

from src.utils.output_format_builders import SwaggerBuilder, PostmanCollectionBuilder
from src.utils.json_loader import load_json_file
from src.utils.config_loader import load_config
from src.utils.folder_scanners import EndpointFolderScanner
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)


@component
class DocumentationMerger:
    """
    Haystack component that merges individual endpoint documentation files
    into complete Swagger and Postman Collection files.
    
    Usage:
        merger = DocumentationMerger()
        result = merger.run(output_dir="output")
        print(f"Swagger: {result['swagger_path']}")
        print(f"Postman: {result['postman_path']}")
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the DocumentationMerger component.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        
        # Get merger-specific config with defaults
        merger_config = self.config.get("doc_merger", {})
        self.api_title = merger_config.get("api_title", "API Documentation")
        self.api_version = merger_config.get("api_version", "1.0.0")
        self.api_description = merger_config.get("api_description", "Auto-generated API documentation")
        self.base_url = merger_config.get("base_url", None)
        
        # Get default output dir from doc_creator config
        doc_creator_config = self.config.get("doc_creator", {})
        self.default_output_dir = doc_creator_config.get("output_dir", "output")
        self.endpoint_scanner = EndpointFolderScanner()
    
    @component.output_types(
        swagger_path=str,
        postman_path=str,
        endpoints_merged=int
    )
    def run(self, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Merge all endpoint documentation files into complete output files.
        
        Args:
            output_dir: Path to directory containing endpoint folders.
                       Defaults to config value if not provided.
                       
        Returns:
            Dictionary with:
                - swagger_path: Path to generated swagger.json
                - postman_path: Path to generated postman_collection.json
                - endpoints_merged: Number of endpoints merged
        """
        # Use provided output_dir or default from config
        output_dir = output_dir or self.default_output_dir
        
        output_dir = output_dir or self.default_output_dir
        
        logger.info(f"Starting DocumentationMerger on {output_dir}", location="run")
        
        # Scan for endpoint folders
        endpoints = self.endpoint_scanner.scan(output_dir)
        
        # Build Swagger spec
        swagger_builder = SwaggerBuilder(
            title=self.api_title,
            version=self.api_version,
            description=self.api_description,
            base_url=self.base_url
        )
        
        swagger_endpoints = [
            {
                "method_name": ep["method_name"],
                "http_method": ep["http_method"],
                "data": ep["swagger_data"]
            }
            for ep in endpoints
        ]
        
        swagger_spec = swagger_builder.build(swagger_endpoints)
        
        # Build Postman collection
        postman_builder = PostmanCollectionBuilder(
            collection_name=self.api_title,
            base_url=self.base_url
        )
        
        postman_endpoints = [
            {
                "method_name": ep["method_name"],
                "data": ep["postman_data"]
            }
            for ep in endpoints
        ]
        
        postman_collection = postman_builder.build(postman_endpoints)
        
        # Save output files
        swagger_path = os.path.join(output_dir, "swagger.json")
        postman_path = os.path.join(output_dir, "postman_collection.json")
        
        with open(swagger_path, "w", encoding="utf-8") as f:
            json.dump(swagger_spec, f, indent=2)
        
        with open(postman_path, "w", encoding="utf-8") as f:
            json.dump(postman_collection, f, indent=2)
        
        result = {
            "swagger_path": swagger_path,
            "postman_path": postman_path,
            "endpoints_merged": len(endpoints)
        }
        
        logger.info(
            f"DocumentationMerger complete: {result['endpoints_merged']} endpoints merged. "
            f"Swagger: {swagger_path}, Postman: {postman_path}",
            location="run"
        )
        
        return result
