"""
DocumentationMerger - Haystack component for merging endpoint documentation files.

This component scans the output directory for individual endpoint folders,
reads their swagger.json files, and merges them into
complete Swagger/OpenAPI 3.0 Collection v2.1 output files.
"""

from haystack import component
from typing import Dict, Any, List, Optional
import os
import json
import logging
from src.utils.weaviateStore import WeaviateStore

from src.utils.output_format_builders import SwaggerBuilder
from src.utils.logger import DocGenLogger
from src.utils.config_loader import load_config
from src.utils.weaviateStore import resolve_weaviate_url

logger = DocGenLogger(__name__)


@component
class DocumentationMerger:
    """
    Haystack component that merges individual endpoint documentation files
    into complete Swagger Collection files.
    
    Usage:
        merger = DocumentationMerger()
        result = merger.run(output_dir="output")
        print(f"Swagger: {result['swagger_path']}")
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the DocumentationMerger component.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        weaviate_url = resolve_weaviate_url(self.config)
        self.store = WeaviateStore.get_store(url=weaviate_url)
        
        # Get merger-specific config with defaults
        merger_config = self.config.get("doc_merger", {})
        self.api_title = merger_config.get("api_title", "API Documentation")
        self.api_version = merger_config.get("api_version", "1.0.0")
        self.api_description = merger_config.get("api_description", "Auto-generated API documentation")
        self.base_url = merger_config.get("base_url", None)
        
        # Get default output dir from doc_creator config
        doc_creator_config = self.config.get("doc_creator", {})
        self.default_output_dir = doc_creator_config.get("output_dir", "output")

    @component.output_types(
        swagger_path=str,
        swagger_spec=Dict[str, Any],
        endpoints_merged=int
    )
    def run(
        self,
        project_name: str,
        output_dir: Optional[str] = None,
        api_details: Optional[Dict[str, Any]] = None,
        wait_for_weaviate: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Merge all endpoint documentation files into complete output files.
        
        Args:
            project_name: Name of the project to merge docs for
            output_dir: Path to directory containing endpoint folders (for output saving)
            api_details: Optional team/project info for filtering
            wait_for_weaviate: Dummy input for pipeline ordering
                        
        Returns:
            Dictionary with:
                - swagger_path: Path to generated swagger.json
                - swagger_spec: The complete Swagger/OpenAPI specification
                - endpoints_merged: Number of endpoints merged
        """
        # Use provided output_dir or default from config combined with project_name
        output_dir = output_dir or os.path.join(self.default_output_dir, project_name)
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Starting DocumentationMerger for project: {project_name}", location="run")
        
        # Build filter by doc_type and api_details
        conditions: List[Dict[str, Any]] = [
            {"field": "meta.doc_type", "operator": "==", "value": "endpoint_documentation"}
        ]
        
        if api_details:
            from src.utils.rbac_utils import to_uuid
            if "team_id" in api_details:
                conditions.append({"field": "meta.team_id", "operator": "==", "value": to_uuid(api_details["team_id"])})
            if "job_id" in api_details:
                conditions.append({"field": "meta.job_id", "operator": "==", "value": to_uuid(api_details["job_id"])})
            if "project_name" in api_details:
                conditions.append({"field": "meta.project_name", "operator": "==", "value": api_details["project_name"]})

        filters = {
            "operator": "AND",
            "conditions": conditions
        }

        # Fetch from Weaviate
        docs = self.store.filter_documents(filters=filters)
                
        logger.info(f"Fetched {len(docs)} endpoint documents from Weaviate for merging", location="run")

        if not docs:
            logger.warning(f"No documents found in Weaviate for project {project_name}")
            return {"swagger_path": "", "swagger_spec": {}, "endpoints_merged": 0}

        # Build Swagger spec
        swagger_builder = SwaggerBuilder(
            title=self.api_title,
            version=self.api_version,
            description=self.api_description,
            base_url=self.base_url
        )
        
        swagger_endpoints = []
        for doc in docs:
            raw_json = doc.meta.get("raw_json")
            if raw_json:
                swagger_data = json.loads(raw_json)
                swagger_endpoints.append({
                    "method_name": doc.meta.get("endpoint_name", "unknown"),
                    "http_method": doc.meta.get("method", "get"),
                    "data": swagger_data,
                    "node_id": doc.meta.get("node_id")
                })
        
        swagger_spec = swagger_builder.build(swagger_endpoints)
        
        # Save output files
        swagger_path = os.path.join(output_dir, "swagger.json")
        
        with open(swagger_path, "w", encoding="utf-8") as f:
            json.dump(swagger_spec, f, indent=2)
        
        result = {
            "swagger_path": swagger_path,
            "swagger_spec": swagger_spec,
            "endpoints_merged": len(swagger_endpoints)
        }
        
        logger.info(
            f"DocumentationMerger complete: {result['endpoints_merged']} endpoints merged. "
            f"Swagger: {swagger_path}",
            location="run"
        )
        
        return result
