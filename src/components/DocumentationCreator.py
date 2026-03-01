"""
DocumentationCreator - Haystack component for generating REST API documentation.

This component analyzes code_mapper output, fetches dependency information from Weaviate,
and uses LLM to generate comprehensive API documentation in Swagger formats.
"""

import os
import json
from string import Template
from haystack import component
from src.utils.logger import DocGenLogger
from typing import Dict, Any, List, Optional
from src.utils.config_loader import load_config
from src.utils.llm_json_handler import LLMJsonHandler
from src.utils.weaviate_utils import fetch_by_node_id
from src.utils.dependency_graph import DependencyGraph
from src.utils.modelGenerator import ModelGenerator
from prompts import doc_creator_prompt as DOCUMENTATION_PROMPT
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
from src.utils.definitions import API_METHODS
logger = DocGenLogger(__name__)


@component
class DocumentationCreator:
    """
    Haystack component that generates REST API documentation from code analysis.
    
    Processes mapped_ast.json and AST files to create Swagger documentation
    for each API endpoint.
    """
    
    def __init__(
        self,
        weaviate_url: str = "http://127.0.0.1:8080",
        config_path: str = "config.yaml"
    ):
        self.generator = ModelGenerator("doc_creator", config_path).get_generator()
        self.config = load_config(config_path)
        self.output_dir = self.config.get("doc_creator", {}).get("output_dir", "output")
        
        # Initialize Weaviate document store
        self.document_store = WeaviateDocumentStore(url=weaviate_url)
    
    def _fetch_dependency_context(self, node_ids: List[str]) -> str:
        """Fetch code context from Weaviate for a list of node IDs."""
        if not node_ids:
            return "No internal dependencies identified."
        
        context_parts = []
        for node_id in node_ids:
            # Fetch from Weaviate using composite ID
            docs = fetch_by_node_id(self.document_store, node_id)
            
            if docs:
                doc = docs[0]
                context_parts.append(f"**{node_id}**:\n{doc.content}\n")
            else:
                context_parts.append(f"**{node_id}**: No additional context available.\n")
        
        return "\n".join(context_parts) if context_parts else "No dependency context found."
    
    def _build_prompt(self, method: Dict, dependencies_context: str) -> str:
        """Build the LLM prompt for documentation generation."""
        return DOCUMENTATION_PROMPT.substitute(
            controller_name=method.get("class_name", "Unknown"),
            method_name=method.get("method_name", "unknown"),
            http_method=method.get("method_type", "GET"),
            endpoint_path=method.get("method_path", "/"),
            base_path=method.get("base_path", "/"),
            method_definition=method.get("method_definition", ""),
            dependencies_context=dependencies_context
        )
    
  
  

    @component.output_types(
        methods_processed=int,
        methods_failed=int,
        output_files=Dict[str, Dict[str, str]],
        output_dir=str
    )
    def run(
        self,
        endpoint_graphs: Optional[Dict[str, Any]] = None,
        project_name: str = ""
    ) -> Dict[str, Any]:
        """
        Process EndpointGraphs, fetch code context, and generate API documentation.

        Args:
            endpoint_graphs: Dictionary mapping endpoint_id to DependencyGraph objects
            project_name: Name of the project to isolate outputs (appended to output_dir)

        Returns:
            Dictionary with processing results
        """
        logger.info(f"Starting DocumentationCreator")

        project_output_dir = os.path.join(self.output_dir, project_name) if project_name else self.output_dir
        self._project_output_dir = project_output_dir

        if not endpoint_graphs:
            logger.warning("No endpoint graphs found to document")
            return {
                "methods_processed": 0,
                "methods_failed": 0,
                "output_files": {},
                "output_dir": project_output_dir
            }

        methods_processed = 0
        methods_failed = 0
        output_files = {}

        for endpoint_id, graph in endpoint_graphs.items():
            logger.info(f"Processing endpoint graph: {endpoint_id}")

            try:
                # 1. Gather all nodes involved in this endpoint (including the endpoint itself)
                node_ids = list(graph.get_all_nodes())

                # 2. Fetch context from Weaviate for all nodes
                dep_context = self._fetch_dependency_context(node_ids)
                
                # 3. Extract the endpoint method's details from Weaviate to guide the prompt
                endpoint_doc_list = fetch_by_node_id(self.document_store, endpoint_id)
                logger.info(f"Found {len(endpoint_doc_list)} doc(s) in Weaviate for {endpoint_id}")

                if not endpoint_doc_list:
                    logger.error(f"Endpoint {endpoint_id} not found in Weaviate. Skipping.")
                    methods_failed += 1
                    continue

                endpoint_doc = endpoint_doc_list[0]
                meta = endpoint_doc.meta

                api_details_str = meta.get("api_method_details", "{}")
                try:
                    api_details = json.loads(api_details_str) if isinstance(api_details_str, str) else api_details_str
                except Exception:
                    api_details = {}
                if not isinstance(api_details, dict):
                    api_details = {}

                raw_method_type = str(api_details.get("method_type", "unknown"))
               
                logger.info(f"Processing endpoint {endpoint_id} of type: {raw_method_type}")
                # Check if this is an internal/RPC method like `grpc_method`
                if raw_method_type.lower()  not in API_METHODS:
                    logger.info(f"Skipping non-REST method {endpoint_id} of type: {raw_method_type}")
                    # We still count it as 'processed' so it doesn't skew failure metrics, but we don't document it.
                    methods_processed += 1
                    continue
                    
                method_info = {
                    "class_name": meta.get("class_name", endpoint_id.split(":")[1] if len(endpoint_id.split(":")) > 1 else "Unknown"),
                    "method_name": meta.get("name", endpoint_id.split(":")[2] if len(endpoint_id.split(":")) > 2 else "unknown"),
                    "method_type": raw_method_type.lower(),
                    # LLM writes 'path', fallback to 'method_path' for older docs
                    "method_path": api_details.get("path", api_details.get("method_path", "/")),
                    "base_path": api_details.get("base_path", "/"),
                    "method_definition": endpoint_doc.content
                }
                
                # 4. Build prompt and generate
                prompt = self._build_prompt(method_info, dep_context)
                documentation = LLMJsonHandler.parse_with_retry(generator=self.generator, prompt=prompt,max_retries=3)
                
                if documentation:
                    method_name = method_info.get("method_name", "unknown")
                    saved_files = self._save_outputs(method_name, documentation, method_info)
                    output_files[method_name] = saved_files
                    methods_processed += 1
                else:
                    logger.error(f"Failed to generate docs for {endpoint_id}")
                    methods_failed += 1
                    
            except Exception as e:
                logger.error(f"Error processing {endpoint_id}: {e}")
                methods_failed += 1
        
        result = {
            "methods_processed": methods_processed,
            "methods_failed": methods_failed,
            "output_files": output_files,
            "output_dir": project_output_dir
        }
        
        logger.info(f"DocumentationCreator complete: {methods_processed} processed, {methods_failed} failed")
        return result

    def _save_outputs(
        self,
        method_name: str,
        documentation: Dict[str, Any],
        method_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Write documentation files for a single endpoint method.

        Args:
            method_name: The method/endpoint name (used as subdirectory)
            documentation: LLM output dict with a 'swagger' key
            method_info: Optional dict with method_type, method_path, base_path for enrichment

        Returns:
            Dict mapping 'swagger' to the written file path
        """
        output_dir = getattr(self, "_project_output_dir", self.output_dir)
        method_dir = os.path.join(output_dir, method_name)
        os.makedirs(method_dir, exist_ok=True)

        swagger_data = documentation.get("swagger", {})

        if method_info:
            base_path = method_info.get("base_path", "")
            method_path = method_info.get("method_path", "")
            fallback_path = method_path if method_path.startswith("/") else f"/{method_path}"
            if base_path and not method_path.startswith(base_path):
                fallback_path = f"{base_path.rstrip('/')}/{method_path.lstrip('/')}"
            if not fallback_path or fallback_path == "/":
                fallback_path = f"/{method_name}"
            swagger_data["method"] = method_info.get("method_type", "get").lower()
            swagger_data["path"] = fallback_path

        swagger_path = os.path.join(method_dir, "swagger.json")
        with open(swagger_path, "w", encoding="utf-8") as f:
            json.dump(swagger_data, f, indent=2)

        logger.info(f"Saved documentation for {method_name} to {method_dir}")
        return {"swagger": swagger_path}
